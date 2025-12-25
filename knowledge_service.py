from sqlalchemy.orm import Session
from models import Knowledge
from typing import List, Optional, Tuple
from embedding_service import EmbeddingService
import numpy as np
from vector_store import MilvusVectorStore
import pdfplumber
import io
import re

class KnowledgeService:
    """知识库管理服务"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = MilvusVectorStore()
    
    def create_knowledge(self, db: Session, title: str, content: str, category: str) -> Knowledge:
        """创建知识库条目并索引到Milvus"""
        # 生成embedding
        text_for_embedding = f"{title} {content}"
        embedding = None
        try:
            embedding = self.embedding_service.get_embedding(text_for_embedding)
        except Exception as e:
            print(f"Warning: Failed to generate embedding: {e}")
        
        db_knowledge = Knowledge(
            title=title, 
            content=content, 
            category=category,
            embedding=None  # 向量改用Milvus存储
        )
        db.add(db_knowledge)
        db.commit()
        db.refresh(db_knowledge)
        
        # 索引到Milvus
        try:
            if embedding is not None:
                self.vector_store.index(db_knowledge.id, embedding)
        except Exception as e:
            print(f"Warning: Failed to upsert into Milvus: {e}")
        
        return db_knowledge

    def get_knowledge(self, db: Session, knowledge_id: int) -> Optional[Knowledge]:
        """根据ID获取知识库条目"""
        return db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
    
    def get_knowledges(self, db: Session, skip: int = 0, limit: int = 100) -> List[Knowledge]:
        """获取知识库条目列表"""
        return db.query(Knowledge).offset(skip).limit(limit).all()
    
    def get_knowledges_by_category(self, db: Session, category: str) -> List[Knowledge]:
        """根据分类获取知识库条目"""
        return db.query(Knowledge).filter(Knowledge.category == category).all()
    
    def update_knowledge(self, db: Session, knowledge_id: int, title: str = None, 
                        content: str = None, category: str = None) -> Optional[Knowledge]:
        """更新知识库条目并更新Milvus索引"""
        db_knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if db_knowledge:
            if title is not None:
                db_knowledge.title = title
            if content is not None:
                db_knowledge.content = content
            if category is not None:
                db_knowledge.category = category
                
            # 如果标题或内容有更新，重新生成embedding并更新Milvus
            if title is not None or content is not None:
                text_for_embedding = f"{db_knowledge.title} {db_knowledge.content}"
                try:
                    embedding = self.embedding_service.get_embedding(text_for_embedding)
                    db_knowledge.embedding = None  # 不再在DB中存储
                    db.commit()
                    db.refresh(db_knowledge)
                    # 更新Milvus索引（先删后插避免重复）
                    try:
                        self.vector_store.delete_by_id(db_knowledge.id)
                    except Exception:
                        pass
                    self.vector_store.index(db_knowledge.id, embedding)
                except Exception as e:
                    print(f"Warning: Failed to generate embedding: {e}")
            else:
                db.commit()
                db.refresh(db_knowledge)
        return db_knowledge

    def delete_knowledge(self, db: Session, knowledge_id: int) -> bool:
        """删除知识库条目，并从Milvus中移除"""
        db_knowledge = db.query(Knowledge).filter(Knowledge.id == knowledge_id).first()
        if not db_knowledge:
            return False
        try:
            self.vector_store.delete_by_id(knowledge_id)
        except Exception:
            pass
        db.delete(db_knowledge)
        db.commit()
        return True
    
    def search_knowledge_by_embedding(self, db: Session, query_embedding: np.ndarray, top_k: int = 5) -> List[tuple]:
        """基于Milvus搜索最相关的知识库条目，返回[(Knowledge, similarity), ...]"""
        results: List[Tuple[int, float]] = self.vector_store.search(query_embedding, top_k=top_k)
        out: List[Tuple[Knowledge, float]] = []
        for kid, score in results:
            knowledge = db.query(Knowledge).filter(Knowledge.id == kid).first()
            if knowledge:
                # 将相似度限制在0-1之间（COSINE通常0~1，按需调整）
                sim = max(0.0, min(1.0, score))
                out.append((knowledge, sim))
        return out

    def parse_pdf(self, file_bytes: bytes, regex: Optional[str] = None, max_chunk_chars: int = 2000) -> List[str]:
        """解析PDF文本并按规则切分为段落。
        - 若提供regex，则按该正则作为“段落标题”进行切分（如：第XXX条）
        - 若未提供regex，则自动检测包含“第...条”的模式，否则退回空行切分
        """
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            full_text_parts: List[str] = []
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt:
                    full_text_parts.append(txt)
            full_text = "\n".join(full_text_parts)
        
        # 标准化换行
        text = re.sub(r"\r\n?|\u000B", "\n", full_text)
        
        # 更健壮的默认正则：匹配“第 X 条”（允许空格，中文或阿拉伯数字）
        default_pattern = r"(第\s*[一二三四五六七八九十百千0-9]+\s*条)"
        pattern = regex if (regex and regex.strip()) else default_pattern
        
        # 尝试按正则分段，容错处理无效正则
        chunks: List[str] = []
        try:
            matches = list(re.finditer(pattern, text))
        except re.error:
            matches = []
        
        if matches:
            # 以每个标题为起点，截取至下一个标题之前的内容
            indices = [m.start() for m in matches] + [len(text)]
            for i in range(len(matches)):
                start = indices[i]
                end = indices[i+1]
                segment = text[start:end].strip()
                if segment:
                    chunks.append(segment)
        else:
            # 回退：基于空行的分段
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            chunks.extend(paragraphs)
        
        # 控制每段最大长度：如超出则按句号/空行进一步拆分
        final_chunks: List[str] = []
        for c in chunks:
            if len(c) <= max_chunk_chars:
                final_chunks.append(c)
            else:
                # 尝试按句号或换行拆分
                sub_parts = re.split(r"(?<=[。！？!?.])\s+|\n+", c)
                buf = []
                size = 0
                for sp in sub_parts:
                    if size + len(sp) + 1 <= max_chunk_chars:
                        buf.append(sp)
                        size += len(sp) + 1
                    else:
                        if buf:
                            final_chunks.append("".join(buf).strip())
                        buf = [sp]
                        size = len(sp)
                if buf:
                    final_chunks.append("".join(buf).strip())
        
        return final_chunks

    def import_pdf(self, db: Session, file_bytes: bytes, filename: str, category: str = "文档导入", max_chunk_chars: int = 1000, regex: Optional[str] = None) -> dict:
        """读取PDF，按段落切分并存入向量数据库和知识库（支持正则切分）"""
        chunks = self.parse_pdf(file_bytes, regex=regex, max_chunk_chars=max_chunk_chars)
        knowledge_ids: List[int] = []
        for i, chunk in enumerate(chunks):
            title = f"{filename} - 段落 {i+1}"
            k = self.create_knowledge(db, title=title, content=chunk, category=category)
            knowledge_ids.append(k.id)
        return {
            "filename": filename,
            "chunks_imported": len(chunks),
            "knowledge_ids": knowledge_ids,
        }

    def import_chunks(self, db: Session, filename: str, chunks: List[str], category: str = "文档导入") -> dict:
        """将人工编辑后的文本块导入知识库并索引"""
        knowledge_ids: List[int] = []
        for i, chunk in enumerate(chunks):
            clean = (chunk or "").strip()
            if not clean:
                continue
            title = f"{filename} - 段落 {i+1}"
            k = self.create_knowledge(db, title=title, content=clean, category=category)
            knowledge_ids.append(k.id)
        return {
            "filename": filename,
            "chunks_imported": len(knowledge_ids),
            "knowledge_ids": knowledge_ids,
        }