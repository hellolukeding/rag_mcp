#!/usr/bin/env python3
"""
测试新的向量化状态功能
包括: pending, processing, completed, failed 四种状态
"""

from utils.logger import logger
from database.models import DatabaseManager
from core.vectorize import get_vectorize_instance
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))


async def test_vectorization_status():
    """测试向量化状态变化"""
    logger.info("🧪 开始测试向量化状态功能...")

    # 初始化数据库
    db_manager = DatabaseManager()
    await db_manager.init_database()
    logger.info("✅ 数据库初始化完成")

    # 获取向量化服务
    vectorize_service = get_vectorize_instance()
    vectorize_service.start()
    logger.info("✅ 向量化服务启动完成")

    try:
        # 创建测试目录和文件
        test_dir = Path("test/temp_status_test")
        test_dir.mkdir(exist_ok=True)

        test_file = test_dir / "status_test.md"
        test_content = """# 向量化状态测试

这是一个用于测试向量化状态变化的文档。

## 测试内容

- pending: 初始状态，文件已上传但未开始向量化
- processing: 正在向量化处理中
- completed: 向量化成功完成
- failed: 向量化失败

## 测试流程

1. 创建文件记录（状态应为 pending）
2. 启动向量化任务（状态应变为 processing）  
3. 等待向量化完成（状态应变为 completed）
4. 验证最终状态和数据

这个测试将验证整个状态变化流程是否正常工作。
"""

        test_file.write_text(test_content, encoding='utf-8')
        logger.info(f"✅ 创建测试文件: {test_file}")

        # 1. 创建文件记录，初始状态应为 pending
        logger.info("\n📝 步骤1: 创建文件记录，检查初始状态...")

        await db_manager.insert_file(
            file_id="status_test_file",
            original_name="status_test.md",
            file_name="status_test.md",
            file_path=str(test_file),
            file_type=".md",
            file_size=test_file.stat().st_size
        )

        # 检查初始状态
        file_info = await db_manager.get_file_by_id("status_test_file")
        if file_info and file_info["vectorized"] == "pending":
            logger.info("✅ 初始状态正确: pending")
        else:
            logger.error(
                f"❌ 初始状态错误: {file_info['vectorized'] if file_info else 'None'}")

        # 2. 启动向量化任务，检查状态变为 processing
        logger.info("\n🔄 步骤2: 启动向量化任务，检查处理中状态...")

        # 创建任务文件对象
        from core.vectorize import TaskFile
        task_file = TaskFile(
            file_id="status_test_file",
            original_name="status_test.md",
            file_name="status_test.md",
            file_path=str(test_file),
            file_type=".md",
            file_size=test_file.stat().st_size
        )

        # 添加向量化任务
        task_id = vectorize_service.add_task(task_file)
        logger.info(f"✅ 向量化任务已创建: {task_id}")

        # 等待任务开始处理（状态变为 processing）
        processing_detected = False
        for i in range(20):  # 最多等待10秒
            await asyncio.sleep(0.5)
            file_info = await db_manager.get_file_by_id("status_test_file")
            if file_info["vectorized"] == "processing":
                logger.info("✅ 检测到处理中状态: processing")
                processing_detected = True
                break

        if not processing_detected:
            logger.warning("⚠️ 未检测到处理中状态，可能处理速度太快")

        # 3. 等待向量化完成，检查最终状态
        logger.info("\n⏳ 步骤3: 等待向量化完成...")

        completed = False
        for i in range(60):  # 最多等待30秒
            await asyncio.sleep(0.5)
            file_info = await db_manager.get_file_by_id("status_test_file")
            current_status = file_info["vectorized"]

            if i % 10 == 0:  # 每5秒输出一次状态
                logger.info(f"📊 当前状态: {current_status}")

            if current_status == "completed":
                logger.info("✅ 向量化成功完成: completed")
                completed = True
                break
            elif current_status == "failed":
                logger.error("❌ 向量化失败: failed")
                break

        if not completed and file_info["vectorized"] != "completed":
            logger.error(f"❌ 向量化未在预期时间内完成，最终状态: {file_info['vectorized']}")

        # 4. 验证数据完整性
        logger.info("\n🔍 步骤4: 验证数据完整性...")

        if completed:
            # 检查文档记录
            documents = await db_manager.get_documents_by_file_id("status_test_file")
            if documents:
                logger.info(f"✅ 文档记录存在: {len(documents)} 个")

                # 检查向量块
                for doc in documents:
                    chunks = await db_manager.get_chunks_by_document_id(doc.id)
                    logger.info(f"✅ 文档 {doc.id} 有 {len(chunks)} 个向量块")
            else:
                logger.error("❌ 未找到文档记录")

        # 5. 测试状态映射
        logger.info("\n📋 步骤5: 验证所有状态...")

        # 测试手动设置各种状态
        test_statuses = ["pending", "processing", "completed", "failed"]
        for status in test_statuses:
            success = await db_manager.update_file_vectorized_status("status_test_file", status)
            if success:
                file_info = await db_manager.get_file_by_id("status_test_file")
                if file_info["vectorized"] == status:
                    logger.info(f"✅ 状态 {status} 设置成功")
                else:
                    logger.error(f"❌ 状态 {status} 设置失败")

        # 6. 测试文件列表API响应格式
        logger.info("\n📋 步骤6: 测试API响应格式...")

        all_files = await db_manager.get_all_files()
        test_file_found = False
        for file_data in all_files:
            if file_data["file_id"] == "status_test_file":
                test_file_found = True
                logger.info(f"✅ 文件列表中找到测试文件")
                logger.info(f"📊 向量化状态: {file_data['vectorized']}")
                logger.info(
                    f"📅 向量化时间: {file_data.get('vectorized_at', 'None')}")
                break

        if not test_file_found:
            logger.error("❌ 文件列表中未找到测试文件")

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        raise
    finally:
        # 停止向量化服务
        vectorize_service.stop()
        logger.info("🛑 向量化服务已停止")

        # 清理测试数据
        try:
            await db_manager.delete_file_and_documents("status_test_file")
            logger.info("🗑️ 清理测试数据")
        except Exception as e:
            logger.warning(f"清理测试数据失败: {e}")

        # 清理测试文件
        import shutil
        test_dir = Path("test/temp_status_test")
        if test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info("🗑️ 清理测试文件")


async def main():
    """主函数"""
    try:
        await test_vectorization_status()
        logger.info("✅ 向量化状态测试完成")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
