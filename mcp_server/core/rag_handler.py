"""
RAG Handler for MCP Server
Provides document retrieval and search functionality
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from core.services import document_service, embedding_service
from database.models import db_manager
from mcp_server.core.config import config
from mcp_server.core.schemas import DocumentInfo, SearchRequest, SearchResult

sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class RAGHandler:
    """RAG处理器，专门处理文档检索相关功能"""

    def __init__(self):
        self.embedding_service = embedding_service
        self.document_service = document_service
        self.db_manager = db_manager
        self.config = config

    async def search_documents(
        self,
        query: str,
        limit: int = None,
        threshold: float = None,
        document_ids: List[int] = None
    ) -> Dict[str, Any]:
        """
        搜索相关文档块

        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            threshold: 相似度阈值
            document_ids: 可选的文档ID列表，用于限制搜索范围

        Returns:
            搜索结果字典
        """
        start_time = datetime.now()

        # 使用默认值
        if limit is None:
            limit = self.config.rag.default_search_limit
        if threshold is None:
            threshold = self.config.rag.default_similarity_threshold

        # 限制最大结果数
        limit = min(limit, self.config.rag.max_search_results)

        try:
            # 获取查询向量
            query_embedding = await self.embedding_service.get_single_embedding(query)

            # 搜索相似文档块
            similar_chunks = await self.document_service.search_similar_chunks(
                query_embedding=query_embedding,
                threshold=threshold,
                limit=limit
            )

            # 如果指定了文档ID，过滤结果
            if document_ids:
                similar_chunks = [
                    chunk for chunk in similar_chunks
                    if chunk.get('document_id') in document_ids
                ]

            # 获取文档信息并格式化结果
            results = []
            for chunk in similar_chunks:
                # 获取文档信息
                document = await self.db_manager.get_document(chunk['document_id'])

                result = {
                    "chunk_id": chunk['chunk_id'],
                    "document_id": chunk['document_id'],
                    "document_name": document.get('filename', 'Unknown') if document else 'Unknown',
                    "content": chunk['content'],
                    "similarity_score": chunk['similarity_score'],
                    "chunk_index": chunk['chunk_index']
                }
                results.append(result)

            # 计算查询时间
            end_time = datetime.now()
            query_time_ms = int((end_time - start_time).total_seconds() * 1000)

            return {
                "results": results,
                "total_results": len(results),
                "query_time_ms": query_time_ms,
                "query": query,
                "threshold": threshold,
                "limit": limit
            }

        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")

    async def list_documents(self) -> Dict[str, Any]:
        """
        获取所有文档列表

        Returns:
            文档列表字典
        """
        try:
            documents = await self.document_service.get_all_documents()

            # 为每个文档添加块数量信息
            document_list = []
            for doc in documents:
                chunks = await self.document_service.get_document_chunks(doc['id'])

                document_info = {
                    "id": doc['id'],
                    "filename": doc['filename'],
                    "file_type": doc['file_type'],
                    "file_size": doc['file_size'],
                    "chunk_count": len(chunks),
                    "created_at": doc['created_at']
                }
                document_list.append(document_info)

            return {
                "documents": document_list,
                "total_documents": len(document_list)
            }

        except Exception as e:
            raise Exception(f"Failed to list documents: {str(e)}")

    async def get_document(self, document_id: int) -> Dict[str, Any]:
        """
        获取文档详情

        Args:
            document_id: 文档ID

        Returns:
            文档详情字典
        """
        try:
            # 获取文档基本信息
            document = await self.document_service.get_document(document_id)
            if not document:
                raise Exception(f"Document with ID {document_id} not found")

            # 获取文档块
            chunks = await self.document_service.get_document_chunks(document_id)

            # 格式化块信息
            chunk_list = []
            for chunk in chunks:
                chunk_info = {
                    "id": chunk['id'],
                    "chunk_index": chunk['chunk_index'],
                    "content": chunk['content']
                }
                chunk_list.append(chunk_info)

            # 排序块
            chunk_list.sort(key=lambda x: x['chunk_index'])

            # 安全解析metadata
            metadata = document.get('metadata')
            if metadata:
                try:
                    metadata = json.loads(metadata)
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            else:
                metadata = {}

            return {
                "document": {
                    "id": document['id'],
                    "filename": document['filename'],
                    "file_type": document['file_type'],
                    "content": document.get('content', ''),
                    "metadata": metadata,
                    "created_at": document['created_at'],
                    "file_size": document['file_size'],
                    "chunks": chunk_list
                }
            }

        except Exception as e:
            raise Exception(f"Failed to get document: {str(e)}")

    async def get_search_statistics(self) -> Dict[str, Any]:
        """
        获取搜索统计信息

        Returns:
            统计信息字典
        """
        try:
            documents = await self.document_service.get_all_documents()

            total_documents = len(documents)
            total_chunks = 0
            file_types = {}

            for doc in documents:
                chunks = await self.document_service.get_document_chunks(doc['id'])
                total_chunks += len(chunks)

                file_type = doc.get('file_type', 'unknown')
                file_types[file_type] = file_types.get(file_type, 0) + 1

            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "file_types": file_types,
                "average_chunks_per_document": total_chunks / total_documents if total_documents > 0 else 0,
                "similarity_threshold": self.config.rag.default_similarity_threshold,
                "default_search_limit": self.config.rag.default_search_limit
            }

        except Exception as e:
            raise Exception(f"Failed to get statistics: {str(e)}")


# 创建全局实例
rag_handler = RAGHandler()
