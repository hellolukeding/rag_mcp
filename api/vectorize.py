"""
任务队列向量化API
用于管理异步向量化任务
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.vectorize import TaskFile, get_vectorize_instance
from database.models import db_manager
from utils.logger import logger

router = APIRouter()


class VectorizeTaskRequest(BaseModel):
    """向量化任务请求"""
    file_id: str
    file_path: str


class VectorizeTaskResponse(BaseModel):
    """向量化任务响应"""
    success: bool
    message: str
    task_id: Optional[str] = None
    data: Optional[Dict] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    success: bool
    message: str
    data: Optional[Dict] = None


@router.post("/task/vectorize", response_model=VectorizeTaskResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_vectorize_task(request: VectorizeTaskRequest):
    """
    创建向量化任务

    Args:
        request: 包含file_id和file_path的请求

    Returns:
        任务ID和状态信息
    """
    try:
        # 获取向量化服务实例
        vectorize_service = get_vectorize_instance()

        # 检查文件是否存在
        full_path = Path(request.file_path)
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在: {request.file_path}"
            )

        # 初始化数据库并获取文件信息
        await db_manager.init_database()
        file_info = await db_manager.get_file_by_id(request.file_id)

        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"数据库中未找到文件记录: {request.file_id}"
            )

        # 检查文件是否已经向量化
        if file_info.get("vectorized", False):
            return VectorizeTaskResponse(
                success=True,
                message="文件已经向量化完成",
                data={
                    "file_id": request.file_id,
                    "original_name": file_info["original_name"],
                    "vectorized_at": file_info["vectorized_at"],
                    "already_vectorized": True
                }
            )

        # 创建TaskFile对象
        task_file = TaskFile(
            file_id=file_info["file_id"],
            original_name=file_info["original_name"],
            file_name=file_info["file_name"],
            file_path=file_info["file_path"],
            file_type=file_info["file_type"],
            file_size=file_info["file_size"],
            created_at=file_info["created_at"]
        )

        # 添加到任务队列
        task_id = vectorize_service.add_task(task_file)

        logger.info(f"创建向量化任务成功: {task_id}, 文件: {file_info['original_name']}")

        return VectorizeTaskResponse(
            success=True,
            message="向量化任务已创建",
            task_id=task_id,
            data={
                "file_id": request.file_id,
                "original_name": file_info["original_name"],
                "file_size": file_info["file_size"],
                "file_type": file_info["file_type"],
                "task_id": task_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建向量化任务失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建向量化任务失败: {str(e)}"
        )


@router.get("/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    获取任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    try:
        vectorize_service = get_vectorize_instance()
        task_status = vectorize_service.get_task_status(task_id)

        if not task_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务未找到: {task_id}"
            )

        return TaskStatusResponse(
            success=True,
            message="获取任务状态成功",
            data=task_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )


@router.get("/tasks", response_model=TaskStatusResponse)
async def get_all_tasks():
    """
    获取所有任务状态

    Returns:
        所有任务的状态信息
    """
    try:
        vectorize_service = get_vectorize_instance()
        all_tasks = vectorize_service.get_all_tasks()

        return TaskStatusResponse(
            success=True,
            message=f"获取任务列表成功，共 {len(all_tasks)} 个任务",
            data={
                "tasks": all_tasks,
                "total_count": len(all_tasks)
            }
        )

    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {str(e)}"
        )


@router.get("/files/unvectorized", response_model=TaskStatusResponse)
async def get_unvectorized_files():
    """
    获取未向量化的文件列表

    Returns:
        未向量化的文件列表
    """
    try:
        vectorize_service = get_vectorize_instance()
        unvectorized_files = await vectorize_service.get_unvectorized_files()

        return TaskStatusResponse(
            success=True,
            message=f"获取未向量化文件列表成功，共 {len(unvectorized_files)} 个文件",
            data={
                "files": unvectorized_files,
                "total_count": len(unvectorized_files)
            }
        )

    except Exception as e:
        logger.error(f"获取未向量化文件列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取未向量化文件列表失败: {str(e)}"
        )


@router.get("/files/{file_id}/status", response_model=TaskStatusResponse)
async def get_file_vectorized_status(file_id: str):
    """
    获取文件向量化状态

    Args:
        file_id: 文件ID

    Returns:
        文件向量化状态信息
    """
    try:
        vectorize_service = get_vectorize_instance()
        file_status = await vectorize_service.get_file_vectorized_status(file_id)

        if not file_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件未找到: {file_id}"
            )

        return TaskStatusResponse(
            success=True,
            message="获取文件向量化状态成功",
            data=file_status
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件向量化状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取文件向量化状态失败: {str(e)}"
        )


@router.post("/files/batch_vectorize", response_model=TaskStatusResponse)
async def batch_vectorize_files():
    """
    批量向量化所有未向量化的文件

    Returns:
        批量任务创建结果
    """
    try:
        vectorize_service = get_vectorize_instance()

        # 获取未向量化的文件
        unvectorized_files = await vectorize_service.get_unvectorized_files()

        if not unvectorized_files:
            return TaskStatusResponse(
                success=True,
                message="没有需要向量化的文件",
                data={
                    "files_processed": 0,
                    "task_ids": []
                }
            )

        task_ids = []

        # 为每个文件创建向量化任务
        for file_info in unvectorized_files:
            task_file = TaskFile(
                file_id=file_info["file_id"],
                original_name=file_info["original_name"],
                file_name=file_info["file_name"],
                file_path=file_info["file_path"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                created_at=file_info["created_at"]
            )

            task_id = vectorize_service.add_task(task_file)
            task_ids.append(task_id)

            logger.info(f"为文件 {file_info['original_name']} 创建向量化任务: {task_id}")

        return TaskStatusResponse(
            success=True,
            message=f"批量向量化任务已创建，共 {len(task_ids)} 个任务",
            data={
                "files_processed": len(unvectorized_files),
                "task_ids": task_ids,
                "files": [{"file_id": f["file_id"], "original_name": f["original_name"]}
                          for f in unvectorized_files]
            }
        )

    except Exception as e:
        logger.error(f"批量向量化文件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量向量化文件失败: {str(e)}"
        )
