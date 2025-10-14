#!/usr/bin/env python3
"""
测试文件内容查看功能
"""

from utils.logger import logger
from database.models import DatabaseManager
from api.upload import get_file_content
import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_file_content_api():
    """测试文件内容查看API"""
    logger.info("🧪 开始测试文件内容查看功能...")

    # 初始化数据库
    db_manager = DatabaseManager()
    await db_manager.init_database()
    logger.info("✅ 数据库初始化完成")

    try:
        # 创建测试文件
        test_dir = Path("test/temp_content_test")
        test_dir.mkdir(exist_ok=True)

        test_content = """这是一个测试文件的内容。

包含多行文本：
1. 第一行内容
2. 第二行内容  
3. 第三行内容

测试中文字符和标点符号：，。！？"""

        test_file = test_dir / "content_test.txt"
        test_file.write_text(test_content, encoding='utf-8')
        logger.info(f"✅ 创建测试文件: {test_file}")

        # 创建文件记录
        file_record_id = await db_manager.insert_file(
            file_id="content_test_001",
            original_name="content_test.txt",
            file_name="content_test.txt",
            file_path=str(test_file),
            file_type=".txt",
            file_size=len(test_content.encode('utf-8'))
        )
        logger.info(f"✅ 创建文件记录: content_test_001 (DB ID: {file_record_id})")

        # 测试获取文件内容
        logger.info("🔍 测试获取文件内容...")
        response = await get_file_content("content_test_001")

        if response.code == 200:
            logger.info("✅ 成功获取文件内容")
            logger.info(f"📄 文件名: {response.data.original_name}")
            logger.info(f"📝 文件类型: {response.data.file_type}")
            logger.info(f"📏 文件大小: {response.data.file_size} bytes")
            logger.info(f"📅 创建时间: {response.data.created_at}")
            logger.info(
                f"✅ 向量化状态: {'已完成' if response.data.vectorized else '未完成'}")
            logger.info("📖 文件内容:")
            logger.info("=" * 50)
            logger.info(response.data.content)
            logger.info("=" * 50)

            # 验证内容是否正确
            if response.data.content.strip() == test_content.strip():
                logger.info("✅ 文件内容读取正确")
            else:
                logger.error("❌ 文件内容读取不匹配")
                logger.error(f"期望内容长度: {len(test_content)}")
                logger.error(f"实际内容长度: {len(response.data.content)}")
        else:
            logger.error(f"❌ 获取文件内容失败: {response.msg}")

        # 测试不存在的文件
        logger.info("\n🔍 测试获取不存在的文件...")
        response_404 = await get_file_content("nonexistent_file")
        if response_404.code == 404:
            logger.info("✅ 正确处理不存在的文件")
        else:
            logger.error(f"❌ 处理不存在文件的逻辑有误: {response_404.code}")

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        raise
    finally:
        # 清理测试文件
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
            logger.info("🗑️ 清理测试文件")

        # 清理数据库记录
        try:
            await db_manager.delete_file_and_documents("content_test_001")
            logger.info("🗑️ 清理数据库记录")
        except Exception as e:
            logger.warning(f"清理数据库记录失败: {e}")

    logger.info("🎉 文件内容查看功能测试完成!")


async def main():
    """主函数"""
    try:
        await test_file_content_api()
        logger.info("✅ 测试成功完成")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
