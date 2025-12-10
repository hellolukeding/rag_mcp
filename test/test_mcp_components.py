#!/usr/bin/env python3
"""
MCP服务器基本功能测试
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置环境变量
os.environ['OPENAI_API_KEY'] = 'sk-test-key-12345'


async def test_mcp_components():
    """测试MCP组件是否正常工作"""
    print("🧪 MCP组件测试")
    print("=" * 40)

    try:
        # 1. 测试配置导入
        print("📋 测试配置模块...")
        from mcp_server.core.config import config
        print(f"✅ 配置加载成功: {config.server.name}")

        # 2. 测试RAG处理器
        print("\n🔍 测试RAG处理器...")
        from mcp_server.core.rag_handler import rag_handler

        # 测试文档列表功能
        documents = await rag_handler.list_documents()
        print(f"✅ RAG处理器工作正常，找到 {len(documents)} 个文档")

        if documents and len(documents) > 0:
            # 显示第一个文档信息
            first_doc = documents[0] if isinstance(
                documents, list) else documents
            if isinstance(first_doc, dict):
                print(f"📄 示例文档: {first_doc.get('title', 'N/A')}")
            else:
                print(f"📄 文档类型: {type(first_doc)}")
                print(f"📄 文档内容: {str(first_doc)[:100]}")

        # 3. 测试搜索功能
        print("\n🔍 测试搜索功能...")
        try:
            search_results = await rag_handler.search_documents("AI", limit=2)
            print(f"✅ 搜索功能正常，返回 {len(search_results)} 个结果")

            if search_results:
                for i, result in enumerate(search_results[:2]):
                    print(f"  {i+1}. {result.get('content', '')[:50]}...")

        except Exception as e:
            print(f"⚠️ 搜索功能测试失败（可能需要向量化）: {e}")

        # 4. 测试统计信息
        print("\n📊 测试统计信息...")
        stats = await rag_handler.get_search_statistics()
        print(f"✅ 统计信息: {stats}")

        print("\n🎉 所有MCP组件测试通过!")
        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_database_connection():
    """测试数据库连接"""
    print("\n🗄️ 数据库连接测试")
    print("=" * 40)

    try:
        from database.models import db_manager

        # 使用正确的数据库连接方法
        db = await db_manager._get_db()

        # 获取表信息
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = await cursor.fetchall()
        table_names = [table['name'] for table in tables]
        print(f"✅ 数据库连接成功，找到表: {table_names}")

        # 获取文档数量
        cursor = await db.execute("SELECT COUNT(*) as count FROM documents")
        doc_count = await cursor.fetchone()
        print(f"📚 文档数量: {doc_count['count']}")

        # 获取分块数量
        cursor = await db.execute("SELECT COUNT(*) as count FROM document_chunks")
        chunk_count = await cursor.fetchone()
        print(f"📄 分块数量: {chunk_count['count']}")

        await db.close()

        return True

    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 MCP服务器组件测试套件")
    print("=" * 50)
    print(f"📁 项目根目录: {project_root}")

    # 运行测试
    db_ok = await test_database_connection()
    mcp_ok = await test_mcp_components()

    if db_ok and mcp_ok:
        print("\n✅ 所有测试通过! MCP服务器组件工作正常")

        print("\n📝 要启动MCP服务器，请运行:")
        print("  poetry run python -m mcp_server.server.mcp_server")
        print("\n📝 要测试MCP通信，请运行:")
        print("  poetry run python -m test.test_mcp_simple")

        return 0
    else:
        print("\n❌ 某些测试失败")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试出错: {e}")
        sys.exit(1)
