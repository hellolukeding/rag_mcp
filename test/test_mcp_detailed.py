#!/usr/bin/env python3
"""
MCP服务器详细测试 - 包含工具调用
"""

import asyncio
import json
import os
import subprocess
import sys
import time

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


async def detailed_mcp_test():
    """详细测试MCP服务器功能"""
    print("🔍 MCP服务器详细功能测试")
    print("=" * 50)

    # 启动服务器
    server_path = project_root
    process = await asyncio.create_subprocess_exec(
        "poetry", "run", "python", "-m", "mcp_server.server.mcp_server",
        cwd=server_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    print("🚀 MCP服务器已启动")
    await asyncio.sleep(2)  # 等待服务器启动

    try:
        # 1. 发送初始化请求
        print("\n📝 发送初始化请求...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        # 发送请求并读取响应
        process.stdin.write(json.dumps(init_request).encode() + b'\n')
        await process.stdin.drain()

        # 读取响应
        response_line = await process.stdout.readline()
        init_response = json.loads(response_line.decode().strip())
        print(
            f"✅ 初始化响应: {json.dumps(init_response, indent=2, ensure_ascii=False)}")

        # 2. 发送初始化完成通知
        print("\n📋 发送初始化完成通知...")
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }

        process.stdin.write(json.dumps(
            initialized_notification).encode() + b'\n')
        await process.stdin.drain()

        # 等待一下确保初始化完成
        await asyncio.sleep(1)

        # 3. 获取工具列表
        print("\n🛠️ 获取可用工具列表...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }

        process.stdin.write(json.dumps(tools_request).encode() + b'\n')
        await process.stdin.drain()

        # 读取工具列表响应
        tools_response_line = await process.stdout.readline()
        tools_response = json.loads(tools_response_line.decode().strip())
        print(
            f"📋 可用工具: {json.dumps(tools_response, indent=2, ensure_ascii=False)}")

        # 4. 测试文档列表工具
        print("\n📚 测试 list_documents 工具...")
        list_docs_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_documents",
                "arguments": {}
            }
        }

        process.stdin.write(json.dumps(list_docs_request).encode() + b'\n')
        await process.stdin.drain()

        # 读取响应
        list_docs_response_line = await process.stdout.readline()
        list_docs_response = json.loads(
            list_docs_response_line.decode().strip())
        print(
            f"📋 文档列表: {json.dumps(list_docs_response, indent=2, ensure_ascii=False)}")

        # 5. 测试搜索工具
        print("\n🔍 测试 rag_search 工具...")
        search_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "rag_search",
                "arguments": {
                    "query": "AI心理咨询",
                    "limit": 3
                }
            }
        }

        process.stdin.write(json.dumps(search_request).encode() + b'\n')
        await process.stdin.drain()

        # 读取搜索响应
        search_response_line = await process.stdout.readline()
        search_response = json.loads(search_response_line.decode().strip())
        print(
            f"🔍 搜索结果: {json.dumps(search_response, indent=2, ensure_ascii=False)}")

        # 6. 测试统计信息工具
        print("\n📊 测试 search_statistics 工具...")
        stats_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "search_statistics",
                "arguments": {}
            }
        }

        process.stdin.write(json.dumps(stats_request).encode() + b'\n')
        await process.stdin.drain()

        # 读取统计响应
        stats_response_line = await process.stdout.readline()
        stats_response = json.loads(stats_response_line.decode().strip())
        print(
            f"📊 统计信息: {json.dumps(stats_response, indent=2, ensure_ascii=False)}")

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

    finally:
        # 停止服务器
        print("\n🛑 停止MCP服务器...")
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
            print("✅ 服务器已正常停止")
        except asyncio.TimeoutError:
            print("⚠️ 强制终止服务器...")
            process.kill()
            await process.wait()

if __name__ == "__main__":
    try:
        asyncio.run(detailed_mcp_test())
        print("\n🎉 MCP服务器测试完成!")
    except KeyboardInterrupt:
        print("\n\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
