from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Knowledge
from knowledge_service import KnowledgeService

def init_db():
    """初始化数据库并添加示例数据"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    # 获取数据库会话
    db = SessionLocal()
    
    # 检查是否已有数据
    existing_knowledges = db.query(Knowledge).count()
    if existing_knowledges > 0:
        print("数据库中已有数据，跳过初始化")
        db.close()
        return
    
    # 添加示例数据
    sample_knowledges = [
        {
            "title": "示例标题",
            "content": "示例内容",
            "category": "示例分类"
        }
    ]
    
    knowledge_service = KnowledgeService()
    for knowledge_data in sample_knowledges:
        knowledge_service.create_knowledge(
            db, 
            knowledge_data["title"], 
            knowledge_data["content"], 
            knowledge_data["category"]
        )
    
    db.close()
    print("数据库初始化完成，示例数据已添加")

if __name__ == "__main__":
    init_db()