import openai
import numpy as np
from config import Config
import pickle
import logging
import httpx

# 配置日志
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class EmbeddingService:
    """Embedding服务"""
    
    def __init__(self):
        """初始化Embedding客户端"""
        self.client = openai.OpenAI(
            base_url=Config.EMBEDDING_BASE_URL,
            api_key=Config.EMBEDDING_API_KEY
        )
        self.model = Config.EMBEDDING_MODEL
        self.base_url = Config.EMBEDDING_BASE_URL
    
    def get_embedding(self, text: str) -> np.ndarray:
        """获取文本的embedding向量"""
        try:
            # 检查是否是Ollama端点
            if "ollama" in self.base_url or "11434" in self.base_url:
                return self._get_ollama_embedding(text)
            else:
                # 使用OpenAI格式
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                if not response.data:
                    raise Exception("No embedding data received")
                embedding = response.data[0].embedding
                return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"获取embedding时出错: {str(e)}")
            raise
    
    def _get_ollama_embedding(self, text: str) -> np.ndarray:
        """获取Ollama格式的embedding向量"""
        try:
            # 直接使用httpx调用Ollama API
            url = f"{self.base_url}/embeddings"
            payload = {
                "model": self.model,
                "prompt": text
            }
            
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            
            data = response.json()
            if "embedding" not in data:
                raise Exception("No embedding data received from Ollama")
                
            embedding = data["embedding"]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"获取Ollama embedding时出错: {str(e)}")
            raise
    
    def encode_embedding(self, embedding: np.ndarray) -> bytes:
        """将numpy数组编码为字节"""
        return pickle.dumps(embedding)
    
    def decode_embedding(self, embedding_bytes: bytes) -> np.ndarray:
        """将字节解码为numpy数组"""
        return pickle.loads(embedding_bytes)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个向量之间的余弦相似度"""
        # 归一化向量
        embedding1_norm = embedding1 / np.linalg.norm(embedding1)
        embedding2_norm = embedding2 / np.linalg.norm(embedding2)
        
        # 计算余弦相似度
        similarity = np.dot(embedding1_norm, embedding2_norm)
        return float(similarity)