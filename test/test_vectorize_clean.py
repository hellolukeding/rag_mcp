#!/usr/bin/env python3
"""
向量化服务测试脚本
测试 core.vectorlize 模块的功能
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

from core.vectorize import TaskFile, Vectorize, get_vectorize_instance
from database.models import db_manager
from utils.logger import logger

# 加载环境变量
load_dotenv()

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

# 导入项目模块


async def setup():
    """初始化测试环境"""
    logger.info("=" * 80)
    logger.info("开始向量化服务测试")
    logger.info("=" * 80)

    # 初始化数据库
    await db_manager.init_database()
    logger.info("数据库初始化完成")

    # 获取向量化服务实例
    vectorize_service = get_vectorize_instance()
    logger.info("向量化服务获取完成")

    return vectorize_service


def create_test_files():
    """创建测试文件"""
    test_dir = Path(__file__).parent

    # 创建测试文档1
    doc1_path = test_dir / "test_ai_document.txt"
    with open(doc1_path, 'w', encoding='utf-8') as f:
        f.write("""
人工智能的发展历程

人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。

历史发展：
1. 1950年代：图灵测试的提出
2. 1960年代：专家系统的兴起
3. 1980年代：机器学习算法的突破
4. 2000年代：深度学习的革命
5. 2020年代：大语言模型的爆发

应用领域：
- 自然语言处理
- 计算机视觉
- 语音识别
- 自动驾驶
- 医疗诊断
- 金融分析

未来展望：
人工智能将继续在各个领域发挥重要作用，推动社会的数字化转型。
""")

    # 创建测试文档2
    doc2_path = test_dir / "test_tech_document.txt"
    with open(doc2_path, 'w', encoding='utf-8') as f:
        f.write("""
云计算技术概述

云计算是一种按使用量付费的模式，这种模式提供可用的、便捷的、按需的网络访问，进入可配置的计算资源共享池。

服务模式：
1. IaaS (Infrastructure as a Service) - 基础设施即服务
2. PaaS (Platform as a Service) - 平台即服务  
3. SaaS (Software as a Service) - 软件即服务

部署模式：
- 公有云
- 私有云
- 混合云
- 多云

主要优势：
- 成本降低
- 弹性扩展
- 高可用性
- 快速部署

技术架构：
云计算基于虚拟化、分布式计算、并行计算等技术构建。
""")

    logger.info(f"创建了 2 个测试文件")
    return [doc1_path, doc2_path]


async def test_add_single_task(vectorize_service, test_files):
    """测试添加单个向量化任务"""
    logger.info("=" * 80)
    logger.info("测试1: 添加单个向量化任务")
    logger.info("=" * 80)

    test_file = test_files[0]

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

    logger.info(f"添加任务成功，任务ID: {task_id}")
    logger.info(f"文件名: {task_file.original_name}")

    # 等待任务完成
    result = await wait_for_task_completion(vectorize_service, task_id)
    return result


async def test_add_multiple_tasks(vectorize_service, test_files):
    """测试添加多个向量化任务"""
    logger.info("=" * 80)
    logger.info("测试2: 添加多个向量化任务")
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
        logger.info(f"添加任务成功，任务ID: {task_id}, 文件: {task_file.original_name}")

    # 等待所有任务完成
    results = []
    for task_id in task_ids:
        result = await wait_for_task_completion(vectorize_service, task_id)
        results.append(result)

    return results


async def test_get_task_status(vectorize_service):
    """测试获取任务状态"""
    logger.info("=" * 80)
    logger.info("测试3: 获取所有任务状态")
    logger.info("=" * 80)

    all_tasks = vectorize_service.get_all_tasks()

    for task in all_tasks:
        logger.info(f"任务ID: {task['task_id']}")
        logger.info(f"文件名: {task['original_name']}")
        logger.info(f"状态: {task['status']}")
        logger.info(f"进度: {task['progress']:.1f}%")
        logger.info(f"块总数: {task['chunks_total']}")
        logger.info(f"已处理块数: {task['chunks_processed']}")
        if task['error_message']:
            logger.error(f"错误信息: {task['error_message']}")
        logger.info("-" * 40)


async def test_database_status():
    """测试数据库状态"""
    logger.info("=" * 80)
    logger.info("测试4: 检查数据库状态")
    logger.info("=" * 80)

    # 检查文件记录
    all_files = await db_manager.get_all_files()
    logger.info(f"数据库中共有 {len(all_files)} 个文件记录")

    for file_info in all_files:
        logger.info(f"文件ID: {file_info['file_id']}")
        logger.info(f"文件名: {file_info['original_name']}")
        logger.info(f"向量化状态: {'已向量化' if file_info['vectorized'] else '未向量化'}")
        logger.info(f"向量化时间: {file_info['vectorized_at']}")
        logger.info("-" * 40)

    # 检查未向量化的文件
    unvectorized_files = await db_manager.get_unvectorized_files()
    logger.info(f"未向量化的文件: {len(unvectorized_files)} 个")


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
            logger.info(f"任务 {task_id[:8]}... 完成成功!")
            return task_status
        elif status == 'failed':
            logger.error(
                f"任务 {task_id[:8]}... 失败: {task_status.get('error_message', '未知错误')}")
            return task_status

        # 等待一段时间后重新检查
        await asyncio.sleep(2)

    logger.warning(f"任务 {task_id[:8]}... 超时")
    return None


async def main():
    """主测试函数"""
    try:
        # 初始化
        vectorize_service = await setup()

        # 创建测试文件
        test_files = create_test_files()

        # 测试1: 添加单个任务
        await test_add_single_task(vectorize_service, test_files)

        # 等待一下
        await asyncio.sleep(2)

        # 测试2: 添加多个任务
        await test_add_multiple_tasks(vectorize_service, test_files)

        # 等待一下
        await asyncio.sleep(2)

        # 测试3: 获取任务状态
        await test_get_task_status(vectorize_service)

        # 测试4: 检查数据库状态
        await test_database_status()

        logger.info("=" * 80)
        logger.info("所有测试完成!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}")
        import traceback
        logger.error(traceback.format_exc())

    finally:
        # 停止向量化服务
        vectorize_service.stop()
        logger.info("向量化服务已停止")


if __name__ == "__main__":
    # 检查环境变量
    required_env = ["OPENAI_API_KEY", "OPENAI_URL", "MODEL_NAME"]
    missing_env = [env for env in required_env if not os.getenv(env)]

    if missing_env:
        logger.error(f"缺少环境变量: {', '.join(missing_env)}")
        logger.info("请在 .env 文件中设置以下变量:")
        for env in required_env:
            logger.info(f"  {env}=your_value")
        sys.exit(1)

    # 运行测试
    asyncio.run(main())
