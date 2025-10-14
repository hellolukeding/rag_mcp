#!/usr/bin/env python3
"""
完整系统测试
测试向量化服务的完整流程：文件上传 -> 向量化 -> 查询 -> 删除
"""

import asyncio
import os
import shutil
import tempfile
from pathlib import Path

from core.vectorize import get_vectorize_service
from database.models import DatabaseManager
from utils.logger import setup_logger

# 设置日志
logger = setup_logger(__name__)


async def test_complete_system():
    """测试完整系统流程"""
    logger.info("🚀 开始完整系统测试...")

    # 初始化数据库
    db_manager = DatabaseManager()
    await db_manager.init_database()
    logger.info("✅ 数据库初始化完成")

    # 获取向量化服务
    vectorize_service = get_vectorize_service()
    vectorize_service.start()
    logger.info("✅ 向量化服务启动完成")

    try:
        # 创建测试目录
        test_dir = Path("test/temp_system_test")
        test_dir.mkdir(exist_ok=True)

        # 创建多个测试文件
        test_files = []
        test_contents = [
            "这是第一个测试文档，包含关于人工智能的内容。",
            "这是第二个测试文档，讨论机器学习和深度学习技术。",
            "这是第三个测试文档，介绍自然语言处理的应用。"
        ]

        logger.info("📝 创建测试文件...")
        for i, content in enumerate(test_contents, 1):
            file_path = test_dir / f"test_doc_{i}.txt"
            file_path.write_text(content, encoding='utf-8')
            test_files.append(file_path)
            logger.info(f"✅ 创建测试文件: {file_path.name}")

        # 1. 测试文件上传和记录创建
        logger.info("\n🔄 步骤1: 测试文件上传和记录创建...")
        file_records = []
        for file_path in test_files:
            # 模拟文件上传
            file_record = await db_manager.create_file_record(
                file_id=f"test_{file_path.stem}",
                original_name=file_path.name,
                file_name=file_path.name,
                file_path=str(file_path),
                file_type="text/plain",
                file_size=file_path.stat().st_size
            )
            file_records.append(file_record)
            logger.info(f"✅ 创建文件记录: {file_record.file_id}")

        # 2. 测试向量化
        logger.info("\n🔄 步骤2: 测试文件向量化...")
        tasks = []
        for file_record in file_records:
            task = vectorize_service.add_task(file_record)
            tasks.append(task)
            logger.info(f"✅ 添加向量化任务: {task.task_id}")

        # 等待所有向量化任务完成
        logger.info("⏳ 等待向量化完成...")
        completed_count = 0
        while completed_count < len(tasks):
            await asyncio.sleep(0.5)
            completed_count = sum(
                1 for task in tasks if task.status == "completed")
            progress = (completed_count / len(tasks)) * 100
            logger.info(
                f"📊 向量化进度: {progress:.1f}% ({completed_count}/{len(tasks)})")

        logger.info("✅ 所有文件向量化完成!")

        # 3. 验证向量化结果
        logger.info("\n🔄 步骤3: 验证向量化结果...")
        for file_record in file_records:
            # 检查文件状态
            updated_record = await db_manager.get_file_by_id(file_record.file_id)
            if updated_record.vectorized == 'completed':
                logger.info(f"✅ 文件 {updated_record.file_name} 向量化成功")
            else:
                logger.error(f"❌ 文件 {updated_record.file_name} 向量化失败")

            # 检查文档记录
            documents = await db_manager.get_documents_by_file_id(file_record.file_id)
            if documents:
                logger.info(f"📑 文档记录存在: {len(documents)} 个")

                # 检查文档块
                for doc in documents:
                    chunks = await db_manager.get_chunks_by_document_id(doc.id)
                    logger.info(f"🧩 文档 {doc.id} 有 {len(chunks)} 个向量块")
            else:
                logger.error(f"❌ 未找到文档记录")

        # 4. 测试数据统计
        logger.info("\n🔄 步骤4: 检查数据统计...")

        # 统计数据
        async with db_manager.get_connection() as db:
            # 文件统计
            async with db.execute("SELECT COUNT(*) FROM files") as cursor:
                files_count = await cursor.fetchone()
                logger.info(f"📄 总文件数: {files_count[0]}")

            # 文档统计
            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                docs_count = await cursor.fetchone()
                logger.info(f"📑 总文档数: {docs_count[0]}")

            # 向量块统计
            async with db.execute("SELECT COUNT(*) FROM document_chunks") as cursor:
                chunks_count = await cursor.fetchone()
                logger.info(f"🧩 总向量块数: {chunks_count[0]}")

            # 已向量化文件统计
            async with db.execute("SELECT COUNT(*) FROM files WHERE vectorized = 'completed'") as cursor:
                vectorized_count = await cursor.fetchone()
                logger.info(f"✅ 已向量化文件数: {vectorized_count[0]}")

        # 5. 测试删除功能
        logger.info("\n🔄 步骤5: 测试文件删除功能...")

        # 删除第一个文件
        test_file_record = file_records[0]
        logger.info(f"🗑️ 删除文件: {test_file_record.file_name}")

        success = await db_manager.delete_file_and_documents(test_file_record.file_id)
        if success:
            logger.info("✅ 文件删除成功")

            # 验证删除结果
            deleted_file = await db_manager.get_file_by_id(test_file_record.file_id)
            if deleted_file is None:
                logger.info("✅ 文件记录已删除")
            else:
                logger.error("❌ 文件记录未删除")

            # 检查相关文档是否删除
            documents = await db_manager.get_documents_by_file_id(test_file_record.file_id)
            if not documents:
                logger.info("✅ 相关文档已删除")
            else:
                logger.error(f"❌ 仍有 {len(documents)} 个文档未删除")
        else:
            logger.error("❌ 文件删除失败")

        # 6. 最终统计
        logger.info("\n🔄 步骤6: 最终数据统计...")
        async with db_manager.get_connection() as db:
            async with db.execute("SELECT COUNT(*) FROM files") as cursor:
                final_files_count = await cursor.fetchone()
                logger.info(f"📄 最终文件数: {final_files_count[0]}")

            async with db.execute("SELECT COUNT(*) FROM documents") as cursor:
                final_docs_count = await cursor.fetchone()
                logger.info(f"📑 最终文档数: {final_docs_count[0]}")

            async with db.execute("SELECT COUNT(*) FROM document_chunks") as cursor:
                final_chunks_count = await cursor.fetchone()
                logger.info(f"🧩 最终向量块数: {final_chunks_count[0]}")

        logger.info("🎉 完整系统测试完成!")

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        raise
    finally:
        # 停止向量化服务
        vectorize_service.stop()
        logger.info("🛑 向量化服务已停止")

        # 清理测试文件
        if test_dir.exists():
            shutil.rmtree(test_dir)
            logger.info("🗑️ 清理测试文件")


async def main():
    """主函数"""
    try:
        await test_complete_system()
        logger.info("✅ 测试成功完成")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
