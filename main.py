from fastapi import FastAPI, Depends, HTTPException, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, AsyncGenerator
import json
import asyncio
import uuid

from database import engine, get_db
from models import Base
from schemas import KnowledgeCreate, KnowledgeResponse, QARequest, QAResponse, QAResult, FeedbackCreate, PDFImportResult, PDFParseResult, ChunksImportRequest, SessionResponse, SessionListResponse, PromptSettings
from knowledge_service import KnowledgeService
from qa_service import QAService
from settings_service import SettingsService
from memory_service import MemoryService
from datetime import datetime

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建FastAPI应用
app = FastAPI(title="本地知识库问答系统", version="1.0.0")

# 初始化服务
knowledge_service = KnowledgeService()
qa_service = QAService()
settings_service = SettingsService()
memory_service = MemoryService()

@app.get("/")
async def root():
    return {"message": "欢迎使用本地知识库问答系统"}

# 知识库管理接口
@app.post("/knowledge/", response_model=KnowledgeResponse)
async def create_knowledge(knowledge: KnowledgeCreate, db: Session = Depends(get_db)):
    """创建知识库条目"""
    db_knowledge = knowledge_service.create_knowledge(
        db, knowledge.title, knowledge.content, knowledge.category
    )
    return db_knowledge

@app.get("/knowledge/", response_model=List[KnowledgeResponse])
async def read_knowledges(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取知识库条目列表"""
    knowledges = knowledge_service.get_knowledges(db, skip=skip, limit=limit)
    return knowledges

@app.get("/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def read_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    """获取指定知识库条目"""
    db_knowledge = knowledge_service.get_knowledge(db, knowledge_id)
    if db_knowledge is None:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return db_knowledge

@app.put("/knowledge/{knowledge_id}", response_model=KnowledgeResponse)
async def update_knowledge(knowledge_id: int, knowledge: KnowledgeCreate, db: Session = Depends(get_db)):
    """更新知识库条目"""
    db_knowledge = knowledge_service.update_knowledge(
        db, knowledge_id, knowledge.title, knowledge.content, knowledge.category
    )
    if db_knowledge is None:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return db_knowledge

@app.delete("/knowledge/{knowledge_id}")
async def delete_knowledge(knowledge_id: int, db: Session = Depends(get_db)):
    """删除知识库条目"""
    result = knowledge_service.delete_knowledge(db, knowledge_id)
    if not result:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return {"message": "Knowledge deleted successfully"}

# 解析PDF，返回段落供人工编辑
@app.post("/knowledge/parse-pdf", response_model=PDFParseResult)
async def parse_pdf(file: UploadFile = File(...), regex: str = Form(""), max_chunk_chars: int = Form(2000)):
    data = await file.read()
    chunks = knowledge_service.parse_pdf(file_bytes=data, regex=regex or None, max_chunk_chars=int(max_chunk_chars))
    return {"filename": file.filename, "chunk_count": len(chunks), "chunks": chunks}

# 上传并导入PDF（直接导入）
@app.post("/knowledge/import-pdf", response_model=PDFImportResult)
async def import_pdf(file: UploadFile = File(...), category: str = Form("文档导入"), max_chunk_chars: int = Form(1000), regex: str = Form(""), db: Session = Depends(get_db)):
    """上传并导入PDF，按段落切分并索引到Milvus（支持正则）"""
    data = await file.read()
    result = knowledge_service.import_pdf(db, file_bytes=data, filename=file.filename, category=category, max_chunk_chars=int(max_chunk_chars), regex=regex or None)
    return result

# 导入人工编辑后的段落
@app.post("/knowledge/import-chunks", response_model=PDFImportResult)
async def import_chunks(payload: ChunksImportRequest, db: Session = Depends(get_db)):
    result = knowledge_service.import_chunks(db, filename=payload.filename, chunks=payload.chunks, category=payload.category)
    return result

# 问答接口（支持session_id）
@app.post("/qa/ask", response_model=QAResult)
async def ask_question(qa_request: QARequest, db: Session = Depends(get_db)):
    """提问并获取答案（支持会话记忆）"""
    qa_result = qa_service.ask_question(db, qa_request.question, session_id=qa_request.session_id)
    return qa_result

@app.post("/qa/ask-stream")
async def ask_question_stream(qa_request: QARequest, db: Session = Depends(get_db)):
    """流式提问并获取答案（支持会话记忆）"""
    async def generate_stream():
        # 生成流式响应
        for chunk in qa_service.ask_question_stream(db, qa_request.question, session_id=qa_request.session_id):
            yield chunk
            
    return StreamingResponse(generate_stream(), media_type="text/plain")

# 图片理解接口
@app.post("/qa/ask-image", response_model=QAResponse)
async def ask_image(question: str = Form("请描述这张图片"), image: UploadFile = File(...), session_id: str = Form("") , db: Session = Depends(get_db)):
    data = await image.read()
    res = qa_service.ask_image_question(db, question=question, image_bytes=data, session_id=(session_id or None))
    # 兼容QAResponse结构（无retrieved_knowledges）
    return {
        "id": 0,
        "question": question,
        "answer": res["answer"],
        "created_at": datetime.utcnow(),
        "model_used": qa_service.image_model,
        "process_log": res["process_log"],
        "人工介入": False,
    }

# 反馈接口
@app.post("/qa/feedback")
async def add_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    """添加反馈"""
    qa_service.add_feedback(db, feedback.qa_record_id, feedback.is_useful, feedback.comment)
    return {"message": "Feedback added successfully"}

# 会话管理接口
@app.post("/sessions", response_model=SessionResponse)
async def create_session():
    sid = str(uuid.uuid4())
    return {"session_id": sid}

@app.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    return {"sessions": memory_service.list_sessions()}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    memory_service.clear_session(session_id)
    return {"message": "Session cleared"}

# Prompt设置接口
@app.get("/settings/prompt", response_model=PromptSettings)
async def get_prompt_settings(db: Session = Depends(get_db)):
    return settings_service.get_prompt_settings(db)

@app.put("/settings/prompt", response_model=PromptSettings)
async def update_prompt_settings(payload: PromptSettings, db: Session = Depends(get_db)):
    return settings_service.update_prompt_settings(db, payload.system_prompt, payload.answer_prompt)