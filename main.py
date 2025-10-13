from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.upload import router as upload_router
from api.vectorize import router as vectorize_router
from database.models import db_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时初始化数据库
    await db_manager.init_database()
    yield
    # 关闭时的清理工作（如果需要）


app = FastAPI(
    title="RAG-MCP API",
    description="A RAG (Retrieval-Augmented Generation) API with MCP integration",
    version="0.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(upload_router, prefix="/api/v1", tags=["upload"])
app.include_router(vectorize_router, prefix="/api/v1", tags=["vectorize"])


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
