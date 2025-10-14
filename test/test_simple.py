#!/usr/bin/env python3
"""
简化版向量化测试 - 快速验证功能
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

from core.vectorize import TaskFile, get_vectorize_instance
from database.models import db_manager
from utils.logger import logger

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))


async def simple_test():
    """简单的向量化功能测试"""

    logger.info("🚀 开始简化向量化测试")

    # 1. 初始化数据库
    await db_manager.init_database()
    logger.info("✅ 数据库初始化完成")

    # 2. 获取向量化服务
    vectorize_service = get_vectorize_instance()
    logger.info("✅ 向量化服务启动完成")

    # 3. 创建测试文件
    test_dir = Path(__file__).parent / "temp"
    test_dir.mkdir(exist_ok=True)

    test_file = test_dir / "simple_test.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("""
这是一个简单的测试文档。

人工智能技术正在快速发展，深度学习算法在各个领域都有广泛应用。
自然语言处理、计算机视觉、语音识别等技术不断取得突破。
未来人工智能将会在更多场景中发挥重要作用。

向量数据库作为AI应用的重要基础设施，为语义搜索和推荐系统提供支持。
""")

    logger.info(f"✅ 创建测试文件: {test_file}")

    # 4. 创建向量化任务
    task_file = TaskFile(
        file_id=str(uuid.uuid4()),
        original_name="simple_test.txt",
        file_name="simple_test.txt",
        file_path=str(test_file),
        file_type=".txt",
        file_size=test_file.stat().st_size
    )

    task_id = vectorize_service.add_task(task_file)
    logger.info(f"✅ 添加向量化任务: {task_id[:8]}...")

    # 5. 等待任务完成
    logger.info("⏳ 等待向量化完成...")

    for i in range(30):  # 最多等待30秒
        await asyncio.sleep(1)

        status = vectorize_service.get_task_status(task_id)
        if status:
            current_status = status['status']
            progress = status['progress']

            if current_status == 'completed':
                logger.info(f"🎉 向量化成功完成! 进度: {progress:.1f}%")
                break
            elif current_status == 'failed':
                logger.error(f"❌ 向量化失败: {status.get('error_message', '未知错误')}")
                break
            else:
                logger.info(f"📊 进度: {progress:.1f}% - {current_status}")
        else:
            logger.warning("⚠️ 无法获取任务状态")

    # 6. 检查数据库结果
    logger.info("🔍 检查数据库结果...")

    # 检查文件记录
    files = await db_manager.get_all_files()
    vectorized_files = [f for f in files if f.get('vectorized')]
    logger.info(f"📁 文件记录: {len(files)} 个, 其中 {len(vectorized_files)} 个已向量化")

    # 检查文档块
    try:
        all_chunks = await db_manager.get_all_document_chunks()
        logger.info(f"🧩 文档块: {len(all_chunks)} 个")

        if all_chunks:
            # 显示第一个块的信息
            first_chunk = all_chunks[0]
            embedding_dim = len(first_chunk['embedding'])
            logger.info(f"📊 向量维度: {embedding_dim}")
            logger.info(f"📝 文本块示例: {first_chunk['content'][:50]}...")

    except Exception as e:
        logger.error(f"❌ 获取文档块失败: {e}")

    # 7. 测试状态API
    logger.info("🔍 测试状态API...")

    for file_info in files:
        status = await vectorize_service.get_file_vectorized_status(file_info['file_id'])
        if status:
            vec_status = "✅ 已向量化" if status['vectorized'] else "❌ 未向量化"
            logger.info(f"📄 {status['original_name']}: {vec_status}")

    # 8. 清理
    vectorize_service.stop()
    logger.info("🛑 向量化服务已停止")

    # 删除测试文件
    try:
        import shutil
        shutil.rmtree(test_dir)
        logger.info("🗑️ 清理测试文件")
    except Exception as e:
        logger.warning(f"⚠️ 清理失败: {e}")

    logger.info("🎊 简化测试完成!")


async def main():
    """主函数"""
    try:
        await simple_test()
        logger.info("✅ 测试成功完成")
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    # 检查环境变量
    required_env = ["OPENAI_API_KEY", "OPENAI_URL", "MODEL_NAME"]
    missing = [env for env in required_env if not os.getenv(env)]

    if missing:
        logger.error(f"❌ 缺少环境变量: {', '.join(missing)}")
        sys.exit(1)

    logger.info("🧪 环境变量检查通过，开始测试...")
    asyncio.run(main())
