import os
import uuid
from pathlib import Path
from typing import Any, Dict

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from core.schemas import (ApiResponse, FileInfoResponse, FileListResponse,
                          FileUploadResponse)
from database.models import db_manager

router = APIRouter()

# 支持的文件类型
ALLOWED_EXTENSIONS = {".docx", ".pdf", ".md", ".markdown"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
    "application/pdf",  # pdf
    "text/markdown",  # markdown
    "text/plain"  # markdown files often detected as text/plain
}

# 上传目录
UPLOAD_DIR = Path("upload")
UPLOAD_DIR.mkdir(exist_ok=True)


def validate_file_type(filename: str, content: bytes) -> bool:
    """验证文件类型"""
    # 检查文件扩展名
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False

    # 简单的文件内容检查
    if file_ext == ".pdf":
        # PDF文件以%PDF开头
        return content.startswith(b'%PDF')
    elif file_ext == ".docx":
        # DOCX文件是ZIP格式，以PK开头
        return content.startswith(b'PK')
    elif file_ext in [".md", ".markdown"]:
        # Markdown文件是文本文件，检查是否可以解码为UTF-8
        try:
            content.decode('utf-8')
            return True
        except UnicodeDecodeError:
            return False

    return True


@router.post("/files", status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile = File(...)) -> ApiResponse[FileUploadResponse]:
    """
    上传文件接口
    支持的文件格式: .docx, .pdf, .md, .markdown
    """
    try:
        # 读取文件内容
        content = await file.read()

        # 验证文件类型
        if not validate_file_type(file.filename, content):
            return ApiResponse(
                code=400,
                msg="不支持的文件格式。仅支持 docx, pdf, markdown 文件",
                data=None
            )

        # 生成唯一文件ID
        file_id = str(uuid.uuid4())

        # 解析文件名和扩展名
        original_name = file.filename
        file_ext = Path(original_name).suffix.lower()

        # 生成新的文件名（防止重名冲突）
        new_filename = f"{file_id}{file_ext}"
        file_path = UPLOAD_DIR / new_filename

        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # 获取文件大小
        file_size = len(content)

        # 记录到数据库
        await db_manager.insert_file(
            file_id=file_id,
            original_name=original_name,
            file_name=new_filename,
            file_path=str(file_path),
            file_type=file_ext,
            file_size=file_size
        )

        return ApiResponse(
            code=200,
            msg="文件上传成功",
            data=FileUploadResponse(
                file_id=file_id,
                original_name=original_name,
                file_size=file_size,
                file_type=file_ext
            )
        )

    except Exception as e:
        return ApiResponse(
            code=500,
            msg=f"文件上传失败: {str(e)}",
            data=None
        )


@router.get("/files/{file_id}", status_code=status.HTTP_200_OK)
async def get_file_info(file_id: str) -> ApiResponse[FileInfoResponse]:
    """
    根据文件ID获取文件信息
    """
    try:
        file_info = await db_manager.get_file_by_id(file_id)
        if not file_info:
            return ApiResponse(
                code=404,
                msg="文件不存在",
                data=None
            )

        return ApiResponse(
            code=200,
            msg="获取文件信息成功",
            data=FileInfoResponse(
                file_id=file_info["file_id"],
                original_name=file_info["original_name"],
                file_name=file_info["file_name"],
                file_path=file_info["file_path"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                created_at=file_info["created_at"]
            )
        )

    except Exception as e:
        return ApiResponse(
            code=500,
            msg=f"获取文件信息失败: {str(e)}",
            data=None
        )


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(file_id: str) -> ApiResponse[None]:
    """
    根据文件ID删除文件
    """
    try:
        file_info = await db_manager.get_file_by_id(file_id)
        if not file_info:
            return ApiResponse(
                code=404,
                msg="文件不存在",
                data=None
            )

        # 删除文件记录
        success = await db_manager.delete_file(file_id)
        if not success:
            return ApiResponse(
                code=500,
                msg="删除文件记录失败",
                data=None
            )

        # 删除实际文件
        file_path = Path(file_info["file_path"])
        if file_path.exists():
            os.remove(file_path)

        return ApiResponse(
            code=200,
            msg="文件删除成功",
            data=None
        )

    except Exception as e:
        return ApiResponse(
            code=500,
            msg=f"删除文件失败: {str(e)}",
            data=None
        )


@router.get("/files", status_code=status.HTTP_200_OK)
async def list_files() -> ApiResponse[FileListResponse]:
    """
    列出所有上传的文件
    """
    try:
        files = await db_manager.get_all_files()
        file_list = [
            FileInfoResponse(
                file_id=file["file_id"],
                original_name=file["original_name"],
                file_name=file["file_name"],
                file_path=file["file_path"],
                file_type=file["file_type"],
                file_size=file["file_size"],
                created_at=file["created_at"]
            ) for file in files
        ]

        return ApiResponse(
            code=200,
            msg="获取文件列表成功",
            data=FileListResponse(
                files=file_list,
                total=len(file_list)
            )
        )

    except Exception as e:
        return ApiResponse(
            code=500,
            msg=f"获取文件列表失败: {str(e)}",
            data=None
        )
