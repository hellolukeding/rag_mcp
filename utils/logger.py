
import os
import sys
from pathlib import Path

from loguru import logger as loguru_logger


class Logger:
    def __init__(self):
        # 获取项目根目录
        self.project_root = Path(__file__).parent.parent
        self.logs_dir = self.project_root / "logs"

        # 确保logs目录存在
        self.logs_dir.mkdir(exist_ok=True)

        # 移除默认的logger配置
        loguru_logger.remove()

        # 配置控制台输出
        loguru_logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )

        # 配置文件输出 - 普通日志
        loguru_logger.add(
            self.logs_dir / "app.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG",
            rotation="10 MB",  # 日志文件大小达到10MB时轮转
            retention="30 days",  # 保留30天的日志
            compression="zip",  # 压缩旧日志文件
            encoding="utf-8"
        )

        # 配置文件输出 - 错误日志
        loguru_logger.add(
            self.logs_dir / "error.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="ERROR",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8"
        )

        # 配置文件输出 - 每日日志
        loguru_logger.add(
            self.logs_dir / "daily_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="INFO",
            rotation="00:00",  # 每天午夜轮转
            retention="7 days",  # 保留7天的每日日志
            encoding="utf-8"
        )

    def get_logger(self, name: str = None):
        """获取logger实例"""
        if name:
            return loguru_logger.bind(name=name)
        return loguru_logger

    def debug(self, message: str, **kwargs):
        """调试级别日志"""
        loguru_logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """信息级别日志"""
        loguru_logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """警告级别日志"""
        loguru_logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """错误级别日志"""
        loguru_logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """严重错误级别日志"""
        loguru_logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """异常日志（包含堆栈信息）"""
        loguru_logger.exception(message, **kwargs)


# 创建全局logger实例
logger_instance = Logger()
logger = logger_instance.get_logger()
