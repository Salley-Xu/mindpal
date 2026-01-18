# main.py - 简洁版本
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api_endpoints import router

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ 初始化FastAPI ------------------
app = FastAPI(
    title="MindPal Pro Backend", 
    version="3.2",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(router)

# ------------------ 启动入口 ------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("MindPal Pro 后端服务 v3.2 启动中...")
    print("✨ 功能：上下文感知对话系统 + 个性化推荐")
    print("🔗 API地址: http://localhost:8000")
    print("📝 接口文档: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)