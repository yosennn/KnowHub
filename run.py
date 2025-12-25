import uvicorn
import subprocess
import sys
import os
from config import Config

def run_backend():
    """运行后端服务"""
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

def run_frontend():
    """运行前端服务"""
    subprocess.run([sys.executable, "-m", "streamlit", "run", "frontend.py"])

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "backend":
            run_backend()
        elif sys.argv[1] == "frontend":
            run_frontend()
    else:
        print("使用方法:")
        print("  python run.py backend   - 启动后端服务")
        print("  python run.py frontend  - 启动前端服务")