#!/usr/bin/env python3
"""
简化的向量化状态测试 - 专注于API响应
"""

from utils.logger import logger
from database.models import DatabaseManager
from api.upload import list_files
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))


async def test_api_status_response():
    """测试API响应中的向量化状态"""
    logger.info("🧪 开始测试API向量化状态响应...")

    # 初始化数据库
    db_manager = DatabaseManager()
    await db_manager.init_database()

    try:
        # 1. 测试不同状态的文件
        logger.info("📝 创建不同状态的测试文件记录...")

        test_files = [
            ("pending_file", "pending"),
            ("processing_file", "processing"),
            ("completed_file", "completed"),
            ("failed_file", "failed")
        ]

        for file_id, status in test_files:
            # 创建文件记录
            await db_manager.insert_file(
                file_id=file_id,
                original_name=f"{status}_test.md",
                file_name=f"{status}_test.md",
                file_path=f"/test/{status}_test.md",
                file_type=".md",
                file_size=1000
            )

            # 设置状态
            await db_manager.update_file_vectorized_status(file_id, status)
            logger.info(f"✅ 创建 {status} 状态文件: {file_id}")

        # 2. 测试API响应
        logger.info("\n🔍 测试API响应格式...")

        # 调用文件列表API
        api_response = await list_files()

        if api_response.code == 200:
            logger.info("✅ API调用成功")

            files = api_response.data.files
            logger.info(f"📊 返回文件数量: {len(files)}")

            # 验证各种状态
            status_counts = {}
            for file in files:
                status = file.vectorized_status
                status_counts[status] = status_counts.get(status, 0) + 1

                if file.file_id in [f[0] for f in test_files]:
                    expected_status = next(
                        f[1] for f in test_files if f[0] == file.file_id)
                    if status == expected_status:
                        logger.info(f"✅ {file.file_id} 状态正确: {status}")
                    else:
                        logger.error(
                            f"❌ {file.file_id} 状态错误: 期望 {expected_status}, 实际 {status}")

            logger.info(f"\n📈 状态分布统计:")
            for status, count in status_counts.items():
                logger.info(f"  {status}: {count} 个文件")

            # 验证状态枚举
            valid_statuses = ["pending", "processing", "completed", "failed"]
            for status in status_counts.keys():
                if status in valid_statuses:
                    logger.info(f"✅ 状态 '{status}' 有效")
                else:
                    logger.error(f"❌ 状态 '{status}' 无效")

        else:
            logger.error(f"❌ API调用失败: {api_response.msg}")

        # 3. 测试单个文件API
        logger.info("\n🔍 测试单个文件API...")

        file_info = await db_manager.get_file_by_id("completed_file")
        if file_info:
            logger.info(f"✅ 获取文件信息成功")
            logger.info(f"📊 文件状态: {file_info['vectorized']}")
            logger.info(f"📅 向量化时间: {file_info.get('vectorized_at', 'None')}")
        else:
            logger.error("❌ 获取文件信息失败")

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        raise
    finally:
        # 清理测试数据
        logger.info("\n🗑️ 清理测试数据...")
        for file_id, _ in test_files:
            try:
                await db_manager.delete_file_and_documents(file_id)
            except Exception as e:
                logger.warning(f"清理 {file_id} 失败: {e}")


async def main():
    """主函数"""
    try:
        await test_api_status_response()
        logger.info("✅ API向量化状态测试完成")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
