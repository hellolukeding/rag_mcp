#!/usr/bin/env python3
"""
向量化服务性能测试脚本
测试向量化服务的并发处理能力和性能指标
"""

import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from typing import List

from core.vectorize import (TaskFile, TaskStatus, Vectorize,
                            get_vectorize_instance)
from database.models import db_manager
from utils.logger import logger

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))


class VectorizePerformanceTest:
    """向量化性能测试类"""

    def __init__(self):
        self.vectorize_service = None
        self.test_files = []
        self.performance_metrics = {}

    async def setup(self):
        """测试前的设置"""
        logger.info("=" * 60)
        logger.info("向量化服务性能测试")
        logger.info("=" * 60)

        # 初始化数据库
        await db_manager.init_database()

        # 获取向量化服务实例
        self.vectorize_service = get_vectorize_instance()

        # 创建性能测试文件
        await self.create_performance_test_files()

    async def create_performance_test_files(self):
        """创建性能测试文件"""
        test_dir = Path(__file__).parent / "performance_test_data"
        test_dir.mkdir(exist_ok=True)

        # 创建不同大小的测试文件
        test_contents = {
            "small": self.generate_text_content(500),    # 500字符
            "medium": self.generate_text_content(2000),  # 2000字符
            "large": self.generate_text_content(8000),   # 8000字符
            "xlarge": self.generate_text_content(15000),  # 15000字符
        }

        for size, content in test_contents.items():
            # 创建多个同样大小的文件用于并发测试
            for i in range(3):
                filename = f"test_{size}_{i+1}.txt"
                test_file = test_dir / filename

                with open(test_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                # 创建TaskFile对象
                file_id = str(uuid.uuid4())
                task_file = TaskFile(
                    file_id=file_id,
                    original_name=filename,
                    file_name=filename,
                    file_path=str(test_file),
                    file_type=test_file.suffix,
                    file_size=test_file.stat().st_size
                )
                self.test_files.append((size, task_file))

        logger.info(f"创建了 {len(self.test_files)} 个性能测试文件")

    def generate_text_content(self, char_count: int) -> str:
        """生成指定字符数的测试文本"""
        base_text = """
        人工智能技术正在快速发展，深度学习和机器学习算法在各个领域都取得了突破性进展。
        自然语言处理技术使得计算机能够更好地理解和生成人类语言。
        向量化技术将文本转换为数值表示，为语义搜索和相似度计算提供了基础。
        大型语言模型的出现改变了人工智能的发展格局，为各种应用场景提供了强大的能力。
        机器学习模型的训练需要大量的计算资源和高质量的数据集。
        数据预处理和特征工程是机器学习项目中的重要环节。
        模型的评估和优化对于提高系统性能至关重要。
        """

        # 重复文本直到达到目标字符数
        repeated_text = ""
        while len(repeated_text) < char_count:
            repeated_text += base_text

        return repeated_text[:char_count]

    async def test_single_file_performance(self):
        """测试单文件处理性能"""
        logger.info("\n" + "=" * 50)
        logger.info("性能测试1: 单文件处理时间")
        logger.info("=" * 50)

        results = {}

        # 测试不同大小文件的处理时间
        size_files = {}
        for size, task_file in self.test_files:
            if size not in size_files:
                size_files[size] = task_file

        for size, task_file in size_files.items():
            logger.info(
                f"测试 {size} 文件: {task_file.original_name} ({task_file.file_size} 字节)")

            start_time = time.time()
            task_id = self.vectorize_service.add_task(task_file)

            # 等待任务完成
            await self.wait_for_task_completion(task_id)

            end_time = time.time()
            processing_time = end_time - start_time

            results[size] = {
                'file_size': task_file.file_size,
                'processing_time': processing_time,
                'chars_per_second': task_file.file_size / processing_time
            }

            logger.info(f"  处理时间: {processing_time:.2f}秒")
            logger.info(
                f"  处理速度: {results[size]['chars_per_second']:.2f} 字符/秒")

        self.performance_metrics['single_file'] = results
        return True

    async def test_concurrent_performance(self):
        """测试并发处理性能"""
        logger.info("\n" + "=" * 50)
        logger.info("性能测试2: 并发处理能力")
        logger.info("=" * 50)

        # 准备并发任务
        concurrent_files = [task_file for _, task_file in self.test_files]

        logger.info(f"准备并发处理 {len(concurrent_files)} 个文件")

        start_time = time.time()
        task_ids = []

        # 同时添加所有任务
        for task_file in concurrent_files:
            task_id = self.vectorize_service.add_task(task_file)
            task_ids.append(task_id)
            logger.info(f"添加任务: {task_file.original_name}")

        logger.info(f"所有任务已添加，开始并发处理...")

        # 等待所有任务完成
        await self.wait_for_all_tasks_completion(task_ids)

        end_time = time.time()
        total_time = end_time - start_time

        # 计算总文件大小
        total_size = sum(task_file.file_size for _,
                         task_file in self.test_files)

        results = {
            'total_files': len(concurrent_files),
            'total_size': total_size,
            'total_time': total_time,
            'throughput': total_size / total_time,
            'files_per_second': len(concurrent_files) / total_time
        }

        logger.info(f"并发处理结果:")
        logger.info(f"  总文件数: {results['total_files']}")
        logger.info(f"  总大小: {results['total_size']} 字节")
        logger.info(f"  总时间: {results['total_time']:.2f}秒")
        logger.info(f"  吞吐量: {results['throughput']:.2f} 字符/秒")
        logger.info(f"  文件处理速度: {results['files_per_second']:.2f} 文件/秒")

        self.performance_metrics['concurrent'] = results
        return True

    async def test_memory_usage_monitoring(self):
        """测试内存使用情况监控"""
        logger.info("\n" + "=" * 50)
        logger.info("性能测试3: 内存使用监控")
        logger.info("=" * 50)

        try:
            import psutil
            process = psutil.Process()

            # 记录初始内存使用
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            logger.info(f"初始内存使用: {initial_memory:.2f} MB")

            # 添加一些任务
            large_files = [task_file for size,
                           task_file in self.test_files if size == 'xlarge']
            task_ids = []

            for task_file in large_files:
                task_id = self.vectorize_service.add_task(task_file)
                task_ids.append(task_id)

            # 监控处理过程中的内存使用
            peak_memory = initial_memory
            while task_ids:
                current_memory = process.memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

                # 检查完成的任务
                completed_tasks = []
                for task_id in task_ids:
                    task_status = self.vectorize_service.get_task_status(
                        task_id)
                    if task_status and TaskStatus(task_status['status']) in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        completed_tasks.append(task_id)

                for task_id in completed_tasks:
                    task_ids.remove(task_id)

                if task_ids:
                    await asyncio.sleep(1)

            final_memory = process.memory_info().rss / 1024 / 1024

            results = {
                'initial_memory_mb': initial_memory,
                'peak_memory_mb': peak_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': peak_memory - initial_memory
            }

            logger.info(f"内存使用情况:")
            logger.info(f"  初始内存: {results['initial_memory_mb']:.2f} MB")
            logger.info(f"  峰值内存: {results['peak_memory_mb']:.2f} MB")
            logger.info(f"  最终内存: {results['final_memory_mb']:.2f} MB")
            logger.info(f"  内存增长: {results['memory_increase_mb']:.2f} MB")

            self.performance_metrics['memory'] = results

        except ImportError:
            logger.warning("psutil 未安装，跳过内存监控测试")
            logger.info("可通过 pip install psutil 安装内存监控依赖")

        return True

    async def test_error_handling_performance(self):
        """测试错误处理性能"""
        logger.info("\n" + "=" * 50)
        logger.info("性能测试4: 错误处理能力")
        logger.info("=" * 50)

        # 创建无效文件任务
        invalid_task_file = TaskFile(
            file_id=str(uuid.uuid4()),
            original_name="nonexistent.txt",
            file_name="nonexistent.txt",
            file_path="/nonexistent/path/file.txt",
            file_type=".txt",
            file_size=1000
        )

        start_time = time.time()
        task_id = self.vectorize_service.add_task(invalid_task_file)

        # 等待任务失败
        await self.wait_for_task_completion(task_id)

        end_time = time.time()
        error_handling_time = end_time - start_time

        task_status = self.vectorize_service.get_task_status(task_id)

        results = {
            'error_handling_time': error_handling_time,
            'task_failed_correctly': task_status['status'] == 'failed',
            'error_message': task_status.get('error_message', 'No error message')
        }

        logger.info(f"错误处理结果:")
        logger.info(f"  错误处理时间: {results['error_handling_time']:.2f}秒")
        logger.info(f"  任务正确失败: {results['task_failed_correctly']}")
        logger.info(f"  错误信息: {results['error_message']}")

        self.performance_metrics['error_handling'] = results
        return True

    async def wait_for_task_completion(self, task_id: str, timeout: int = 300):
        """等待单个任务完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            task_status = self.vectorize_service.get_task_status(task_id)

            if task_status:
                status = TaskStatus(task_status['status'])
                if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    return

            await asyncio.sleep(1)

    async def wait_for_all_tasks_completion(self, task_ids: List[str], timeout: int = 600):
        """等待所有任务完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            completed_count = 0

            for task_id in task_ids:
                task_status = self.vectorize_service.get_task_status(task_id)
                if task_status:
                    status = TaskStatus(task_status['status'])
                    if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        completed_count += 1

            logger.info(f"进度: {completed_count}/{len(task_ids)} 任务完成")

            if completed_count == len(task_ids):
                return

            await asyncio.sleep(3)

    def print_performance_summary(self):
        """打印性能测试总结"""
        logger.info("\n" + "=" * 60)
        logger.info("性能测试总结")
        logger.info("=" * 60)

        if 'single_file' in self.performance_metrics:
            logger.info("\n单文件处理性能:")
            for size, metrics in self.performance_metrics['single_file'].items():
                logger.info(
                    f"  {size}: {metrics['processing_time']:.2f}秒, {metrics['chars_per_second']:.2f} 字符/秒")

        if 'concurrent' in self.performance_metrics:
            metrics = self.performance_metrics['concurrent']
            logger.info(f"\n并发处理性能:")
            logger.info(f"  吞吐量: {metrics['throughput']:.2f} 字符/秒")
            logger.info(f"  文件处理速度: {metrics['files_per_second']:.2f} 文件/秒")

        if 'memory' in self.performance_metrics:
            metrics = self.performance_metrics['memory']
            logger.info(f"\n内存使用:")
            logger.info(f"  峰值内存: {metrics['peak_memory_mb']:.2f} MB")
            logger.info(f"  内存增长: {metrics['memory_increase_mb']:.2f} MB")

        if 'error_handling' in self.performance_metrics:
            metrics = self.performance_metrics['error_handling']
            logger.info(f"\n错误处理:")
            logger.info(f"  错误处理时间: {metrics['error_handling_time']:.2f}秒")

    async def cleanup(self):
        """清理测试环境"""
        test_dir = Path(__file__).parent / "performance_test_data"
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)

    async def run_performance_tests(self):
        """运行所有性能测试"""
        try:
            await self.setup()

            tests = [
                self.test_single_file_performance,
                self.test_concurrent_performance,
                self.test_memory_usage_monitoring,
                self.test_error_handling_performance
            ]

            for test_func in tests:
                try:
                    await test_func()
                    logger.info(f"✓ {test_func.__name__} 完成")
                except Exception as e:
                    logger.error(f"✗ {test_func.__name__} 失败: {e}")

            self.print_performance_summary()

        finally:
            await self.cleanup()


async def main():
    """主函数"""
    try:
        # 检查环境变量
        required_env_vars = ["OPENAI_API_KEY", "MODEL_NAME", "OPENAI_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
            return

        # 运行性能测试
        test = VectorizePerformanceTest()
        await test.run_performance_tests()

    except KeyboardInterrupt:
        logger.info("性能测试被用户中断")
    except Exception as e:
        logger.error(f"性能测试异常: {e}")


if __name__ == "__main__":
    asyncio.run(main())
