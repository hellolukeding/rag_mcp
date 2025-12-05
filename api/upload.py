import io
import os
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse

# PDF和DOCX处理库
try:
    import PyPDF2
    from docx import Document
except ImportError:
    PyPDF2 = None
    Document = None

from core.schemas import (ApiResponse, FileContentResponse, FileInfoResponse,
                          FileListResponse, FileUploadResponse)
from core.storage import minio_storage
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


async def extract_file_content(content: bytes, file_type: str) -> str:
    """
    根据文件类型提取文件内容

    Args:
        content: 文件内容字节
        file_type: 文件类型（扩展名）

    Returns:
        提取的文本内容
    """
    try:
        if file_type in [".md", ".markdown", ".txt"]:
            # 处理文本文件
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                return content.decode('gbk')

        elif file_type == ".pdf":
            # 处理PDF文件
            if PyPDF2 is None:
                return "PDF处理库未安装，无法读取PDF文件内容"

            text_content = ""
            try:
                with io.BytesIO(content) as f:
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

            with io.BytesIO(content) as f:
                doc = Document(f)
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
        logger.info(f"Received file upload request: {file.filename}")
        # 读取文件内容
        content = await file.read()
        logger.info(f"Read file content, size: {len(content)}")

        # 验证文件类型
        if not validate_file_type(file.filename, content):
            logger.warning(f"Invalid file type: {file.filename}")
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

        # 上传到MinIO
        logger.info(f"Uploading to MinIO: {new_filename}")
        await minio_storage.upload_file(new_filename, content, file.content_type)
        logger.info(f"Uploaded to MinIO: {new_filename}")

        # 获取文件大小
        file_size = len(content)

        # 记录到数据库
        # file_path 字段现在存储 MinIO 中的对象名称
        logger.info(f"Inserting into DB: {file_id}")
        await db_manager.insert_file(
            file_id=file_id,
            original_name=original_name,
            file_name=new_filename,
            file_path=new_filename,
            file_type=file_ext,
            file_size=file_size
        )
        logger.info(f"Inserted into DB: {file_id}")

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

        # 从MinIO获取文件内容
        file_name = file_info["file_name"]
        try:
            content = await minio_storage.get_file_content(file_name)
        except Exception as e:
            logger.error(f"从MinIO获取文件失败: {e}")
            return ApiResponse(
                code=404,
                msg="文件内容获取失败",
                data=None
            )

        # 根据文件类型提取内容
        text_content = await extract_file_content(content, file_info["file_type"])

        return ApiResponse(
            code=200,
            msg="获取文件内容成功",
            data=FileContentResponse(
                file_id=file_info["file_id"],
                original_name=file_info["original_name"],
                file_name=file_info["file_name"],
                file_type=file_info["file_type"],
                file_size=file_info["file_size"],
                content=text_content,
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


@router.get("/files/{file_id}/download", status_code=status.HTTP_200_OK,
            responses={
                200: {
                    "description": "文件下载流",
                    "content": {
                        "application/octet-stream": {
                            "schema": {
                                "type": "string",
                                "format": "binary"
                            }
                        }
                    }
                },
                404: {"description": "文件不存在"}
            })
async def download_file(file_id: str):
    """
    下载文件

    返回文件流，浏览器会自动触发下载
    """
    try:
        file_info = await db_manager.get_file_by_id(file_id)
        if not file_info:
            return ApiResponse(
                code=404,
                msg="文件不存在",
                data=None
            )

        file_name = file_info["file_name"]
        original_name = file_info["original_name"]

        # 获取文件流
        try:
            file_object = minio_storage.get_file_object(file_name)
        except Exception as e:
            logger.error(f"从MinIO获取文件流失败: {e}")
            return ApiResponse(
                code=404,
                msg="文件获取失败",
                data=None
            )

        # URL编码文件名
        encoded_filename = urllib.parse.quote(original_name)

        # 使用StreamingResponse返回文件流
        return StreamingResponse(
            file_object,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
        )

    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return ApiResponse(
            code=500,
            msg=f"下载文件失败: {str(e)}",
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

        # 删除MinIO中的文件
        file_name = file_info["file_name"]
        try:
            await minio_storage.delete_file(file_name)
            logger.info(f"已删除MinIO文件: {file_name}")
        except Exception as e:
            logger.warning(f"删除MinIO文件失败: {e}")
            # MinIO文件删除失败不影响数据库记录的删除

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
    直接从MinIO获取文件列表，并补充数据库中的元数据
    """
    try:
        # 1. 获取MinIO中的所有文件
        minio_objects = minio_storage.list_files()

        # 2. 获取数据库中的所有文件记录
        db_files = await db_manager.get_all_files()
        # 创建文件名到文件记录的映射
        db_files_map = {f["file_name"]: f for f in db_files}

        file_list = []
        for obj in minio_objects:
            file_name = obj.object_name

            # 尝试从数据库记录中获取信息
            if file_name in db_files_map:
                file_info = db_files_map[file_name]
                file_list.append(FileInfoResponse(
                    file_id=file_info["file_id"],
                    original_name=file_info["original_name"],
                    file_name=file_info["file_name"],
                    file_path=file_info["file_path"],
                    file_type=file_info["file_type"],
                    file_size=file_info["file_size"],
                    created_at=str(file_info["created_at"]),
                    vectorized_status=file_info.get("vectorized", "pending"),
                    vectorized_at=str(file_info["vectorized_at"]) if file_info.get(
                        "vectorized_at") else None
                ))
            else:
                # 如果数据库中没有记录（可能是直接上传到MinIO的文件）
                # 尝试从文件名解析信息
                file_ext = Path(file_name).suffix.lower()
                # 假设文件名就是 file_id + ext
                file_id = Path(file_name).stem

                file_list.append(FileInfoResponse(
                    file_id=file_id,
                    original_name=file_name,  # 无法获取原始文件名，使用对象名
                    file_name=file_name,
                    file_path=file_name,
                    file_type=file_ext,
                    file_size=obj.size,
                    created_at=str(obj.last_modified),
                    vectorized_status="unknown",  # 状态未知
                    vectorized_at=None
                ))

        return ApiResponse(
            code=200,
            msg="获取文件列表成功",
            data=FileListResponse(
                files=file_list,
                total=len(file_list)
            )
        )

    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return ApiResponse(
            code=500,
            msg=f"获取文件列表失败: {str(e)}",
            data=None
        )
