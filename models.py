from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class Knowledge(Base):
    """知识库条目模型"""
    __tablename__ = "knowledge"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    category = Column(String, index=True)  # 分类，如"规划政策"、"补偿方案"、"权利变更"等
    embedding = Column(LargeBinary, nullable=True)  # 存储embedding向量

class QARecord(Base):
    """问答记录模型"""
    __tablename__ = "qa_records"
    
    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    model_used = Column(String)
    process_log = Column(JSON)  # JSON格式的过程日志记录
    人工介入 = Column(Boolean, default=False)

class Feedback(Base):
    """用户反馈模型"""
    __tablename__ = "feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    qa_record_id = Column(Integer, ForeignKey("qa_records.id"))
    is_useful = Column(Boolean)  # 点赞或点踩
    comment = Column(Text)  # 用户评论
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AppSetting(Base):
    """应用设置模型：用于存储可变的系统提示词等配置"""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())