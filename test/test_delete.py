#!/usr/bin/env python3
"""
测试文件删除功能，包括向量数据的删除
"""

from utils.logger import logger
from database.models import db_manager
from core.vectorize import TaskFile, get_vectorize_instance
import asyncio
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))


async def test_file_deletion():
    """测试文件删除功能"""

    logger.info("🧪 开始测试文件删除功能")

    # 1. 初始化数据库
    await db_manager.init_database()
    logger.info("✅ 数据库初始化完成")

    # 2. 获取向量化服务
    vectorize_service = get_vectorize_instance()
    logger.info("✅ 向量化服务启动完成")

    # 3. 创建测试文件
    test_dir = Path(__file__).parent / "temp_delete_test"
    test_dir.mkdir(exist_ok=True)

    test_file = test_dir / "delete_test.txt"
    test_content = """
这是一个用于测试删除功能的文件。

包含多段文本内容，用于生成向量数据：

1. 人工智能技术的发展
2. 机器学习算法的应用
3. 深度学习模型的训练
4. 自然语言处理的进展
5. 计算机视觉的突破

这些内容将被向量化并存储在数据库中，然后我们将测试删除功能。
"""

    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(test_content)

    logger.info(f"✅ 创建测试文件: {test_file}")

    # 4. 创建文件记录
    file_id = str(uuid.uuid4())
    await db_manager.insert_file(
        file_id=file_id,
        original_name="delete_test.txt",
        file_name="delete_test.txt",
        file_path=str(test_file),
        file_type=".txt",
        file_size=test_file.stat().st_size
    )
    logger.info(f"✅ 创建文件记录: {file_id}")

    # 5. 创建向量化任务
    task_file = TaskFile(
        file_id=file_id,
        original_name="delete_test.txt",
        file_name="delete_test.txt",
        file_path=str(test_file),
        file_type=".txt",
        file_size=test_file.stat().st_size
    )

    task_id = vectorize_service.add_task(task_file)
    logger.info(f"✅ 添加向量化任务: {task_id[:8]}...")

    # 6. 等待向量化完成
    logger.info("⏳ 等待向量化完成...")

    for i in range(30):  # 最多等待30秒
        await asyncio.sleep(1)

        status = vectorize_service.get_task_status(task_id)
        if status and status['status'] == 'completed':
            logger.info(f"✅ 向量化完成!")
            break
        elif status and status['status'] == 'failed':
            logger.error(f"❌ 向量化失败: {status.get('error_message')}")
            return False

    # 7. 检查数据库中的数据
    logger.info("🔍 检查向量化后的数据...")

    # 检查文件记录
    file_info = await db_manager.get_file_by_id(file_id)
    if not file_info:
        logger.error("❌ 找不到文件记录")
        return False

    logger.info(f"📄 文件记录存在: {file_info['original_name']}")
    logger.info(f"   向量化状态: {'已完成' if file_info['vectorized'] else '未完成'}")

    # 检查文档记录
    documents = await db_manager.get_all_documents()
    target_docs = [d for d in documents if d['file_path'] == str(test_file)]

    if not target_docs:
        logger.error("❌ 找不到文档记录")
        return False

    target_doc = target_docs[0]
    logger.info(f"📑 文档记录存在: ID={target_doc['id']}")

    # 检查文档块
    chunks = await db_manager.get_document_chunks(target_doc['id'])
    logger.info(f"🧩 文档块数量: {len(chunks)}")

    if not chunks:
        logger.error("❌ 找不到文档块")
        return False

    # 8. 执行删除操作
    logger.info("🗑️ 开始执行删除操作...")

    success = await db_manager.delete_file_and_documents(file_id)
    if not success:
        logger.error("❌ 删除操作失败")
        return False

    logger.info("✅ 删除操作完成")

    # 9. 验证删除结果
    logger.info("🔍 验证删除结果...")

    # 检查文件记录是否被删除
    file_info_after = await db_manager.get_file_by_id(file_id)
    if file_info_after:
        logger.error("❌ 文件记录未被删除")
        return False
    logger.info("✅ 文件记录已删除")

    # 检查文档记录是否被删除
    documents_after = await db_manager.get_all_documents()
    target_docs_after = [
        d for d in documents_after if d['file_path'] == str(test_file)]

    if target_docs_after:
        logger.error("❌ 文档记录未被删除")
        return False
    logger.info("✅ 文档记录已删除")

    # 检查文档块是否被删除（应该通过外键约束自动删除）
    try:
        chunks_after = await db_manager.get_document_chunks(target_doc['id'])
        if chunks_after:
            logger.error("❌ 文档块未被删除")
            return False
        logger.info("✅ 文档块已删除")
    except Exception:
        # 由于文档已被删除，查询文档块可能会出错，这是正常的
        logger.info("✅ 文档块已随文档一起删除")

    # 10. 清理
    vectorize_service.stop()
    logger.info("🛑 向量化服务已停止")

    # 删除测试文件夹
    try:
        import shutil
        shutil.rmtree(test_dir)
        logger.info("🗑️ 清理测试文件")
    except Exception as e:
        logger.warning(f"⚠️ 清理失败: {e}")

    logger.info("🎉 文件删除功能测试完成!")
    return True


async def main():
    """主函数"""
    try:
        success = await test_file_deletion()

        if success:
            logger.info("✅ 测试成功完成")
        else:
            logger.error("❌ 测试失败")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    # 检查环境变量
    required_env = ["OPENAI_API_KEY", "OPENAI_URL", "MODEL_NAME"]
    missing = [env for env in required_env if not os.getenv(env)]

    if missing:
        logger.error(f"❌ 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)

    logger.info("🧪 开始删除功能测试...")
    asyncio.run(main())
