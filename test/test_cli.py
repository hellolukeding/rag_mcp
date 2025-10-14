#!/usr/bin/env python3
"""
向量化服务命令行测试工具
提供简单的命令行界面来测试向量化功能
"""

import argparse
import asyncio
import os
import sys
import time
import uuid
from pathlib import Path

from core.vectorize import TaskFile, TaskStatus, get_vectorize_instance
from database.models import db_manager
from utils.logger import logger

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))


class VectorizeCliTool:
    """向量化命令行工具"""

    def __init__(self):
        self.vectorize_service = None

    async def init_service(self):
        """初始化服务"""
        await db_manager.init_database()
        self.vectorize_service = get_vectorize_instance()
        logger.info("向量化服务初始化完成")

    async def add_file_task(self, file_path: str):
        """添加文件向量化任务"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {file_path}")
                return None

            # 创建TaskFile对象
            task_file = TaskFile(
                file_id=str(uuid.uuid4()),
                original_name=file_path.name,
                file_name=file_path.name,
                file_path=str(file_path),
                file_type=file_path.suffix,
                file_size=file_path.stat().st_size
            )

            # 添加任务
            task_id = self.vectorize_service.add_task(task_file)
            logger.info(f"已添加向量化任务:")
            logger.info(f"  任务ID: {task_id}")
            logger.info(f"  文件名: {task_file.original_name}")
            logger.info(f"  文件大小: {task_file.file_size} 字节")

            return task_id

        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return None

    async def monitor_task(self, task_id: str):
        """监控任务进度"""
        logger.info(f"开始监控任务: {task_id}")

        while True:
            task_status = self.vectorize_service.get_task_status(task_id)

            if not task_status:
                logger.error("任务不存在")
                break

            status = TaskStatus(task_status['status'])
            progress = task_status['progress']

            print(f"\\r任务状态: {status.value} | 进度: {progress:.1f}% | "
                  f"文本块: {task_status['chunks_processed']}/{task_status['chunks_total']}", end="")

            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                print()  # 换行
                if status == TaskStatus.COMPLETED:
                    logger.info("任务完成成功!")
                else:
                    logger.error(
                        f"任务失败: {task_status.get('error_message', 'Unknown error')}")
                break

            await asyncio.sleep(1)

    async def list_tasks(self):
        """列出所有任务"""
        tasks = self.vectorize_service.get_all_tasks()

        if not tasks:
            logger.info("当前没有任务")
            return

        logger.info(f"当前任务列表 (共 {len(tasks)} 个):")
        logger.info("-" * 80)

        for task in tasks:
            status_emoji = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'failed': '❌'
            }.get(task['status'], '❓')

            logger.info(
                f"{status_emoji} {task['task_id'][:8]}... - {task['original_name']}")
            logger.info(
                f"   状态: {task['status']} | 进度: {task['progress']:.1f}%")

            if task['error_message']:
                logger.info(f"   错误: {task['error_message']}")

    async def check_file_status(self, file_id: str = None):
        """检查文件向量化状态"""
        if file_id:
            status = await self.vectorize_service.get_file_vectorized_status(file_id)
            if status:
                logger.info(f"文件 {status['original_name']}:")
                logger.info(f"  ID: {file_id}")
                logger.info(
                    f"  向量化状态: {'已完成' if status['vectorized'] else '未完成'}")
                logger.info(f"  向量化时间: {status['vectorized_at'] or 'N/A'}")
            else:
                logger.error(f"文件 {file_id} 不存在")
        else:
            # 列出所有未向量化的文件
            unvectorized = await self.vectorize_service.get_unvectorized_files()
            if unvectorized:
                logger.info(f"未向量化的文件 (共 {len(unvectorized)} 个):")
                for file_info in unvectorized:
                    logger.info(
                        f"  📄 {file_info['original_name']} (ID: {file_info['file_id'][:8]}...)")
            else:
                logger.info("所有文件都已向量化")

    async def process_file_and_wait(self, file_path: str):
        """处理文件并等待完成"""
        task_id = await self.add_file_task(file_path)
        if task_id:
            await self.monitor_task(task_id)

    async def batch_process_directory(self, directory: str, file_pattern: str = "*"):
        """批量处理目录中的文件"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                logger.error(f"目录不存在: {directory}")
                return

            # 查找匹配的文件
            files = list(dir_path.glob(file_pattern))
            if not files:
                logger.info(f"在目录 {directory} 中没有找到匹配 '{file_pattern}' 的文件")
                return

            logger.info(f"找到 {len(files)} 个文件待处理")

            # 添加所有任务
            task_ids = []
            for file_path in files:
                if file_path.is_file():
                    task_id = await self.add_file_task(str(file_path))
                    if task_id:
                        task_ids.append(task_id)

            if not task_ids:
                logger.error("没有成功添加任何任务")
                return

            logger.info(f"已添加 {len(task_ids)} 个任务，开始处理...")

            # 监控所有任务
            while task_ids:
                completed_tasks = []

                for task_id in task_ids:
                    task_status = self.vectorize_service.get_task_status(
                        task_id)
                    if task_status:
                        status = TaskStatus(task_status['status'])
                        if status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                            completed_tasks.append(task_id)
                            if status == TaskStatus.COMPLETED:
                                logger.info(f"✅ 任务完成: {task_id[:8]}...")
                            else:
                                logger.error(f"❌ 任务失败: {task_id[:8]}...")

                for task_id in completed_tasks:
                    task_ids.remove(task_id)

                if task_ids:
                    logger.info(f"等待 {len(task_ids)} 个任务完成...")
                    await asyncio.sleep(3)

            logger.info("批量处理完成!")

        except Exception as e:
            logger.error(f"批量处理失败: {e}")


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="向量化服务命令行测试工具")
    parser.add_argument("command", choices=[
        "add", "monitor", "list", "status", "process", "batch"
    ], help="命令类型")

    parser.add_argument("--file", "-f", help="文件路径")
    parser.add_argument("--task-id", "-t", help="任务ID")
    parser.add_argument("--file-id", help="文件ID")
    parser.add_argument("--directory", "-d", help="目录路径")
    parser.add_argument("--pattern", "-p", default="*.txt",
                        help="文件匹配模式 (默认: *.txt)")

    args = parser.parse_args()

    # 检查环境变量
    required_env_vars = ["OPENAI_API_KEY", "MODEL_NAME", "OPENAI_URL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"缺少必要的环境变量: {', '.join(missing_vars)}")
        return 1

    try:
        tool = VectorizeCliTool()
        await tool.init_service()

        if args.command == "add":
            if not args.file:
                logger.error("请使用 --file 指定文件路径")
                return 1
            await tool.add_file_task(args.file)

        elif args.command == "monitor":
            if not args.task_id:
                logger.error("请使用 --task-id 指定任务ID")
                return 1
            await tool.monitor_task(args.task_id)

        elif args.command == "list":
            await tool.list_tasks()

        elif args.command == "status":
            await tool.check_file_status(args.file_id)

        elif args.command == "process":
            if not args.file:
                logger.error("请使用 --file 指定文件路径")
                return 1
            await tool.process_file_and_wait(args.file)

        elif args.command == "batch":
            if not args.directory:
                logger.error("请使用 --directory 指定目录路径")
                return 1
            await tool.batch_process_directory(args.directory, args.pattern)

    except KeyboardInterrupt:
        logger.info("操作被用户中断")
    except Exception as e:
        logger.error(f"执行失败: {e}")
        return 1

    return 0


def print_usage_examples():
    """打印使用示例"""
    examples = """
使用示例:

1. 添加单个文件任务:
   python test_cli.py add --file /path/to/document.txt

2. 处理文件并等待完成:
   python test_cli.py process --file /path/to/document.txt

3. 监控指定任务:
   python test_cli.py monitor --task-id abc12345

4. 列出所有任务:
   python test_cli.py list

5. 检查文件向量化状态:
   python test_cli.py status
   python test_cli.py status --file-id abc12345

6. 批量处理目录:
   python test_cli.py batch --directory /path/to/docs
   python test_cli.py batch --directory /path/to/docs --pattern "*.docx"
    """
    print(examples)


if __name__ == "__main__":
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        print_usage_examples()

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
