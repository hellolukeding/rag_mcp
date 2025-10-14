from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.upload import router as upload_router
from api.vectorize import router as task_vectorize_router
from core.vectorize import get_vectorize_instance
from database.models import db_manager
from utils.logger import logger

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await db_manager.init_database()

    # 启动向量化服务
    logger.info("正在启动向量化服务...")
    vectorize_service = get_vectorize_instance()
    logger.info("向量化服务启动完成")

    yield

    # 关闭时的清理工作
    logger.info("正在关闭向量化服务...")
    vectorize_service.stop()
    logger.info("向量化服务已关闭")


app = FastAPI(
    title="RAG-MCP API",
    description="A RAG (Retrieval-Augmented Generation) API with MCP integration",
    version="0.1.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[

        "http://localhost:5173",  # Vite开发服务器

        # 生产环境域名可以在这里添加
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-CSRF-Token",
    ],
)

# 注册路由
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(task_vectorize_router, prefix="/api/v1", tags=["vectorize"])


@app.get("/")
async def root():

    return {
        "message": "Welcome to RAG-MCP API",
        "version": "0.1.0",
        "docs_url": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
