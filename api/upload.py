import os
import uuid
from pathlib import Path
from typing import Any, Dict

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

# PDF和DOCX处理库
try:
    import PyPDF2
    from docx import Document
except ImportError:
    PyPDF2 = None
    Document = None

from core.schemas import (ApiResponse, FileContentResponse, FileInfoResponse,
                          FileListResponse, FileUploadResponse)
from database.models import db_manager
from utils.logger import logger

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


async def extract_file_content(file_path: Path, file_type: str) -> str:
    """
    根据文件类型提取文件内容

    Args:
        file_path: 文件路径
        file_type: 文件类型（扩展名）

    Returns:
        提取的文本内容
    """
    try:
        if file_type in [".md", ".markdown", ".txt"]:
            # 处理文本文件
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    return await f.read()
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                async with aiofiles.open(file_path, 'r', encoding='gbk') as f:
                    return await f.read()

        elif file_type == ".pdf":
            # 处理PDF文件
            if PyPDF2 is None:
                return "PDF处理库未安装，无法读取PDF文件内容"

            text_content = ""
            try:
                with open(file_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)

                    # 检查PDF是否加密
                    if pdf_reader.is_encrypted:
                        return "PDF文件已加密，无法读取内容"

                    for page_num in range(len(pdf_reader.pages)):
                        page = pdf_reader.pages[page_num]
                        page_text = page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"

                # 如果提取的内容为空或者包含太多特殊字符，可能是扫描版PDF
                if not text_content.strip() or len([c for c in text_content if c.isprintable()]) < len(text_content) * 0.8:
                    return "PDF文件可能是扫描版或格式不兼容，无法提取文本内容"

                return text_content.strip()

            except Exception as pdf_error:
                logger.error(f"PDF处理错误: {pdf_error}")
                return f"PDF文件读取失败: {str(pdf_error)}"

        elif file_type == ".docx":
            # 处理DOCX文件
            if Document is None:
                return "DOCX处理库未安装，无法读取DOCX文件内容"

            doc = Document(file_path)
            text_content = ""
            for paragraph in doc.paragraphs:
                text_content += paragraph.text + "\n"
            return text_content.strip()

        else:
            return f"不支持的文件类型: {file_type}"

    except Exception as e:
        logger.error(f"提取文件内容失败: {e}")
        return f"提取文件内容失败: {str(e)}"


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
async def get_file_content(file_id: str) -> ApiResponse[FileContentResponse]:
    """
    根据文件ID获取文件内容
    """
    try:
        file_info = await db_manager.get_file_by_id(file_id)
        if not file_info:
            return ApiResponse(
                code=404,
                msg="文件不存在",
                data=None
            )

        # 读取文件内容
        file_path = Path(file_info["file_path"])
        if not file_path.exists():
            return ApiResponse(
                code=404,
                msg="物理文件不存在",
                data=None
            )

        # 根据文件类型提取内容
        content = await extract_file_content(file_path, file_info["file_type"])

        return ApiResponse(
            code=200,
            msg="获取文件内容成功",
            data=FileContentResponse(
                file_id=file_info["file_id"],
                original_name=file_info["original_name"],
                file_name=file_info["file_name"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                content=content,
                created_at=str(file_info["created_at"]),
                vectorized_status=file_info["vectorized"],
                vectorized_at=str(
                    file_info["vectorized_at"]) if file_info["vectorized_at"] else None
            )
        )

    except Exception as e:
        return ApiResponse(
            code=500,
            msg=f"获取文件内容失败: {str(e)}",
            data=None
        )


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(file_id: str) -> ApiResponse[None]:
    """
    根据文件ID删除文件及其向量数据
    """
    try:
        file_info = await db_manager.get_file_by_id(file_id)
        if not file_info:
            return ApiResponse(
                code=404,
                msg="文件不存在",
                data=None
            )

        # 删除文件记录和相关的文档、向量数据
        success = await db_manager.delete_file_and_documents(file_id)
        if not success:
            return ApiResponse(
                code=500,
                msg="删除文件记录失败",
                data=None
            )

        # 删除实际文件
        file_path = Path(file_info["file_path"])
        if file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"已删除物理文件: {file_path}")
            except Exception as e:
                logger.warning(f"删除物理文件失败: {e}")
                # 物理文件删除失败不影响数据库记录的删除

        logger.info(
            f"成功删除文件及其向量数据: {file_info['original_name']} (ID: {file_id})")

        return ApiResponse(
            code=200,
            msg="文件及向量数据删除成功",
            data=None
        )

    except Exception as e:
        logger.error(f"删除文件失败: {e}")
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
                created_at=file["created_at"],
                vectorized_status=file.get("vectorized", "pending"),
                vectorized_at=file.get("vectorized_at")
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
