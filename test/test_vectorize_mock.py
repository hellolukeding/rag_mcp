#!/usr/bin/env python3
"""
向量化服务模拟测试脚本
使用模拟的向量化API测试功能
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

from core.vectorize import TaskFile, Vectorize
from database.models import db_manager
from utils.logger import logger

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))


class MockVectorizeService(Vectorize):
    """模拟向量化服务，不调用真实API"""

    def __init__(self, max_workers: int = 2):
        super().__init__(max_workers)
        # 重写向量化客户端的方法
        self.queue._get_embeddings_batch = self._mock_get_embeddings_batch

    async def _mock_get_embeddings_batch(self, texts):
        """模拟获取向量化结果"""
        # 模拟网络延迟
        await asyncio.sleep(0.5)

        # 返回模拟的向量数据 (768维向量)
        mock_embeddings = []
        for text in texts:
            # 生成基于文本长度的模拟向量
            embedding = [0.1 * (i % 10) for i in range(768)]
            mock_embeddings.append(embedding)

        logger.info(f"模拟向量化完成，处理了 {len(texts)} 个文本块")
        return mock_embeddings


async def setup():
    """初始化测试环境"""
    logger.info("=" * 80)
    logger.info("开始模拟向量化服务测试")
    logger.info("=" * 80)

    # 初始化数据库
    await db_manager.init_database()
    logger.info("数据库初始化完成")

    # 创建模拟向量化服务
    vectorize_service = MockVectorizeService(max_workers=1)
    vectorize_service.start()
    logger.info("模拟向量化服务启动完成")

    return vectorize_service


def create_test_files():
    """创建测试文件"""
    test_dir = Path(__file__).parent

    # 创建测试文档1
    doc1_path = test_dir / "mock_test_doc1.txt"
    with open(doc1_path, 'w', encoding='utf-8') as f:
        f.write("""
这是一个测试文档，用于验证向量化功能。

第一段：介绍人工智能的基本概念。人工智能（AI）是计算机科学的一个重要分支，旨在创建能够模拟人类智能行为的机器和系统。

第二段：机器学习是人工智能的核心技术之一。通过算法让计算机从数据中学习模式，无需明确编程即可执行特定任务。

第三段：深度学习作为机器学习的子集，使用多层神经网络来处理复杂的数据模式，在图像识别、自然语言处理等领域取得了突破性进展。

第四段：未来人工智能将在医疗、教育、交通、金融等各个领域发挥更重要的作用，推动社会向智能化方向发展。
""")

    # 创建测试文档2
    doc2_path = test_dir / "mock_test_doc2.txt"
    with open(doc2_path, 'w', encoding='utf-8') as f:
        f.write("""
云计算技术概述文档

云计算是一种基于互联网的计算方式，通过网络以按需、易扩展的方式获得所需的计算资源。

服务模型：
- IaaS（基础设施即服务）：提供虚拟化的计算资源
- PaaS（平台即服务）：提供应用开发和部署平台  
- SaaS（软件即服务）：提供完整的软件应用

部署模式：
- 公有云：由第三方云服务提供商拥有和运营
- 私有云：专门为单个组织建立和维护
- 混合云：结合公有云和私有云的优势

主要优势包括成本效益、弹性扩展、高可用性和快速部署等特点。
""")

    logger.info(f"创建了 2 个测试文件")
    return [doc1_path, doc2_path]


async def test_mock_vectorization(vectorize_service, test_files):
    """测试模拟向量化功能"""
    logger.info("=" * 80)
    logger.info("测试: 模拟向量化功能")
    logger.info("=" * 80)

    task_ids = []

    for test_file in test_files:
        # 创建任务文件对象
        task_file = TaskFile(
            file_id=str(uuid.uuid4()),
            original_name=test_file.name,
            file_name=test_file.name,
            file_path=str(test_file),
            file_type=test_file.suffix,
            file_size=test_file.stat().st_size
        )

        # 添加任务
        task_id = vectorize_service.add_task(task_file)
        task_ids.append(task_id)
        logger.info(
            f"添加模拟向量化任务: {task_id[:8]}..., 文件: {task_file.original_name}")

    # 等待所有任务完成
    results = []
    for task_id in task_ids:
        result = await wait_for_task_completion(vectorize_service, task_id, timeout=60)
        results.append(result)

    return results


async def wait_for_task_completion(vectorize_service, task_id, timeout=30):
    """等待任务完成"""
    logger.info(f"等待任务 {task_id[:8]}... 完成")

    start_time = time.time()

    while time.time() - start_time < timeout:
        task_status = vectorize_service.get_task_status(task_id)

        if not task_status:
            logger.error(f"任务 {task_id} 未找到")
            return None

        status = task_status['status']
        progress = task_status['progress']

        logger.info(f"任务进度: {progress:.1f}% - {status}")

        if status == 'completed':
            logger.info(f"✅ 任务 {task_id[:8]}... 完成成功!")
            return task_status
        elif status == 'failed':
            logger.error(
                f"❌ 任务 {task_id[:8]}... 失败: {task_status.get('error_message', '未知错误')}")
            return task_status

        # 等待一段时间后重新检查
        await asyncio.sleep(1)

    logger.warning(f"⏰ 任务 {task_id[:8]}... 超时")
    return None


async def test_database_results():
    """测试数据库结果"""
    logger.info("=" * 80)
    logger.info("测试: 检查数据库结果")
    logger.info("=" * 80)

    # 检查文件记录
    all_files = await db_manager.get_all_files()
    logger.info(f"📁 数据库中共有 {len(all_files)} 个文件记录")

    vectorized_count = 0
    for file_info in all_files:
        status = "✅ 已向量化" if file_info['vectorized'] else "❌ 未向量化"
        logger.info(f"  📄 {file_info['original_name']} - {status}")
        if file_info['vectorized']:
            vectorized_count += 1
            logger.info(f"     向量化时间: {file_info['vectorized_at']}")

    logger.info(f"📊 向量化统计: {vectorized_count}/{len(all_files)} 个文件已向量化")

    # 检查文档块
    all_chunks = await db_manager.get_all_document_chunks()
    logger.info(f"🧩 数据库中共有 {len(all_chunks)} 个文档块")

    # 按文档统计
    doc_chunks = {}
    for chunk in all_chunks:
        doc_id = chunk['document_id']
        if doc_id not in doc_chunks:
            doc_chunks[doc_id] = []
        doc_chunks[doc_id].append(chunk)

    for doc_id, chunks in doc_chunks.items():
        logger.info(f"  📑 文档 {doc_id}: {len(chunks)} 个文本块")
        # 显示第一个块的向量维度
        if chunks:
            embedding = chunks[0]['embedding']
            logger.info(f"     向量维度: {len(embedding)}")


async def test_vectorized_status_api(vectorize_service):
    """测试向量化状态API"""
    logger.info("=" * 80)
    logger.info("测试: 向量化状态API")
    logger.info("=" * 80)

    # 获取所有文件
    all_files = await db_manager.get_all_files()

    for file_info in all_files:
        file_id = file_info['file_id']

        # 使用向量化服务的API获取状态
        status = await vectorize_service.get_file_vectorized_status(file_id)

        if status:
            logger.info(f"📄 {status['original_name']}")
            logger.info(
                f"   状态: {'✅ 已向量化' if status['vectorized'] else '❌ 未向量化'}")
            if status['vectorized_at']:
                logger.info(f"   时间: {status['vectorized_at']}")
        else:
            logger.warning(f"❌ 无法获取文件 {file_id} 的状态")

    # 获取未向量化文件
    unvectorized = await vectorize_service.get_unvectorized_files()
    logger.info(f"📋 未向量化文件: {len(unvectorized)} 个")


async def main():
    """主测试函数"""
    try:
        # 初始化
        vectorize_service = await setup()

        # 创建测试文件
        test_files = create_test_files()

        # 测试模拟向量化
        await test_mock_vectorization(vectorize_service, test_files)

        # 等待一下确保所有任务完成
        await asyncio.sleep(2)

        # 检查数据库结果
        await test_database_results()

        # 测试状态API
        await test_vectorized_status_api(vectorize_service)

        logger.info("=" * 80)
        logger.info("🎉 所有模拟测试完成!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ 测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        # 停止向量化服务
        if 'vectorize_service' in locals():
            vectorize_service.stop()
            logger.info("向量化服务已停止")


if __name__ == "__main__":
    # 设置模拟环境变量（如果不存在）
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "mock-key"
    if not os.getenv("OPENAI_URL"):
        os.environ["OPENAI_URL"] = "https://mock-api.example.com"
    if not os.getenv("MODEL_NAME"):
        os.environ["MODEL_NAME"] = "mock-model"

    logger.info("🧪 运行模拟向量化测试")

    # 运行测试
    asyncio.run(main())
