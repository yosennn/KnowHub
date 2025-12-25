import os
from typing import Optional
import logging

# 配置日志
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

class Config:
    # OpenAI兼容API配置
    BASE_URL: str = os.getenv("BASE_URL", "https://api.openai.com/v1")
    API_KEY: str = os.getenv("API_KEY", "")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek/deepseek-r1")
    IMAGE_MODEL_NAME: str = os.getenv("IMAGE_MODEL_NAME", "gpt-4o-mini")
    
    # Embedding模型配置
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "bge-m3:latest")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./knowledge_qa.db")

    # Milvus配置
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: str = os.getenv("MILVUS_PORT", "19530")
    MILVUS_COLLECTION: str = os.getenv("MILVUS_COLLECTION", "knowledge_embeddings")
    MILVUS_INDEX_TYPE: str = os.getenv("MILVUS_INDEX_TYPE", "HNSW")
    MILVUS_METRIC_TYPE: str = os.getenv("MILVUS_METRIC_TYPE", "COSINE")
    
    # 应用配置
    APP_TITLE: str = "本地知识库问答系统"
    APP_VERSION: str = "1.0.0"
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# 添加配置输出用于调试
logger.info("Configuration loaded:")
logger.info(f"  BASE_URL: {Config.BASE_URL}")
logger.info(f"  EMBEDDING_BASE_URL: {Config.EMBEDDING_BASE_URL}")
logger.info(f"  EMBEDDING_MODEL: {Config.EMBEDDING_MODEL}")
logger.info(f"  MILVUS_HOST: {Config.MILVUS_HOST}")
logger.info(f"  MILVUS_PORT: {Config.MILVUS_PORT}")
logger.info(f"  MILVUS_COLLECTION: {Config.MILVUS_COLLECTION}")
logger.info(f"  IMAGE_MODEL_NAME: {Config.IMAGE_MODEL_NAME}")
