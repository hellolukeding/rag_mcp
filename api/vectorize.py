import asyncio
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

import PyPDF2
from docx import Document
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from openai import OpenAI

from core.schemas import DocumentChunk, DocumentCreate
from core.services import DocumentService

# 加载环境变量
load_dotenv()

router = APIRouter()

# 初始化OpenAI客户端
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_URL")
)

document_service = DocumentService()


class DocumentProcessor:
    """文档处理器"""

    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """从DOCX文件提取文本"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法解析DOCX文件: {str(e)}"
            )

    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """从PDF文件提取文本"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法解析PDF文件: {str(e)}"
            )

    @staticmethod
    def extract_text_from_txt(file_path: str) -> str:
        """从TXT文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except UnicodeDecodeError:
            # 尝试其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as file:
                    return file.read().strip()
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"无法读取TXT文件: {str(e)}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无法读取TXT文件: {str(e)}"
            )

    def extract_text(self, file_path: str) -> str:
        """根据文件类型提取文本"""
        file_extension = Path(file_path).suffix.lower()

        if file_extension == '.docx':
            return self.extract_text_from_docx(file_path)
        elif file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.txt', '.md']:
            return self.extract_text_from_txt(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {file_extension}"
            )

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """将文本分割成块"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # 尝试在句号、换行符或空格处分割
            if end < len(text):
                for delimiter in ['\n\n', '\n', '。', '. ', ' ']:
                    split_pos = text.rfind(delimiter, start, end)
                    if split_pos > start:
                        end = split_pos + len(delimiter)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap if end < len(text) else end

        return chunks


class EmbeddingService:
    """嵌入向量服务"""

    def __init__(self):
        self.model_name = os.getenv("MODEL_NAME", "Qwen/Qwen3-Embedding-8B")

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的嵌入向量"""
        try:
            # 使用线程池执行同步的OpenAI API调用
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(
                    executor,
                    lambda: client.embeddings.create(
                        input=texts,
                        model=self.model_name
                    )
                )

            embeddings = [data.embedding for data in response.data]
            return embeddings

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"获取嵌入向量失败: {str(e)}"
            )


# 初始化服务
processor = DocumentProcessor()
embedding_service = EmbeddingService()


@router.post("/vectorize", status_code=status.HTTP_200_OK)
async def vectorize_file(file_path: str):
    """
    向量化文件并存储到数据库

    Args:
        file_path: 上传文件的路径，例如 "upload/b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx"

    Returns:
        处理结果信息
    """
    try:
        # 检查文件是否存在
        full_path = Path(file_path)
        if not full_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"文件不存在: {file_path}"
            )

        # 提取文件名和扩展名
        filename = full_path.name
        file_extension = full_path.suffix.lower()

        # 提取文本内容
        text_content = processor.extract_text(str(full_path))

        if not text_content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件内容为空或无法提取文本"
            )

        # 分割文本
        text_chunks = processor.chunk_text(text_content)

        # 获取嵌入向量
        embeddings = await embedding_service.get_embeddings(text_chunks)

        # 创建文档记录
        document_data = DocumentCreate(
            filename=filename,
            file_path=file_path,
            content=text_content,
            file_type=file_extension,
            file_size=full_path.stat().st_size
        )

        # 保存文档到数据库
        document = document_service.create_document(document_data)

        # 保存文档块和向量
        chunks_created = 0
        for i, (chunk_text, embedding) in enumerate(zip(text_chunks, embeddings)):
            chunk_data = DocumentChunk(
                document_id=document.id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding
            )
            document_service.create_document_chunk(chunk_data)
            chunks_created += 1

        return {
            "success": True,
            "message": "文件向量化成功",
            "data": {
                "document_id": document.id,
                "filename": filename,
                "file_path": file_path,
                "total_chunks": chunks_created,
                "text_length": len(text_content),
                "file_type": file_extension
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"向量化处理失败: {str(e)}"
        )
