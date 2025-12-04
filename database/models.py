import json
import os
from datetime import datetime
from typing import Any, List, Optional, Tuple
from urllib.parse import quote_plus

import asyncpg
from pgvector.asyncpg import register_vector

# Try to import config, fallback to defaults if not found
try:
    from mcp_server.core.config import config
except ImportError:
    # Fallback config for standalone testing or if import fails
    class MockConfig:
        class DatabaseConfig:
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = int(os.getenv("POSTGRES_PORT", "5432"))
            user = os.getenv("POSTGRES_USER", "psql")
            password = os.getenv("POSTGRES_PASSWORD", "luoji@123")
            database = os.getenv("POSTGRES_DB", "ai_chat")

            @property
            def dsn(self) -> str:
                password = quote_plus(self.password)
                return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.database}"

        db = DatabaseConfig()

    config = MockConfig()


class DatabaseManager:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def get_pool(self) -> asyncpg.Pool:
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                dsn=config.db.dsn,
                min_size=1,
                max_size=10
            )
        return self.pool

    async def init_database(self):
        """初始化数据库表"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            # Enable vector extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Register vector type for this connection
            await register_vector(conn)

            # Create documents table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create document_chunks table with vector support
            # Using 1536 dimensions for OpenAI text-embedding-ada-002
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for document_id
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
                ON document_chunks(document_id)
            """)

            # Create HNSW index for vector search
            try:
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
                    ON document_chunks USING hnsw (embedding vector_cosine_ops)
                """)
            except Exception as e:
                print(f"Warning: Could not create vector index: {e}")

            # Create files table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id SERIAL PRIMARY KEY,
                    file_id TEXT UNIQUE NOT NULL,
                    original_name TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    vectorized TEXT DEFAULT 'pending',
                    vectorized_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    async def insert_document(
        self,
        filename: str,
        file_path: str,
        content: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None,
        metadata: Optional[dict] = None
    ) -> int:
        """插入文档"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO documents (filename, file_path, content, file_type, file_size, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """, filename, file_path, content, file_type, file_size, json.dumps(metadata) if metadata else None)
            return row['id']

    async def insert_document_chunk(
        self,
        document_id: int,
        chunk_index: int,
        content: str,
        embedding: List[float]
    ) -> int:
        """插入文档块"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await register_vector(conn)
            row = await conn.fetchrow("""
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, document_id, chunk_index, content, embedding)
            return row['id']

    async def get_document(self, doc_id: int) -> Optional[dict]:
        """获取单个文档"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1", doc_id
            )

            if row:
                return {
                    "id": row["id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "content": row["content"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def get_document_chunks(self, document_id: int) -> List[dict]:
        """获取文档的所有块"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch("""
                SELECT * FROM document_chunks 
                WHERE document_id = $1 
                ORDER BY chunk_index
            """, document_id)

            chunks = []
            for row in rows:
                chunks.append({
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "embedding": row["embedding"].tolist() if hasattr(row["embedding"], "tolist") else row["embedding"],
                    "created_at": row["created_at"]
                })
            return chunks

    async def get_all_documents(self) -> List[dict]:
        """获取所有文档"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM documents ORDER BY created_at DESC")

            documents = []
            for row in rows:
                documents.append({
                    "id": row["id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "content": row["content"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else row["metadata"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })

            return documents

    async def get_all_embeddings(self) -> List[Tuple[int, int, List[float]]]:
        """获取所有文档块的嵌入向量"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch("""
                SELECT document_id, id, embedding 
                FROM document_chunks 
                ORDER BY document_id, chunk_index
            """)

            embeddings = []
            for row in rows:
                document_id = row["document_id"]
                chunk_id = row["id"]
                embedding = row["embedding"].tolist() if hasattr(
                    row["embedding"], "tolist") else row["embedding"]
                embeddings.append((document_id, chunk_id, embedding))

            return embeddings

    async def get_all_chunk_embeddings(self) -> List[dict]:
        """获取所有文档块的完整信息和嵌入向量"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            await register_vector(conn)
            rows = await conn.fetch("""
                SELECT dc.*, d.filename, d.file_path
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY dc.document_id, dc.chunk_index
            """)

            chunks = []
            for row in rows:
                chunks.append({
                    "chunk_id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "embedding": row["embedding"].tolist() if hasattr(row["embedding"], "tolist") else row["embedding"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "created_at": row["created_at"]
                })
            return chunks

    async def delete_document(self, doc_id: int) -> bool:
        """删除文档"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("DELETE FROM documents WHERE id = $1", doc_id)
            # result is like "DELETE 1"
            return int(result.split()[1]) > 0

    async def update_document(
        self,
        doc_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """更新文档"""
        updates = []
        values = []
        param_idx = 1

        if title is not None:
            updates.append(f"title = ${param_idx}")
            values.append(title)
            param_idx += 1

        if content is not None:
            updates.append(f"content = ${param_idx}")
            values.append(content)
            param_idx += 1

        if embedding is not None:
            updates.append(f"embedding = ${param_idx}")
            values.append(embedding)
            param_idx += 1

        if metadata is not None:
            updates.append(f"metadata = ${param_idx}")
            values.append(json.dumps(metadata))
            param_idx += 1

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(doc_id)

        query = f"UPDATE documents SET {', '.join(updates)} WHERE id = ${param_idx}"

        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if embedding is not None:
                await register_vector(conn)
            result = await conn.execute(query, *values)
            return int(result.split()[1]) > 0

    async def insert_file(
        self,
        file_id: str,
        original_name: str,
        file_name: str,
        file_path: str,
        file_type: str,
        file_size: int
    ) -> int:
        """插入文件记录"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO files (file_id, original_name, file_name, file_path, file_type, file_size, vectorized)
                VALUES ($1, $2, $3, $4, $5, $6, 'pending')
                RETURNING id
            """, file_id, original_name, file_name, file_path, file_type, file_size)
            return row['id']

    async def get_file_by_id(self, file_id: str) -> Optional[dict]:
        """根据文件ID获取文件信息"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM files WHERE file_id = $1
            """, file_id)
            if row:
                return {
                    "id": row["id"],
                    "file_id": row["file_id"],
                    "original_name": row["original_name"],
                    "file_name": row["file_name"],
                    "file_path": row["file_path"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "vectorized": row["vectorized"] if "vectorized" in row else "pending",
                    "vectorized_at": row["vectorized_at"] if "vectorized_at" in row else None,
                    "created_at": row["created_at"]
                }
            return None

    async def get_all_files(self) -> List[dict]:
        """获取所有文件信息"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM files ORDER BY created_at DESC
            """)
            files = []
            for row in rows:
                files.append({
                    "id": row["id"],
                    "file_id": row["file_id"],
                    "original_name": row["original_name"],
                    "file_name": row["file_name"],
                    "file_path": row["file_path"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "vectorized": row["vectorized"] if "vectorized" in row else "pending",
                    "vectorized_at": row["vectorized_at"] if "vectorized_at" in row else None,
                    "created_at": row["created_at"]
                })
            return files

    async def update_file_vectorized_status(self, file_id: str, status: str) -> bool:
        """
        更新文件向量化状态
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            if status == 'completed':
                result = await conn.execute("""
                    UPDATE files SET vectorized = $1, vectorized_at = CURRENT_TIMESTAMP
                    WHERE file_id = $2
                """, status, file_id)
            else:
                result = await conn.execute("""
                    UPDATE files SET vectorized = $1, vectorized_at = NULL
                    WHERE file_id = $2
                """, status, file_id)
            return int(result.split()[1]) > 0

    async def get_unvectorized_files(self) -> List[dict]:
        """获取未向量化的文件（包括pending和failed状态）"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM files WHERE vectorized IN ('pending', 'failed') OR vectorized IS NULL
                ORDER BY created_at ASC
            """)
            files = []
            for row in rows:
                files.append({
                    "id": row["id"],
                    "file_id": row["file_id"],
                    "original_name": row["original_name"],
                    "file_name": row["file_name"],
                    "file_path": row["file_path"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "vectorized": bool(row["vectorized"]) if "vectorized" in row else False,
                    "vectorized_at": row["vectorized_at"] if "vectorized_at" in row else None,
                    "created_at": row["created_at"]
                })
            return files

    async def delete_documents_by_file_path(self, file_path: str) -> int:
        """根据文件路径删除相关的文档记录（包括文档块）"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM documents WHERE file_path = $1
            """, file_path)
            return int(result.split()[1])

    async def delete_file_and_documents(self, file_id: str) -> bool:
        """删除文件记录及相关的文档数据"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                # 先获取文件信息
                file_row = await conn.fetchrow("""
                    SELECT file_path FROM files WHERE file_id = $1
                """, file_id)

                if not file_row:
                    return False

                file_path = file_row['file_path']

                # 删除相关的文档记录 (CASCADE will handle chunks)
                await conn.execute("""
                    DELETE FROM documents WHERE file_path = $1
                """, file_path)

                # 删除文件记录
                result = await conn.execute("""
                    DELETE FROM files WHERE file_id = $1
                """, file_id)

                return int(result.split()[1]) > 0

    async def delete_file(self, file_id: str) -> bool:
        """删除文件记录"""
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM files WHERE file_id = $1
            """, file_id)
            return int(result.split()[1]) > 0


# 全局数据库管理器实例
db_manager = DatabaseManager()
