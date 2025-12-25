from typing import List
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.messages import BaseMessage
from config import Config

class MemoryService:
    """LangChain基于SQLite的会话记忆服务，按session_id管理对话历史。"""
    def __init__(self):
        # 使用同一SQLite数据库存储会话历史
        # SQLChatMessageHistory 会自动创建所需的表
        self.connection_string = Config.DATABASE_URL

    def get_history(self, session_id: str) -> SQLChatMessageHistory:
        return SQLChatMessageHistory(session_id=session_id, connection_string=self.connection_string)

    def get_messages(self, session_id: str) -> List[BaseMessage]:
        return self.get_history(session_id).messages

    def add_user_message(self, session_id: str, content: str) -> None:
        self.get_history(session_id).add_user_message(content)

    def add_ai_message(self, session_id: str, content: str) -> None:
        self.get_history(session_id).add_ai_message(content)

    def clear_session(self, session_id: str) -> None:
        self.get_history(session_id).clear()

    def list_sessions(self) -> List[str]:
        """基于消息表的session_id去重列出会话；如无表则返回空。"""
        import sqlite3
        # 连接到SQLite数据库
        if not self.connection_string.startswith("sqlite"):
            return []
        # 连接字符串格式为 sqlite:///./knowledge_qa.db
        db_path = self.connection_string.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            # 兼容可能的表名差异
            sessions = set()
            for table in ("message_store", "langchain_chat_messages"):
                try:
                    cur.execute(f"SELECT DISTINCT session_id FROM {table}")
                    rows = cur.fetchall()
                    for (sid,) in rows:
                        if sid:
                            sessions.add(sid)
                except Exception:
                    continue
            return sorted(list(sessions))
        finally:
            conn.close()