"""
MCP Server implementation for RAG system using MCP SDK
Provides document retrieval capabilities via MCP protocol
"""

from mcp_server.core.rag_handler import rag_handler
from mcp_server.core.config import config
from mcp.types import TextContent, Tool
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server import Server
from dotenv import load_dotenv
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入MCP相关模块

# 导入本地模块

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp-rag-server")

load_dotenv()

# 创建服务器实例
server = Server(config.server.name)


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """返回可用工具列表"""
    return [
        Tool(
            name="rag_search",
            description="Search for relevant document chunks using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant documents"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": config.rag.default_search_limit,
                        "minimum": 1,
                        "maximum": config.rag.max_search_results
                    },
                    "threshold": {
                        "type": "number",
                        "description": "Minimum similarity threshold for results",
                        "default": config.rag.default_similarity_threshold,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "document_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of document IDs to limit search scope"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all available documents in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_document",
            description="Get detailed information about a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "The ID of the document to retrieve"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="search_statistics",
            description="Get search and document statistics",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
    """处理工具调用"""
    try:
        logger.info(f"Handling tool call: {name} with arguments: {arguments}")

        if name == "rag_search":
            result = await handle_rag_search(arguments)
        elif name == "list_documents":
            result = await handle_list_documents(arguments)
        elif name == "get_document":
            result = await handle_get_document(arguments)
        elif name == "search_statistics":
            result = await handle_search_statistics(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")

        logger.info(f"Tool {name} completed successfully")
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        logger.error(f"Error handling tool {name}: {e}")
        error_result = {
            "error": str(e),
            "tool": name,
            "arguments": arguments,
            "success": False
        }
        return [TextContent(type="text", text=json.dumps(error_result, ensure_ascii=False, indent=2))]


async def handle_rag_search(arguments: dict) -> dict:
    """处理RAG搜索"""
    query = arguments.get("query", "")
    limit = arguments.get("limit", config.rag.default_search_limit)
    threshold = arguments.get(
        "threshold", config.rag.default_similarity_threshold)
    document_ids = arguments.get("document_ids")

    if not query.strip():
        raise ValueError("Query cannot be empty")

    result = await rag_handler.search_documents(
        query=query,
        limit=limit,
        threshold=threshold,
        document_ids=document_ids
    )

    result["success"] = True
    return result


async def handle_list_documents(arguments: dict) -> dict:
    """处理文档列表"""
    result = await rag_handler.list_documents()
    result["success"] = True
    return result


async def handle_get_document(arguments: dict) -> dict:
    """处理获取文档详情"""
    document_id = arguments.get("document_id")

    if document_id is None:
        raise ValueError("document_id is required")

    try:
        document_id = int(document_id)
    except (ValueError, TypeError):
        raise ValueError("document_id must be a valid integer")

    result = await rag_handler.get_document(document_id)
    result["success"] = True
    return result


async def handle_search_statistics(arguments: dict) -> dict:
    """处理获取搜索统计"""
    result = await rag_handler.get_search_statistics()
    result["success"] = True
    return result


async def main():
    """主入口函数"""
    try:
        # 验证配置
        config.validate()
        logger.info(
            f"Starting MCP RAG Server: {config.server.name} v{config.server.version}")

        # 使用MCP SDK的stdio_server
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
