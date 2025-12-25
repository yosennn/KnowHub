from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

# 知识库相关模型
class KnowledgeBase(BaseModel):
    title: str
    content: str
    category: str

class KnowledgeCreate(KnowledgeBase):
    pass

class KnowledgeResponse(KnowledgeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# 知识库详情模型（用于问答结果中返回）
class KnowledgeDetail(KnowledgeBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    similarity: float
    
    class Config:
        from_attributes = True

# 问答相关模型
class QARequest(BaseModel):
    question: str
    session_id: Optional[str] = None

class QAResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime
    model_used: str
    process_log: Dict[str, Any]
    人工介入: bool
    
    class Config:
        from_attributes = True

# 问答结果模型（包含检索到的知识）
class QAResult(QAResponse):
    retrieved_knowledges: List[KnowledgeDetail]
    
    class Config:
        from_attributes = True

# 反馈相关模型
class FeedbackCreate(BaseModel):
    qa_record_id: int
    is_useful: bool
    comment: Optional[str] = None

# PDF解析结果（提供人工编辑前预览）
class PDFParseResult(BaseModel):
    filename: str
    chunk_count: int
    chunks: List[str]

# PDF导入结果
class PDFImportResult(BaseModel):
    filename: str
    chunks_imported: int
    knowledge_ids: List[int]

# 手工编辑后导入的请求
class ChunksImportRequest(BaseModel):
    filename: str
    category: str
    chunks: List[str]

# 会话相关
class SessionResponse(BaseModel):
    session_id: str

class SessionListResponse(BaseModel):
    sessions: List[str]

# Prompt设置
class PromptSettings(BaseModel):
    system_prompt: Optional[str] = None
    answer_prompt: Optional[str] = None