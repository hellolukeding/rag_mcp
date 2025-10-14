
import asyncio
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Empty, Queue
from typing import Callable, Dict, List, Optional

import openai
from dotenv import load_dotenv

from database.models import DatabaseManager
from utils.logger import logger

load_dotenv()

# 任务状态枚举


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskFile:
    file_id: str
    original_name: str
    file_name: str
    file_path: str
    file_type: str
    file_size: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class VectorizeTask:
    """向量化任务"""
    task_id: str
    task_file: TaskFile
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    chunks_total: int = 0
    chunks_processed: int = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'task_id': self.task_id,
            'file_id': self.task_file.file_id,
            'original_name': self.task_file.original_name,
            'status': self.status.value,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'chunks_total': self.chunks_total,
            'chunks_processed': self.chunks_processed
        }


class VectorizeQueue:
    """线程安全的向量化任务队列"""

    def __init__(self, max_workers: int = 2):
        self.task_queue = Queue()
        self.tasks = {}  # task_id -> VectorizeTask
        self.lock = threading.Lock()
        self.max_workers = max_workers
        self.workers = []
        self.running = False
        self.progress_callbacks = []  # 进度回调函数列表

        # 初始化数据库管理器和向量化客户端
        self.db_manager = DatabaseManager()
        self._init_vectorize_client()

        logger.info(f"向量化队列初始化完成，最大工作线程数: {max_workers}")

    def _init_vectorize_client(self):
        """初始化向量化客户端"""
        if (os.getenv("OPENAI_API_KEY") is None
           or os.getenv("MODEL_NAME") is None
           or os.getenv("OPENAI_URL") is None):
            raise ValueError("请设置环境变量 OPENAI_API_KEY、MODEL_NAME 和 OPENAI_URL")

        self.model_name = os.getenv("MODEL_NAME", "Qwen/Qwen3-Embedding-8B")
        self.base_url = os.getenv(
            "OPENAI_URL", "https://api.siliconflow.cn/v1")
        self.api_key = os.getenv("OPENAI_API_KEY")

        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        logger.info(f"向量化客户端初始化完成，模型: {self.model_name}")

    def add_progress_callback(self, callback: Callable[[VectorizeTask], None]):
        """添加进度回调函数"""
        with self.lock:
            self.progress_callbacks.append(callback)

    def _notify_progress(self, task: VectorizeTask):
        """通知进度更新"""
        for callback in self.progress_callbacks:
            try:
                callback(task)
            except Exception as e:
                logger.error(f"进度回调函数执行失败: {e}")

    def add_task(self, task_file: TaskFile) -> str:
        """添加向量化任务"""
        task_id = str(uuid.uuid4())
        task = VectorizeTask(
            task_id=task_id,
            task_file=task_file
        )

        with self.lock:
            self.tasks[task_id] = task
            self.task_queue.put(task)

        logger.info(f"添加向量化任务: {task_id}, 文件: {task_file.original_name}")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[VectorizeTask]:
        """获取任务状态"""
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, VectorizeTask]:
        """获取所有任务"""
        with self.lock:
            return self.tasks.copy()

    def start(self):
        """启动队列处理"""
        if self.running:
            logger.warning("向量化队列已经在运行中")
            return

        self.running = True
        logger.info("启动向量化队列处理")

        # 启动工作线程
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_thread,
                name=f"VectorizeWorker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            logger.info(f"启动工作线程: {worker.name}")

    def stop(self):
        """停止队列处理"""
        self.running = False
        logger.info("正在停止向量化队列...")

        # 等待所有工作线程结束
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5)

        self.workers.clear()
        logger.info("向量化队列已停止")

    def _worker_thread(self):
        """工作线程主循环"""
        thread_name = threading.current_thread().name
        logger.info(f"工作线程 {thread_name} 开始运行")

        while self.running:
            try:
                # 从队列中获取任务
                task = self.task_queue.get(timeout=1.0)
                logger.info(f"工作线程 {thread_name} 开始处理任务: {task.task_id}")

                # 处理任务
                self._process_task(task)

                # 标记任务完成
                self.task_queue.task_done()

            except Empty:
                # 队列为空，继续等待
                continue
            except Exception as e:
                logger.error(f"工作线程 {thread_name} 发生异常: {e}")

        logger.info(f"工作线程 {thread_name} 结束运行")

    def _process_task(self, task: VectorizeTask):
        """处理向量化任务"""
        try:
            # 更新任务状态
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.now()
            self._notify_progress(task)

            logger.info(
                f"开始处理向量化任务: {task.task_id}, 文件: {task.task_file.original_name}")

            # 0. 更新文件状态为处理中
            asyncio.run(self._update_file_vectorized_status(
                task.task_file.file_id, "processing"))

            # 1. 读取文件内容
            content = self._read_file_content(task.task_file)

            # 2. 分割文本为块
            chunks = self._split_text_to_chunks(content)
            task.chunks_total = len(chunks)
            self._notify_progress(task)

            logger.info(f"文件分割完成，共 {len(chunks)} 个文本块")

            # 3. 向量化处理
            asyncio.run(self._vectorize_chunks(task, chunks))

            # 4. 更新文件向量化状态为已完成
            asyncio.run(self._update_file_vectorized_status(
                task.task_file.file_id, "completed"))

            # 5. 更新任务完成状态
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.progress = 100.0
            self._notify_progress(task)

            logger.info(f"向量化任务完成: {task.task_id}")

        except Exception as e:
            # 处理失败，更新文件状态为失败
            try:
                asyncio.run(self._update_file_vectorized_status(
                    task.task_file.file_id, "failed"))
            except Exception as update_e:
                logger.error(f"更新文件向量化状态失败: {update_e}")

            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            self._notify_progress(task)

            logger.error(f"向量化任务失败: {task.task_id}, 错误: {e}")

    def _read_file_content(self, task_file: TaskFile) -> str:
        """读取文件内容"""
        try:
            with open(task_file.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(task_file.file_path, 'r', encoding='gbk') as f:
                return f.read()

    def _split_text_to_chunks(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """将文本分割为块"""
        chunks = []
        start = 0

        while start < len(content):
            end = min(start + chunk_size, len(content))
            chunk = content[start:end]
            chunks.append(chunk.strip())
            start = end - overlap if end < len(content) else end

        return [chunk for chunk in chunks if chunk]  # 过滤空块

    async def _vectorize_chunks(self, task: VectorizeTask, chunks: List[str]):
        """向量化文本块并存储到数据库"""
        # 初始化数据库
        await self.db_manager.init_database()

        # 检查文件记录是否已存在，如果不存在则插入
        existing_file = await self.db_manager.get_file_by_id(task.task_file.file_id)
        if not existing_file:
            file_id = await self.db_manager.insert_file(
                file_id=task.task_file.file_id,
                original_name=task.task_file.original_name,
                file_name=task.task_file.file_name,
                file_path=task.task_file.file_path,
                file_type=task.task_file.file_type,
                file_size=task.task_file.file_size
            )
            logger.info(f"插入新文件记录: {task.task_file.original_name}")
        else:
            logger.info(f"文件记录已存在: {task.task_file.original_name}")

        # 插入文档记录
        document_id = await self.db_manager.insert_document(
            filename=task.task_file.original_name,
            file_path=task.task_file.file_path,
            content='\n'.join(chunks),
            file_type=task.task_file.file_type,
            file_size=task.task_file.file_size
        )

        # 批量处理文本块
        batch_size = 5  # 每次处理5个文本块
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]

            # 获取向量
            embeddings = await self._get_embeddings_batch(batch_chunks)

            # 保存到数据库
            for j, (chunk, embedding) in enumerate(zip(batch_chunks, embeddings)):
                await self.db_manager.insert_document_chunk(
                    document_id=document_id,
                    chunk_index=i + j,
                    content=chunk,
                    embedding=embedding
                )

                task.chunks_processed += 1
                task.progress = (task.chunks_processed /
                                 task.chunks_total) * 100
                self._notify_progress(task)

                logger.debug(
                    f"处理文本块 {task.chunks_processed}/{task.chunks_total}")

    async def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量获取文本向量"""
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            raise

    async def _update_file_vectorized_status(self, file_id: str, status: str):
        """
        更新文件向量化状态

        Args:
            file_id: 文件ID
            status: 状态，支持: 'pending', 'processing', 'completed', 'failed'
        """
        try:
            await self.db_manager.init_database()
            success = await self.db_manager.update_file_vectorized_status(file_id, status)
            if success:
                status_map = {
                    'pending': '待处理',
                    'processing': '处理中',
                    'completed': '已完成',
                    'failed': '失败'
                }
                logger.info(
                    f"文件 {file_id} 向量化状态更新为: {status_map.get(status, status)}")
            else:
                logger.warning(f"文件 {file_id} 向量化状态更新失败: 文件未找到")
        except Exception as e:
            logger.error(f"更新文件向量化状态时发生错误: {e}")
            raise


class Vectorize:
    """向量化服务主类"""

    def __init__(self, max_workers: int = 2):
        self.queue = VectorizeQueue(max_workers)
        self.setup_progress_logging()

    def setup_progress_logging(self):
        """设置进度日志输出"""
        def log_progress(task: VectorizeTask):
            status_msg = {
                TaskStatus.PENDING: "等待处理",
                TaskStatus.PROCESSING: f"处理中 ({task.progress:.1f}%)",
                TaskStatus.COMPLETED: "已完成",
                TaskStatus.FAILED: f"失败: {task.error_message}"
            }

            msg = status_msg.get(task.status, "未知状态")

            if task.status == TaskStatus.PROCESSING:
                logger.info(
                    f"任务进度 [{task.task_file.original_name}]: {msg} "
                    f"({task.chunks_processed}/{task.chunks_total})"
                )
            else:
                logger.info(f"任务状态 [{task.task_file.original_name}]: {msg}")

        self.queue.add_progress_callback(log_progress)

    def start(self):
        """启动向量化服务"""
        self.queue.start()
        logger.info("向量化服务已启动")

    def stop(self):
        """停止向量化服务"""
        self.queue.stop()
        logger.info("向量化服务已停止")

    def add_task(self, task_file: TaskFile) -> str:
        """添加向量化任务"""
        return self.queue.add_task(task_file)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.queue.get_task_status(task_id)
        return task.to_dict() if task else None

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务状态"""
        tasks = self.queue.get_all_tasks()
        return [task.to_dict() for task in tasks.values()]

    async def get_unvectorized_files(self) -> List[Dict]:
        """获取未向量化的文件列表"""
        try:
            await self.queue.db_manager.init_database()
            return await self.queue.db_manager.get_unvectorized_files()
        except Exception as e:
            logger.error(f"获取未向量化文件列表失败: {e}")
            return []

    async def get_file_vectorized_status(self, file_id: str) -> Optional[Dict]:
        """获取文件向量化状态"""
        try:
            await self.queue.db_manager.init_database()
            file_info = await self.queue.db_manager.get_file_by_id(file_id)
            if file_info:
                return {
                    "file_id": file_info["file_id"],
                    "original_name": file_info["original_name"],
                    "vectorized": file_info["vectorized"],
                    "vectorized_at": file_info["vectorized_at"]
                }
            return None
        except Exception as e:
            logger.error(f"获取文件向量化状态失败: {e}")
            return None


# 全局向量化实例
_vectorize_instance = None


def get_vectorize_instance() -> Vectorize:
    """获取全局向量化实例"""
    global _vectorize_instance
    if _vectorize_instance is None:
        _vectorize_instance = Vectorize()
        _vectorize_instance.start()
    return _vectorize_instance
