import json
import os
from datetime import datetime
from typing import List, Optional

import httpx

from core.schemas import DocumentChunk, DocumentCreate
from database.models import db_manager


class EmbeddingService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model_name = os.getenv("MODEL_NAME", "text-embedding-ada-002")
        self.base_url = os.getenv("OPENAI_URL", "https://api.openai.com/v1")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的嵌入向量"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model_name,
                "input": texts,
                "encoding_format": "float"
            }

            response = await client.post(
                f"{self.base_url}/embeddings",
                headers=headers,
                json=data,
                timeout=30.0
            )

            if response.status_code != 200:
                raise Exception(
                    f"Embedding API error: {response.status_code}, {response.text}")

            result = response.json()
            return [item["embedding"] for item in result["data"]]

    async def get_single_embedding(self, text: str) -> List[float]:
        """获取单个文本的嵌入向量"""
        embeddings = await self.get_embeddings([text])
        return embeddings[0]


class VectorSearchService:
    def __init__(self):
        pass

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def search_similar_vectors(
        self,
        query_embedding: List[float],
        document_embeddings: List[tuple],
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[tuple]:
        """搜索相似向量"""
        similarities = []

        for doc_id, embedding in document_embeddings:
            similarity = self.cosine_similarity(query_embedding, embedding)
            if similarity >= threshold:
                similarities.append((doc_id, similarity))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]


class DocumentService:
    """文档服务"""

    def __init__(self):
        self.db_manager = db_manager

    def create_document(self, document_data: DocumentCreate) -> dict:
        """创建文档 - 同步版本，用于在异步上下文外调用"""
        import asyncio

        async def _create():
            doc_id = await self.db_manager.insert_document(
                filename=document_data.filename,
                file_path=document_data.file_path,
                content=document_data.content,
                file_type=document_data.file_type,
                file_size=document_data.file_size,
                metadata=document_data.metadata
            )

            # 获取创建的文档
            document = await self.db_manager.get_document(doc_id)
            return document

        # 在新的事件循环中运行
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(_create())

    def create_document_chunk(self, chunk_data: DocumentChunk) -> dict:
        """创建文档块 - 同步版本"""
        import asyncio

        async def _create():
            chunk_id = await self.db_manager.insert_document_chunk(
                document_id=chunk_data.document_id,
                chunk_index=chunk_data.chunk_index,
                content=chunk_data.content,
                embedding=chunk_data.embedding
            )
            return {"id": chunk_id}

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(_create())

    async def get_document(self, document_id: int) -> Optional[dict]:
        """获取文档"""
        return await self.db_manager.get_document(document_id)

    async def get_document_chunks(self, document_id: int) -> List[dict]:
        """获取文档块"""
        return await self.db_manager.get_document_chunks(document_id)

    async def get_all_documents(self) -> List[dict]:
        """获取所有文档"""
        return await self.db_manager.get_all_documents()

    async def search_similar_chunks(
        self,
        query_embedding: List[float],
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[dict]:
        """搜索相似的文档块"""
        chunks = await self.db_manager.get_all_chunk_embeddings()

        similarities = []
        for chunk in chunks:
            similarity = vector_search_service.cosine_similarity(
                query_embedding,
                chunk["embedding"]
            )
            if similarity >= threshold:
                chunk["similarity_score"] = similarity
                similarities.append(chunk)

        # 按相似度排序
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        return similarities[:limit]


# 服务实例
embedding_service = EmbeddingService()
vector_search_service = VectorSearchService()
document_service = DocumentService()
