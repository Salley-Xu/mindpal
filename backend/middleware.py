from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from config import config

def setup_cors(app: FastAPI):
    """设置CORS中间件"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

class RequestLoggingMiddleware:
    """请求日志中间件"""
    async def __call__(self, request, call_next):
        # 记录请求信息
        # 实际实现需要根据FastAPI中间件规范
        response = await call_next(request)
        return response

def setup_middlewares(app: FastAPI):
    """设置所有中间件"""
    setup_cors(app)
    # 添加其他中间件...