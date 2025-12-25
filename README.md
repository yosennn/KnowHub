# 本地知识库问答系统

基于大语言模型(LLM)的本地知识库问答系统原型，能够回答关于规划政策、补偿方案、权利变更等典型问题，并设计了人工介入、过程日志记录与意见采纳反馈机制。

## 功能特点

1. **知识库管理**：支持知识库的增删改查操作
2. **智能问答**：基于知识库内容回答用户问题
3. **反馈机制**：用户可以对回答进行点赞或点踩
4. **过程日志**：完整记录问答过程，确保可追溯性
5. **人工介入**：支持人工介入处理复杂问题
6. **OpenAI兼容**：支持任何OpenAI兼容的模型提供商
7. **RAG实现**：基于Embedding的检索增强生成
8. **流式输出**：支持流式输出，提升用户体验
9. **可配置**：所有配置项集中在一个配置文件中

## 技术架构

- 后端框架：FastAPI
- 前端框架：Streamlit
- 数据库：SQLite
- LLM接口：OpenAI兼容接口
- ORM：SQLAlchemy
- RAG技术：基于Embedding的向量检索

## 功能说明

### RAG (Retrieval-Augmented Generation) 实现

本系统实现了基于Embedding的检索增强生成(RAG)功能：

1. **Embedding生成**：使用OpenAI兼容的Embedding模型为知识库条目生成向量表示
2. **向量存储**：将生成的向量存储在数据库中
3. **相似性检索**：当用户提问时，将问题转换为向量，并与知识库中的向量进行相似性比较
4. **上下文构建**：根据相似性检索结果，构建包含最相关知识的上下文
5. **答案生成**：将问题和上下文传递给大语言模型生成答案

这种方法比简单的关键词匹配更加精确，能够更好地理解问题的语义并找到相关答案。

### 流式输出

系统支持流式输出功能，用户可以在前端看到回答逐步生成的过程，提升交互体验：
1. 用户提交问题后，系统立即开始处理
2. 回答内容以字符流的形式逐步显示在界面上
3. 用户无需等待完整回答生成完毕即可开始阅读

## 安装步骤

1. 克隆或下载项目代码

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置环境变量（可选）：
   ```bash
   export BASE_URL="你的API地址"
   export API_KEY="你的API密钥"
   export EMBEDDING_BASE_URL="你的Embedding API地址"
   export EMBEDDING_API_KEY="你的Embedding API密钥"
   ```

4. 初始化数据库：
   ```bash
   python init_db.py
   ```

## 运行应用

### 方法一：分别运行前后端

1. 启动后端服务：
   ```bash
   python run.py backend
   ```

2. 启动前端服务：
   ```bash
   python run.py frontend
   ```

### 方法二：使用不同的终端窗口

1. 在第一个终端窗口中运行后端：
   ```bash
   uvicorn main:app --reload
   ```

2. 在第二个终端窗口中运行前端：
   ```bash
   streamlit run frontend.py
   ```

## 使用说明

1. 访问前端界面（默认：http://localhost:8501）
2. 在"知识库管理"页面添加相关政策、法规等内容
3. 在"问答"页面提出问题
4. 系统将基于知识库内容生成回答，支持流式输出
5. 用户可以对回答进行反馈

## 配置说明

所有配置项在 [config.py](config.py) 文件中：

- `BASE_URL`：OpenAI兼容API的基础URL
- `API_KEY`：API密钥
- `MODEL_NAME`：使用的模型名称
- `EMBEDDING_BASE_URL`：Embedding API的基础URL
- `EMBEDDING_API_KEY`：Embedding API密钥
- `EMBEDDING_MODEL`：使用的Embedding模型名称
- `DATABASE_URL`：数据库连接URL
- `APP_TITLE`：应用标题
- `LOG_LEVEL`：日志级别

## 目录结构

```
.
├── config.py           # 配置文件
├── database.py         # 数据库连接
├── models.py           # 数据库模型
├── schemas.py          # 数据传输对象
├── knowledge_service.py # 知识库服务
├── qa_service.py       # 问答服务
├── embedding_service.py # Embedding服务
├── main.py             # 后端主应用
├── frontend.py         # 前端应用
├── init_db.py          # 数据库初始化
├── run.py              # 运行脚本
├── requirements.txt    # 依赖列表
└── README.md           # 说明文档
```

## API接口

### 知识库管理

- `POST /knowledge/`：创建知识库条目
- `GET /knowledge/`：获取知识库条目列表
- `GET /knowledge/{id}`：获取指定知识库条目
- `PUT /knowledge/{id}`：更新知识库条目
- `DELETE /knowledge/{id}`：删除知识库条目

### 问答服务

- `POST /qa/ask`：提问并获取答案
- `POST /qa/ask-stream`：流式提问并获取答案
- `POST /qa/feedback`：添加反馈

## 数据库设计

1. **knowledge**：知识库表
   - id：主键
   - title：标题
   - content：内容
   - category：分类
   - created_at：创建时间
   - updated_at：更新时间
   - embedding：向量表示（二进制存储）

2. **qa_records**：问答记录表
   - id：主键
   - question：问题
   - answer：答案
   - created_at：创建时间
   - model_used：使用的模型
   - process_log：过程日志（JSON格式）
   - 人工介入：是否有人工介入

3. **feedback**：反馈表
   - id：主键
   - qa_record_id：问答记录ID
   - is_useful：是否有用（点赞/点踩）
   - comment：评论
   - created_at：创建时间

## 扩展建议

1. 实现更复杂的知识检索算法
2. 添加用户权限管理
3. 增加问答历史记录功能
4. 实现更详细的日志分析功能
5. 添加知识库版本管理
6. 实现多语言支持
7. 使用专门的向量数据库（如Faiss、Pinecone等）替代SQLite存储向量