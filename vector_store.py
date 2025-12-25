from typing import List, Tuple, Optional
from config import Config
import numpy as np
import logging

from pymilvus import (
    connections,
    FieldSchema,
    CollectionSchema,
    DataType,
    Collection,
    utility,
)

logger = logging.getLogger(__name__)

class MilvusVectorStore:
    """Milvus向量存储封装"""

    def __init__(self):
        self.host = Config.MILVUS_HOST
        self.port = Config.MILVUS_PORT
        self.collection_name = Config.MILVUS_COLLECTION
        self.metric_type = Config.MILVUS_METRIC_TYPE
        self.index_type = Config.MILVUS_INDEX_TYPE
        self._collection: Optional[Collection] = None
        self._connect()

    def _connect(self):
        try:
            connections.connect(alias="default", host=self.host, port=self.port)
            logger.info(f"Connected to Milvus at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接 Milvus 失败: {e}")
            raise

    def _get_collection(self) -> Optional[Collection]:
        if self._collection is not None:
            return self._collection
        if utility.has_collection(self.collection_name):
            self._collection = Collection(self.collection_name)
            try:
                self._collection.load()
            except Exception:
                # ignore load errors; will be loaded lazily
                pass
            return self._collection
        return None

    def ensure_collection(self, dim: int) -> Collection:
        """确保集合存在，若不存在则创建。"""
        col = self._get_collection()
        if col:
            # 校验维度是否匹配
            try:
                for f in col.schema.fields:
                    if f.name == "embedding" and f.dtype == DataType.FLOAT_VECTOR:
                        field_dim = int(f.params.get("dim", dim))
                        if field_dim != dim:
                            raise ValueError(f"Milvus集合的维度({field_dim})与当前Embedding维度({dim})不匹配")
                        break
            except Exception:
                pass
            return col

        # 创建集合
        fields = [
            FieldSchema(name="knowledge_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields=fields, description="Knowledge embeddings")
        col = Collection(name=self.collection_name, schema=schema)

        # 创建索引
        try:
            index_params = {
                "index_type": self.index_type,
                "metric_type": self.metric_type,
                "params": {"M": 8, "efConstruction": 200} if self.index_type == "HNSW" else {"nlist": 1024}
            }
            col.create_index(field_name="embedding", index_params=index_params)
            col.load()
            logger.info(f"Milvus集合 {self.collection_name} 已创建，dim={dim}, index={self.index_type}/{self.metric_type}")
        except Exception as e:
            logger.warning(f"创建索引失败或已存在: {e}")
            try:
                col.load()
            except Exception:
                pass
        self._collection = col
        return col

    def index(self, knowledge_id: int, embedding: np.ndarray):
        """插入或更新向量。"""
        if embedding is None:
            return
        embedding = embedding.astype(np.float32)
        dim = int(embedding.shape[0])
        col = self.ensure_collection(dim)
        try:
            # 使用insert以最大兼容性；如需覆盖请先删除再插入
            entities = [
                [int(knowledge_id)],
                [embedding.tolist()],
            ]
            col.insert(entities)
            col.flush()
        except Exception as e:
            logger.error(f"向Milvus插入向量失败: {e}")
            raise

    def delete_by_id(self, knowledge_id: int):
        col = self._get_collection()
        if not col:
            return
        try:
            expr = f"knowledge_id in [{int(knowledge_id)}]"
            col.delete(expr)
            col.flush()
        except Exception as e:
            logger.warning(f"从Milvus删除ID={knowledge_id}失败: {e}")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[int, float]]:
        """在Milvus中搜索最相似的向量，返回(knowledge_id, similarity)。"""
        col = self._get_collection()
        if col is None:
            return []
        try:
            query = query_embedding.astype(np.float32)
            search_params = {"metric_type": self.metric_type, "params": {"ef": 128} if self.index_type == "HNSW" else {"nprobe": 16}}
            results = col.search(
                data=[query.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["knowledge_id"],
            )
            hits = results[0]
            out: List[Tuple[int, float]] = []
            for h in hits:
                kid = int(h.entity.get("knowledge_id"))
                score = float(h.distance)
                out.append((kid, score))
            return out
        except Exception as e:
            logger.error(f"Milvus搜索失败: {e}")
            return []