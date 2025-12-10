"""
MCP Server implementation for RAG system using MCP SDK
Provides document retrieval capabilities via MCP protocol
"""

from mcp.types import TextContent, Tool
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server import Server
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
import time
import threading
import signal
import logging
import json
import asyncio
import os
import sys

# Re-exec when executed as a script so module imports work consistently.
if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    args = [sys.executable, "-m", "mcp_server.server.mcp_server"] + sys.argv[1:]
    os.execvp(sys.executable, args)

# Ensure project root is on sys.path so local package imports resolve even when
# running inside different environments or when another top-level module with
# the same name exists on sys.path.
project_root = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from mcp_server.core.config import config
    from mcp_server.core.rag_handler import rag_handler
except ModuleNotFoundError as e:
    # Helpful error when import fails — include sys.path to aid debugging.
    print("错误: 无法导入 mcp_server 包。请以模块方式运行或确保项目根目录在 PYTHONPATH。")
    print("当前 sys.path:")
    for p in sys.path[:10]:
        print("  ", p)
    raise


# (sys.path insertion moved above) Ensure python path is configured before imports.

# 导入MCP相关模块

# 导入本地模块

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("mcp-rag-server")

load_dotenv()

# Ensure server logs are written to `mcp_server/mcp_server.log` in the package
# directory using a rotating file handler. Make rotation size/backups configurable
# via environment variables so tests can adjust behavior if needed.
try:
    from logging.handlers import RotatingFileHandler

    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_file_path = os.path.join(package_dir, "mcp_server.log")

    # Configurable via env vars (defaults reasonable for production)
    max_bytes = int(os.environ.get("MCP_LOG_MAX_BYTES",
                    str(10 * 1024 * 1024)))  # 10 MB
    backup_count = int(os.environ.get("MCP_LOG_BACKUP_COUNT", "5"))

    # Only add a RotatingFileHandler if one isn't already present for this path
    existing = False
    for h in logger.handlers:
        try:
            if isinstance(h, RotatingFileHandler) and os.path.abspath(h.baseFilename) == os.path.abspath(log_file_path):
                existing = True
                break
        except Exception:
            continue

    if not existing:
        os.makedirs(package_dir, exist_ok=True)
        fh = RotatingFileHandler(
            log_file_path, maxBytes=max_bytes, backupCount=backup_count)
        fh.setLevel(logging.INFO)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        logger.addHandler(fh)
except Exception:
    # If logging setup fails, don't break server startup; continue with console logging
    logger.exception(
        "Failed to set up rotating file logging for mcp_server.log")

# 创建服务器实例
server = Server(config.server.name)

# Thread control: event to signal server started and refs for the thread/loop
server_started_event = threading.Event()
server_loop_ref: dict[str, any] = {}
server_thread: threading.Thread | None = None


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
            # Signal that the server has (almost) started; we are about to run the server loop
            try:
                server_started_event.set()
            except Exception:
                pass
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    # 当进入 stdio_server 上下文后，标记为已启动
    # We can't set the server_started_event before entering the context here since that
    # would happen inside the coroutine; instead we set it right before awaiting server.run

    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def run_server_in_thread(wait_started: bool = True) -> threading.Thread:
    """Start the MCP server in a separate daemon thread to avoid blocking.

    The thread runs its own asyncio event loop and will execute `main()` in that
    event loop. If wait_started is True, this function will block until the
    server sets `server_started_event` or timed-out.
    """
    global server_thread

    def _target():
        loop = asyncio.new_event_loop()
        server_loop_ref['loop'] = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        except Exception as e:
            logger.exception(f"Server thread exception: {e}")
        finally:
            # Clean up
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
            server_loop_ref.pop('loop', None)

    server_thread = threading.Thread(target=_target, daemon=True)
    server_thread.start()
    if wait_started:
        server_started_event.wait(timeout=10)
    return server_thread


def stop_server_in_thread(timeout: float = 5.0):
    """Try to stop the server by stopping the thread's event loop and joining the thread."""
    global server_thread
    try:
        loop = server_loop_ref.get('loop')
        if loop is not None:
            # This should cause loop.run_until_complete to exit
            loop.call_soon_threadsafe(loop.stop)
    except Exception:
        pass
    if server_thread is not None:
        server_thread.join(timeout)
        if server_thread.is_alive():
            logger.warning(
                "Server thread did not exit within timeout; process may still need to be killed.")


if __name__ == "__main__":
    # Run server in separate thread to avoid blocking main thread and make it
    # easier to terminate in interactive environments.
    def _signal_handler(sig, frame):
        logger.info(f"Signal {sig} received, stopping server...")
        stop_server_in_thread()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        run_server_in_thread(wait_started=True)
        logger.info(
            "Server started in background thread. Press Ctrl+C to stop.")
        # Keep the main thread alive while server thread is running
        while True:
            if server_thread and not server_thread.is_alive():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        stop_server_in_thread()
    except Exception as e:
        logger.error(f"Server error: {e}")
        sys.exit(1)
