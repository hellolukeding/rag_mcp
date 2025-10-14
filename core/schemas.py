from datetime import datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class DocumentBase(BaseModel):
    filename: str
    file_path: str
    content: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    metadata: Optional[dict] = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentChunk(BaseModel):
    """文档块模型"""
    document_id: int
    chunk_index: int
    content: str
    embedding: List[float]


class QueryRequest(BaseModel):
    query: str
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.7


class SearchResult(BaseModel):
    document_id: int
    title: str
    content: str
    similarity_score: float
    metadata: Optional[dict] = None


class QueryResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int


# 统一响应格式
class ApiResponse(BaseModel, Generic[T]):
    code: int
    msg: str
    data: Optional[T] = None


# 文件相关的Schema
class FileUploadResponse(BaseModel):
    file_id: str
    original_name: str
    file_size: int
    file_type: str


class FileInfoResponse(BaseModel):
    file_id: str
    original_name: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    created_at: str
    vectorized: bool = False
    vectorized_at: Optional[str] = None


class FileListResponse(BaseModel):
    files: List[FileInfoResponse]
    total: int
