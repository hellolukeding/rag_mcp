#!/usr/bin/env python3
"""
简单的MCP服务器功能验证脚本
"""

import asyncio
import json
import os
import subprocess
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


async def test_mcp_communication():
    """测试MCP通信协议"""
    print("🧪 测试MCP服务器通信")
    print("=" * 40)

    # 启动MCP服务器
    server_path = project_root
    server_cmd = ["poetry", "run", "python", "mcp_server/server/mcp_server.py"]

    try:
        # 启动服务器进程
        print("🚀 启动MCP服务器...")
        process = await asyncio.create_subprocess_exec(
            *server_cmd,
            cwd=server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        print("✅ 服务器进程已启动")
        await asyncio.sleep(2)  # 等待服务器完全启动

        # 测试基本的JSON-RPC通信
        print("\n📡 测试JSON-RPC通信...")

        # 发送初始化请求
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }

        # 发送消息
        message_str = json.dumps(init_message) + '\n'
        process.stdin.write(message_str.encode())
        await process.stdin.drain()

        # 等待响应
        print("⏳ 等待服务器响应...")
        try:
            # 设置超时读取
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=10.0
            )

            if response_line:
                response_text = response_line.decode().strip()
                print(f"📨 收到响应: {response_text}")

                # 尝试解析JSON响应
                try:
                    response_data = json.loads(response_text)
                    print(f"✅ JSON解析成功: {response_data}")

                    if "result" in response_data:
                        print("🎯 初始化成功!")
                    elif "error" in response_data:
                        print(f"⚠️ 服务器返回错误: {response_data['error']}")

                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"原始响应: {response_text}")

            else:
                print("❌ 没有收到服务器响应")

        except asyncio.TimeoutError:
            print("⏱️ 响应超时")

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")

    finally:
        # 清理进程
        print("\n🧹 清理资源...")
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=5)
            print("✅ 服务器进程已正常终止")
        except:
            print("⚠️ 强制终止服务器进程")
            process.kill()
            await process.wait()


async def test_simple_server():
    """测试简单MCP服务器"""
    print("\n🔄 测试简单MCP服务器")
    print("=" * 40)

    server_path = project_root
    server_cmd = ["poetry", "run", "python",
                  "mcp_server/server/simple_mcp_server.py"]

    try:
        print("🚀 启动简单MCP服务器...")
        process = await asyncio.create_subprocess_exec(
            *server_cmd,
            cwd=server_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.sleep(2)
        print("✅ 简单服务器已启动，测试5秒后自动停止")

        # 简单等待然后停止
        await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ 简单服务器测试出错: {e}")

    finally:
        try:
            process.terminate()
            await asyncio.wait_for(process.wait(), timeout=3)
            print("✅ 简单服务器已停止")
        except:
            process.kill()
            await process.wait()


async def main():
    """主测试函数"""
    print("🎯 MCP服务器简单测试套件")
    print("=" * 50)

    # 检查环境
    if not os.path.exists(os.path.join(project_root, "mcp_server")):
        print("❌ 找不到mcp_server目录")
        return

    print(f"📁 项目根目录: {project_root}")

    # 运行测试
    await test_mcp_communication()
    await asyncio.sleep(2)
    await test_simple_server()

    print("\n🎉 所有测试完成!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
