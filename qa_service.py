import json
import openai
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple, Optional
from config import Config
from models import QARecord, Knowledge, Feedback
from knowledge_service import KnowledgeService
from embedding_service import EmbeddingService
from datetime import datetime
import logging
import base64

from memory_service import MemoryService
from settings_service import SettingsService

# 配置日志
logging.basicConfig(level=Config.LOG_LEVEL)
logger = logging.getLogger(__name__)

class QAService:
    """问答服务"""
    
    def __init__(self):
        """初始化OpenAI客户端"""
        self.client = openai.OpenAI(
            base_url=Config.BASE_URL,
            api_key=Config.API_KEY
        )
        self.model = Config.MODEL_NAME
        self.image_model = Config.IMAGE_MODEL_NAME
        self.embedding_service = EmbeddingService()
        self.knowledge_service = KnowledgeService()
        self.memory_service = MemoryService()
        self.settings_service = SettingsService()
    
    def search_knowledge(self, db: Session, query: str) -> List[Tuple[Knowledge, float]]:
        """在知识库中搜索相关条目，返回(knowledge, similarity)"""
        try:
            # 获取查询的embedding
            query_embedding = self.embedding_service.get_embedding(query)
            
            # 基于embedding搜索相关知识
            similar_knowledges = self.knowledge_service.search_knowledge_by_embedding(db, query_embedding, top_k=5)
            
            # 返回(知识条目, 相似度)
            return similar_knowledges
        except Exception as e:
            logger.warning(f"基于embedding的搜索失败，使用简单文本匹配: {str(e)}")
            # 如果embedding搜索失败，回退到简单的文本匹配（无相似度）
            knowledges = db.query(Knowledge).filter(
                Knowledge.content.contains(query) | Knowledge.title.contains(query)
            ).all()
            return [(k, 0.0) for k in knowledges]

    def _build_messages(self, db: Session, question: str, context: str, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """根据会话历史与提示词构建消息列表"""
        prompts = self.settings_service.get_prompt_settings(db)
        system_prompt = prompts.get("system_prompt") or "你是一个专业的政策咨询助手，能够根据提供的材料准确回答问题。"
        answer_prompt = prompts.get("answer_prompt") or "请用中文回答，若信息不足请明确说明无法根据提供的信息回答。"

        user_content = f"""
        根据以下背景信息回答问题。如果背景信息不包含足够信息来回答问题，请说明无法根据提供的信息回答该问题。

        背景信息：
        {context}

        问题：
        {question}

        {answer_prompt}
        """.strip()

        messages: List[Dict[str, Any]] = []
        messages.append({"role": "system", "content": system_prompt})
        # 注入会话历史
        if session_id:
            for msg in self.memory_service.get_messages(session_id):
                role = "user" if msg.type == "human" else ("assistant" if msg.type == "ai" else "system")
                content = msg.content if isinstance(msg.content, str) else json.dumps(msg.content)
                messages.append({"role": role, "content": content})
        # 当前轮次问题
        messages.append({"role": "user", "content": user_content})
        return messages
    
    def generate_answer(self, db: Session, question: str, context: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """调用LLM生成答案"""
        messages = self._build_messages(db, question, context, session_id)
        process_log = {
            "model": self.model,
            "timestamp": str(datetime.now())
        }
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            if usage:
                process_log["prompt_tokens"] = usage.prompt_tokens
                process_log["response_tokens"] = usage.completion_tokens
                process_log["total_tokens"] = usage.total_tokens
            process_log["status"] = "success"
            
            # 写入会话记忆（仅存原始问答）
            if session_id:
                self.memory_service.add_user_message(session_id, question)
                self.memory_service.add_ai_message(session_id, answer)
            
        except Exception as e:
            logger.error(f"调用LLM时出错: {str(e)}")
            answer = "抱歉，暂时无法回答您的问题。"
            process_log["status"] = "error"
            process_log["error_message"] = str(e)
        
        return {
            "answer": answer,
            "process_log": process_log
        }
    
    def generate_answer_stream(self, db: Session, question: str, context: str, session_id: Optional[str] = None):
        """调用LLM流式生成答案"""
        messages = self._build_messages(db, question, context, session_id)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                stream=True
            )
            
            collected = []
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    collected.append(chunk.choices[0].delta.content)
                    yield chunk.choices[0].delta.content
            # 完成后写入会话记忆
            if session_id:
                self.memory_service.add_user_message(session_id, question)
                self.memory_service.add_ai_message(session_id, "".join(collected))
                    
        except Exception as e:
            logger.error(f"调用LLM时出错: {str(e)}")
            yield "抱歉，暂时无法回答您的问题。"
    
    def ask_question(self, db: Session, question: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """处理用户提问"""
        # 搜索相关知识
        similar_knowledges = self.search_knowledge(db, question)  # List[(Knowledge, sim)]
        knowledges_only = [k for k, _ in similar_knowledges]
        
        # 构建上下文
        context = "\n\n".join([f"标题: {k.title}\n内容: {k.content}" for k in knowledges_only])
        if not context:
            context = "未找到相关背景信息。"
        
        # 生成答案
        result = self.generate_answer(db, question, context, session_id=session_id)
        
        # 记录问答过程
        qa_record = QARecord(
            question=question,
            answer=result["answer"],
            model_used=self.model,
            process_log=result["process_log"]
        )
        
        db.add(qa_record)
        db.commit()
        db.refresh(qa_record)
        
        # 准备返回数据，包括检索到的知识与相似度
        response_data = {
            "id": qa_record.id,
            "question": qa_record.question,
            "answer": qa_record.answer,
            "created_at": qa_record.created_at,
            "model_used": qa_record.model_used,
            "process_log": qa_record.process_log,
            "人工介入": qa_record.人工介入,
            "retrieved_knowledges": [
                {
                    "id": k.id,
                    "title": k.title,
                    "content": k.content,
                    "category": k.category,
                    "created_at": k.created_at,
                    "updated_at": k.updated_at,
                    "similarity": float(sim)
                } for (k, sim) in similar_knowledges
            ]
        }
        
        return response_data
    
    def ask_question_stream(self, db: Session, question: str, session_id: Optional[str] = None):
        """流式处理用户提问"""
        # 搜索相关知识
        similar_knowledges = self.search_knowledge(db, question)
        knowledges_only = [k for k, _ in similar_knowledges]
        
        # 构建上下文
        context = "\n\n".join([f"标题: {k.title}\n内容: {k.content}" for k in knowledges_only])
        if not context:
            context = "未找到相关背景信息。"
        
        # 流式生成答案
        for chunk in self.generate_answer_stream(db, question, context, session_id=session_id):
            yield chunk
    
    def add_feedback(self, db: Session, qa_record_id: int, is_useful: bool, comment: str = None) -> Feedback:
        """添加用户反馈"""
        feedback = Feedback(
            qa_record_id=qa_record_id,
            is_useful=is_useful,
            comment=comment
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        return feedback

    def ask_image_question(self, db: Session, question: str, image_bytes: bytes, session_id: Optional[str] = None) -> Dict[str, Any]:
        """图片理解问答：将图片与问题一起发送给多模态模型"""
        prompts = self.settings_service.get_prompt_settings(db)
        system_prompt = prompts.get("system_prompt") or "你是一个专业的政策咨询助手，能够根据提供的材料准确回答问题。"
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64," + base64.b64encode(image_bytes).decode("utf-8")}
                    }
                ]
            }
        ]
        process_log = {
            "model": self.image_model,
            "timestamp": str(datetime.now())
        }
        try:
            response = self.client.chat.completions.create(
                model=self.image_model,
                messages=messages,
                temperature=0.2,
                max_tokens=800
            )
            answer = response.choices[0].message.content
            usage = getattr(response, "usage", None)
            if usage:
                process_log["prompt_tokens"] = usage.prompt_tokens
                process_log["response_tokens"] = usage.completion_tokens
                process_log["total_tokens"] = usage.total_tokens
            process_log["status"] = "success"
            if session_id:
                self.memory_service.add_user_message(session_id, f"[图片问答] {question}")
                self.memory_service.add_ai_message(session_id, answer)
        except Exception as e:
            logger.error(f"多模态模型调用出错: {str(e)}")
            answer = "抱歉，图片理解暂时不可用。"
            process_log["status"] = "error"
            process_log["error_message"] = str(e)
        return {"answer": answer, "process_log": process_log}