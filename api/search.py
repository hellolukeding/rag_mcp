from typing import List

from fastapi import APIRouter, HTTPException, status

from core.schemas import ApiResponse, QueryRequest, QueryResponse, SearchResult
from mcp_server.core.rag_handler import RAGHandler
from utils.logger import logger

router = APIRouter()
rag_handler = RAGHandler()


@router.post("/search", response_model=ApiResponse[QueryResponse])
async def search_knowledge(request: QueryRequest):
    """
    知识库搜索接口
    """
    try:
        search_result = await rag_handler.search_documents(
            query=request.query,
            limit=request.limit,
            threshold=request.threshold
        )

        # 转换结果格式以匹配 SearchResult Schema
        results = []
        for item in search_result.get("results", []):
            results.append(SearchResult(
                document_id=item["document_id"],
                title=item["document_name"],  # 映射 document_name 到 title
                content=item["content"],
                similarity_score=item["similarity_score"],
                metadata={
                    "chunk_id": item["chunk_id"],
                    "chunk_index": item["chunk_index"]
                }
            ))

        return ApiResponse(
            code=200,
            msg="搜索成功",
            data=QueryResponse(
                query=request.query,
                results=results,
                total_results=len(results)
            )
        )

    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return ApiResponse(
            code=500,
            msg=f"搜索失败: {str(e)}",
            data=None
        )
