import streamlit as st
import requests
import json
from typing import Dict, Any
import time
import os

# 应用配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="本地知识库问答系统",
    page_icon="📚",
    layout="wide"
)

# 初始化session state
if "knowledges" not in st.session_state:
    st.session_state.knowledges = []
if "current_question" not in st.session_state:
    st.session_state.current_question = ""
if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""
if "current_qa_id" not in st.session_state:
    st.session_state.current_qa_id = None
if "is_answering" not in st.session_state:
    st.session_state.is_answering = False
if "process_log" not in st.session_state:
    st.session_state.process_log = {}
if "retrieved_knowledges" not in st.session_state:
    st.session_state.retrieved_knowledges = []
# 新增：会话与Prompt设置状态
if "session_id" not in st.session_state:
    st.session_state.session_id = ""
if "sessions" not in st.session_state:
    st.session_state.sessions = []
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = ""
if "answer_prompt" not in st.session_state:
    st.session_state.answer_prompt = ""

# 复用的API函数
def load_knowledges():
    try:
        response = requests.get(f"{API_BASE_URL}/knowledge/")
        if response.status_code == 200:
            st.session_state.knowledges = response.json()
        else:
            st.session_state.knowledges = []
    except Exception as e:
        st.session_state.knowledges = []
        st.error(f"加载知识库失败: {str(e)}")

# 新增：会话管理与Prompt设置API
def load_sessions():
    try:
        resp = requests.get(f"{API_BASE_URL}/sessions")
        if resp.status_code == 200:
            st.session_state.sessions = resp.json().get("sessions", [])
        else:
            st.session_state.sessions = []
    except Exception as e:
        st.session_state.sessions = []
        st.error(f"加载会话失败: {str(e)}")


def create_session():
    try:
        resp = requests.post(f"{API_BASE_URL}/sessions")
        if resp.status_code == 200:
            sid = resp.json().get("session_id", "")
            st.session_state.session_id = sid
            load_sessions()
            st.success("已创建新会话")
        else:
            st.error("创建会话失败")
    except Exception as e:
        st.error(f"创建会话失败: {str(e)}")


def clear_session(session_id: str):
    try:
        if not session_id:
            st.warning("当前未选择会话")
            return
        resp = requests.delete(f"{API_BASE_URL}/sessions/{session_id}")
        if resp.status_code == 200:
            st.success("会话已清空")
            st.session_state.session_id = ""
            load_sessions()
        else:
            st.error("清空会话失败")
    except Exception as e:
        st.error(f"清空会话失败: {str(e)}")


def load_prompt_settings():
    try:
        resp = requests.get(f"{API_BASE_URL}/settings/prompt")
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.system_prompt = data.get("system_prompt", "")
            st.session_state.answer_prompt = data.get("answer_prompt", "")
        else:
            st.warning("无法加载Prompt设置")
    except Exception as e:
        st.error(f"加载Prompt设置失败: {str(e)}")


def save_prompt_settings(system_prompt: str, answer_prompt: str):
    try:
        resp = requests.put(f"{API_BASE_URL}/settings/prompt", json={
            "system_prompt": system_prompt,
            "answer_prompt": answer_prompt
        })
        if resp.status_code == 200:
            st.success("Prompt设置已更新")
            load_prompt_settings()
        else:
            st.error("更新Prompt设置失败")
    except Exception as e:
        st.error(f"更新Prompt设置失败: {str(e)}")


def create_knowledge(title: str, content: str, category: str):
    try:
        response = requests.post(f"{API_BASE_URL}/knowledge/", json={
            "title": title,
            "content": content,
            "category": category
        })
        if response.status_code == 200:
            st.success("知识已添加")
            load_knowledges()
        else:
            st.error("添加知识失败")
    except Exception as e:
        st.error(f"添加知识失败: {str(e)}")

# 新增：删除知识
def delete_knowledge(knowledge_id: int):
    try:
        resp = requests.delete(f"{API_BASE_URL}/knowledge/{knowledge_id}")
        if resp.status_code == 200:
            st.success("知识已删除")
            load_knowledges()
        else:
            st.error("删除失败")
    except Exception as e:
        st.error(f"删除失败: {str(e)}")


def add_feedback(qa_id: int, is_useful: bool, comment: str = None):
    try:
        response = requests.post(f"{API_BASE_URL}/qa/feedback", json={
            "qa_record_id": qa_id,
            "is_useful": is_useful,
            "comment": comment or ""
        })
        if response.status_code == 200:
            st.success("反馈已提交")
        else:
            st.error("反馈提交失败")
    except Exception as e:
        st.error(f"反馈提交失败: {str(e)}")

# 页面标题
st.title("📚 本地知识库问答系统")
# 初始加载会话列表
load_sessions()

# 创建标签页
tab1, tab2, tab3 = st.tabs(["问答", "知识库管理", "系统信息"])

# 问答标签页
with tab1:
    st.header("问答")

    # 会话管理
    session_cols = st.columns([2, 1, 1])
    with session_cols[0]:
        # 构建选项（后端返回 sessions: List[str]）
        existing_ids = st.session_state.sessions
        session_options = [""] + existing_ids
        index = 0
        if st.session_state.session_id in existing_ids:
            index = existing_ids.index(st.session_state.session_id) + 1
        selected = st.selectbox("选择会话", options=session_options, index=index)
        st.session_state.session_id = selected or ""
        st.caption(f"当前会话: {st.session_state.session_id or '未选择'}")
    with session_cols[1]:
        if st.button("新建会话"):
            create_session()
    with session_cols[2]:
        if st.button("清空当前会话"):
            clear_session(st.session_state.session_id)

    # 问题输入和提问按钮
    question = st.text_area("请输入您的问题:", height=100, key="question_input")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("提问", type="primary", use_container_width=True):
            if question.strip():
                st.session_state.current_question = question.strip()
                st.session_state.current_answer = ""
                st.session_state.retrieved_knowledges = []
                st.session_state.is_answering = True
                st.rerun()
            else:
                st.warning("请输入问题")
    
    with col2:
        if st.button("清空", use_container_width=True):
            st.session_state.current_question = ""
            st.session_state.current_answer = ""
            st.session_state.retrieved_knowledges = []
            st.session_state.is_answering = True
            st.rerun()
    
    # 显示答案
    if st.session_state.is_answering:
        st.subheader("回答:")
        answer_placeholder = st.empty()
        full_answer = st.session_state.current_answer
        
        # 如果正在回答或有新问题需要处理
        if st.session_state.is_answering and st.session_state.current_question:
            try:
                # 先调用非流式API获取详细信息（包括检索到的知识和过程日志）
                response = requests.post(f"{API_BASE_URL}/qa/ask", 
                                       json={"question": st.session_state.current_question, "session_id": st.session_state.session_id or ""})
                if response.status_code == 200:
                    qa_data = response.json()
                    st.session_state.current_qa_id = qa_data["id"]
                    st.session_state.process_log = qa_data["process_log"]
                    st.session_state.retrieved_knowledges = qa_data.get("retrieved_knowledges", [])
                # 使用流式请求显示回答
                with requests.post(f"{API_BASE_URL}/qa/ask-stream", 
                                  json={"question": st.session_state.current_question, "session_id": st.session_state.session_id or ""}, 
                                  stream=True) as r:
                    r.raise_for_status()
                    
                    # 实时更新回答
                    for chunk in r.iter_content(chunk_size=1, decode_unicode=True):
                        if chunk:
                            full_answer += chunk
                            answer_placeholder.markdown(full_answer + "▌")
                    
                    # 完成后移除光标符号
                    answer_placeholder.markdown(full_answer)
                    st.session_state.current_answer = full_answer
                    st.session_state.is_answering = False
                    st.session_state.current_question = ""  # 清除问题，避免重复提问
                    
            except Exception as e:
                st.error(f"获取回答失败: {str(e)}")
                st.session_state.current_answer = ""
                st.session_state.is_answering = False
        else:
            # 显示已有的回答
            answer_placeholder.markdown(full_answer)

    # 新增：非流式回答展示（例如图片问答结果）
    if not st.session_state.is_answering and st.session_state.current_answer:
        st.subheader("回答:")
        st.markdown(st.session_state.current_answer)
    
    # 显示检索到的知识（Top 5，并显示相关率）
    if st.session_state.retrieved_knowledges:
        st.subheader("检索到的相关知识:")
        for i, knowledge in enumerate(st.session_state.retrieved_knowledges[:5]):
            rel_rate = knowledge.get("similarity", 0.0)
            rel_percent = f"{rel_rate * 100:.2f}%"
            with st.expander(f"知识 {i+1}: {knowledge['title']}  ·  相关率 {rel_percent}"):
                st.markdown(f"**分类:** {knowledge['category']}")
                st.markdown(f"**内容:**\n\n{knowledge['content']}")
    elif st.session_state.current_answer and not st.session_state.is_answering:
        st.info("本次问答未检索到相关知识。")
    
    # 新增：图片理解问答（折叠优化布局）
    with st.expander("图片理解问答"):
        img_col1, img_col2 = st.columns([2, 1])
        with img_col1:
            image_file = st.file_uploader("上传图片", type=["png", "jpg", "jpeg"], key="image_file_qa")
        with img_col2:
            image_question = st.text_input("图片问题", value="请描述这张图片", key="image_question")
        # 在折叠面板内即时展示答案的占位
        image_answer_placeholder = st.empty()
        submit_cols = st.columns([1,1])
        with submit_cols[0]:
            if st.button("提交图片问答", use_container_width=True):
                if image_file is not None and image_question.strip():
                    try:
                        mime = "image/png"
                        if image_file.type in ["image/jpg", "image/jpeg"]:
                            mime = "image/jpeg"
                        files = {"image": (image_file.name, image_file.getvalue(), mime)}
                        data = {"question": image_question, "session_id": st.session_state.session_id or ""}
                        resp = requests.post(f"{API_BASE_URL}/qa/ask-image", files=files, data=data)
                        if resp.status_code == 200:
                            data = resp.json()
                            st.session_state.current_answer = data.get("answer", "")
                            st.session_state.process_log = data.get("process_log", {})
                            st.success("图片问答完成")
                            # 即时在折叠面板内展示答案（非流式）
                            if st.session_state.current_answer:
                                image_answer_placeholder.markdown(f"**回答：**\n\n{st.session_state.current_answer}")
                            else:
                                image_answer_placeholder.info("后端未返回答案内容。")
                        else:
                            st.error("图片问答失败")
                    except Exception as e:
                        st.error(f"图片问答失败: {str(e)}")
                else:
                    st.warning("请上传图片并填写问题")
        with submit_cols[1]:
            if st.button("清空图片问题", use_container_width=True):
                st.session_state.image_file_qa = None
                st.session_state.image_question = "请描述这张图片"
                image_answer_placeholder.empty()
    
    # 反馈区域
    if st.session_state.current_answer and not st.session_state.is_answering:
        st.subheader("反馈:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👍 有帮助", use_container_width=True):
                if st.session_state.current_qa_id:
                    add_feedback(st.session_state.current_qa_id, True)
        with col2:
            if st.button("👎 无帮助", use_container_width=True):
                if st.session_state.current_qa_id:
                    add_feedback(st.session_state.current_qa_id, False)
        
        with st.expander("详细过程日志"):
            if st.session_state.process_log:
                st.json(st.session_state.process_log)
                
                # 保存日志到文件
                if st.button("保存过程日志到本地文件"):
                    try:
                        log_filename = save_process_log_to_file(st.session_state.process_log, 
                                                               st.session_state.current_question or 
                                                               st.session_state.process_log.get('question', '未知问题'))
                        st.success(f"日志已保存至: {log_filename}")
                    except Exception as e:
                        st.error(f"保存日志失败: {str(e)}")
            else:
                st.info("暂无详细过程日志")

# 知识库管理标签页
with tab2:
    st.header("知识库管理")
    
    # 创建新知识
    with st.expander("添加新知识"):
        with st.form("create_knowledge_form"):
            title = st.text_input("标题")
            category = st.selectbox("分类", ["规划政策", "补偿方案", "权利变更", "其他"])
            content = st.text_area("内容", height=200)
            
            if st.form_submit_button("添加知识"):
                if title and content:
                    create_knowledge(title, content, category)
                else:
                    st.warning("请填写标题和内容")
    
    # 导入PDF（直接导入）
    with st.expander("导入PDF到知识库（快速）"):
        with st.form("import_pdf_form"):
            pdf_file = st.file_uploader("选择PDF文件", type=["pdf"], key="pdf_file_quick")
            category = st.selectbox("分类", ["文档导入", "规划政策", "补偿方案", "权利变更", "其他"], index=0, key="pdf_category_quick")
            max_chunk_chars = st.number_input("每段最大字符数", min_value=200, max_value=4000, value=1000, step=100, key="max_chunk_quick")
            regex = st.text_input("正则（可选，用于按标题分段，如：第[一二三四五六七八九十百千0-9]+条）", value="", key="regex_quick")
            if st.form_submit_button("快速导入"):
                if pdf_file is not None:
                    try:
                        files = {"file": (pdf_file.name, pdf_file.getvalue(), "application/pdf")}
                        data = {"category": category, "max_chunk_chars": str(max_chunk_chars), "regex": regex}
                        resp = requests.post(f"{API_BASE_URL}/knowledge/import-pdf", files=files, data=data)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            st.success(f"导入成功，生成 {res_json['chunks_imported']} 个段落")
                            load_knowledges()
                        else:
                            st.error("导入失败")
                    except Exception as e:
                        st.error(f"导入失败: {str(e)}")
                else:
                    st.warning("请先选择PDF文件")
    
    # 解析PDF并人工编辑后导入
    with st.expander("解析PDF并人工编辑导入（推荐）"):
        # 初始化解析状态
        if "pdf_chunks_preview" not in st.session_state:
            st.session_state.pdf_chunks_preview = []
        if "pdf_parse_filename" not in st.session_state:
            st.session_state.pdf_parse_filename = None
        if "pdf_parse_category" not in st.session_state:
            st.session_state.pdf_parse_category = "文档导入"
        if "pdf_parse_regex" not in st.session_state:
            st.session_state.pdf_parse_regex = "第[一二三四五六七八九十百千0-9]+条"
        
        # 步骤1：上传并解析
        colp1, colp2 = st.columns([2,1])
        with colp1:
            pdf_file2 = st.file_uploader("选择PDF文件", type=["pdf"], key="pdf_file_parse")
        with colp2:
            st.session_state.pdf_parse_category = st.selectbox("分类", ["文档导入", "规划政策", "补偿方案", "权利变更", "其他"], index=0, key="pdf_category_parse")
        st.session_state.pdf_parse_regex = st.text_input("正则（用于按标题分段）", value=st.session_state.pdf_parse_regex, key="regex_parse")
        max_chunk_chars2 = st.number_input("每段最大字符数", min_value=200, max_value=6000, value=2000, step=100, key="max_chunk_parse")
        parse_cols = st.columns([1,1,1])
        with parse_cols[0]:
            if st.button("解析PDF"):
                if pdf_file2 is not None:
                    try:
                        files = {"file": (pdf_file2.name, pdf_file2.getvalue(), "application/pdf")}
                        data = {"regex": st.session_state.pdf_parse_regex, "max_chunk_chars": str(max_chunk_chars2)}
                        resp = requests.post(f"{API_BASE_URL}/knowledge/parse-pdf", files=files, data=data)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            st.session_state.pdf_chunks_preview = res_json["chunks"]
                            st.session_state.pdf_parse_filename = res_json["filename"]
                            st.success(f"解析成功，共 {res_json['chunk_count']} 段")
                        else:
                            st.error("解析失败")
                    except Exception as e:
                        st.error(f"解析失败: {str(e)}")
                else:
                    st.warning("请先选择PDF文件")
        with parse_cols[1]:
            if st.button("全选/取消全选"):
                # 使用checkbox状态管理
                for i in range(len(st.session_state.pdf_chunks_preview)):
                    st.session_state[f"chunk_{i}_include"] = not st.session_state.get(f"chunk_{i}_include", True)
        with parse_cols[2]:
            if st.button("清空解析结果"):
                st.session_state.pdf_chunks_preview = []
                st.session_state.pdf_parse_filename = None
        
        # 步骤2：人工编辑每段
        if st.session_state.pdf_chunks_preview:
            st.info("请逐段审阅并编辑内容，勾选需要导入的段落。")
            for i, chunk in enumerate(st.session_state.pdf_chunks_preview):
                default_include = st.session_state.get(f"chunk_{i}_include", True)
                st.session_state[f"chunk_{i}_include"] = st.checkbox(f"导入段落 {i+1}", value=default_include, key=f"include_{i}")
                st.session_state[f"chunk_{i}_text"] = st.text_area(f"段落 {i+1} 内容", value=chunk, height=200, key=f"text_{i}")
                st.divider()
            
            # 步骤3：提交导入
            if st.button("导入选中段落"):
                selected_chunks = []
                for i in range(len(st.session_state.pdf_chunks_preview)):
                    if st.session_state.get(f"include_{i}", True):
                        selected_chunks.append(st.session_state.get(f"text_{i}", ""))
                if not selected_chunks:
                    st.warning("请至少选择一个段落")
                else:
                    try:
                        payload = {
                            "filename": st.session_state.pdf_parse_filename or (pdf_file2.name if pdf_file2 else "PDF"),
                            "category": st.session_state.pdf_parse_category,
                            "chunks": selected_chunks
                        }
                        resp = requests.post(f"{API_BASE_URL}/knowledge/import-chunks", json=payload)
                        if resp.status_code == 200:
                            res_json = resp.json()
                            st.success(f"导入成功，生成 {res_json['chunks_imported']} 个段落")
                            # 重置解析状态
                            st.session_state.pdf_chunks_preview = []
                            st.session_state.pdf_parse_filename = None
                            load_knowledges()
                        else:
                            st.error("导入失败")
                    except Exception as e:
                        st.error(f"导入失败: {str(e)}")

    # 显示知识库
    st.subheader("现有知识")
    load_knowledges()
    
    if st.session_state.knowledges:
        for knowledge in st.session_state.knowledges:
            with st.expander(f"{knowledge['title']} ({knowledge['category']})"):
                st.markdown(f"**ID:** {knowledge['id']}")
                st.markdown(f"**创建时间:** {knowledge['created_at']}")
                if knowledge['updated_at']:
                    st.markdown(f"**更新时间:** {knowledge['updated_at']}")
                st.markdown(f"**内容:**\n\n{knowledge['content']}")
                # 新增：删除按钮
                if st.button("删除该知识", key=f"delete_{knowledge['id']}"):
                    delete_knowledge(knowledge['id'])
    else:
        st.info("知识库中暂无内容")

# 系统信息标签页
with tab3:
    st.header("系统信息")
    st.markdown("""
    ### 本地知识库问答系统
    
    本系统基于大语言模型构建，具有以下特点：
    
    1. **知识库管理**：支持对知识库条目的增删改查操作
    2. **智能问答**：基于知识库内容回答用户问题
    3. **反馈机制**：用户可以对回答进行点赞或点踩
    4. **过程日志**：完整记录问答过程，确保可追溯性
    5. **人工介入**：支持人工介入处理复杂问题
    6. **RAG技术**：采用检索增强生成技术提升问答准确性
    7. **流式输出**：支持流式输出，提升用户体验
    
    ### 使用说明
    
    1. 在"知识库管理"页面添加相关政策、法规等内容
    2. 在"问答"页面提出问题
    3. 系统将基于知识库内容生成回答
    4. 用户可以对回答进行反馈
    
    ### 技术架构
    
    - 后端框架：FastAPI
    - 前端框架：Streamlit
    - 数据库：SQLite + Milvus（向量存储）
    - LLM接口：OpenAI兼容接口
    """)

    # 新增：Prompt设置
    with st.expander("Prompt设置"):
        load_prompt_settings()
        sys_p = st.text_area("系统Prompt", value=st.session_state.system_prompt, height=160, key="system_prompt_input")
        ans_p = st.text_area("答案模板Prompt", value=st.session_state.answer_prompt, height=160, key="answer_prompt_input")
        if st.button("保存Prompt设置"):
            save_prompt_settings(sys_p.strip(), ans_p.strip())


def save_process_log_to_file(log_data: dict, question: str):
    # 创建logs目录（如果不存在）
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # 生成文件名（使用时间戳和问题前几个字符）
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{logs_dir}/process_log_{timestamp}.json"
    
    # 保存日志数据
    log_entry = {
        "timestamp": timestamp,
        "question": question,
        "log_data": log_data
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    return filename