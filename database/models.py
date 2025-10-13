import json
from datetime import datetime
from typing import List, Optional, Tuple

import aiosqlite


class DatabaseManager:
    def __init__(self, db_path: str = "rag_mcp.db"):
        self.db_path = db_path

    async def init_database(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 更新documents表结构以支持文件信息
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    file_type TEXT,
                    file_size INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 新增document_chunks表用于存储文档块和向量
            await db.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents (id) ON DELETE CASCADE
                )
            """)

            # 添加索引以提高查询性能
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id 
                ON document_chunks(document_id)
            """)

            # 新增的files表用于记录上传文件
            await db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id TEXT UNIQUE NOT NULL,
                    original_name TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

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
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO documents (filename, file_path, content, file_type, file_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                filename,
                file_path,
                content,
                file_type,
                file_size,
                json.dumps(metadata) if metadata else None
            ))
            await db.commit()
            return cursor.lastrowid

    async def insert_document_chunk(
        self,
        document_id: int,
        chunk_index: int,
        content: str,
        embedding: List[float]
    ) -> int:
        """插入文档块"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO document_chunks (document_id, chunk_index, content, embedding)
                VALUES (?, ?, ?, ?)
            """, (
                document_id,
                chunk_index,
                content,
                json.dumps(embedding)
            ))
            await db.commit()
            return cursor.lastrowid

    async def get_document(self, doc_id: int) -> Optional[dict]:
        """获取单个文档"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "id": row["id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "content": row["content"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                }
            return None

    async def get_document_chunks(self, document_id: int) -> List[dict]:
        """获取文档的所有块"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM document_chunks 
                WHERE document_id = ? 
                ORDER BY chunk_index
            """, (document_id,))
            rows = await cursor.fetchall()

            chunks = []
            for row in rows:
                chunks.append({
                    "id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "embedding": json.loads(row["embedding"]),
                    "created_at": row["created_at"]
                })
            return chunks

    async def get_all_documents(self) -> List[dict]:
        """获取所有文档"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM documents ORDER BY created_at DESC")
            rows = await cursor.fetchall()

            documents = []
            for row in rows:
                documents.append({
                    "id": row["id"],
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "content": row["content"],
                    "file_type": row["file_type"],
                    "file_size": row["file_size"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })

            return documents

    async def get_all_embeddings(self) -> List[Tuple[int, int, List[float]]]:
        """获取所有文档块的嵌入向量"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT document_id, id, embedding 
                FROM document_chunks 
                ORDER BY document_id, chunk_index
            """)
            rows = await cursor.fetchall()

            embeddings = []
            for row in rows:
                document_id, chunk_id, embedding_json = row
                embedding = json.loads(embedding_json)
                embeddings.append((document_id, chunk_id, embedding))

            return embeddings

    async def get_all_chunk_embeddings(self) -> List[dict]:
        """获取所有文档块的完整信息和嵌入向量"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT dc.*, d.filename, d.file_path
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                ORDER BY dc.document_id, dc.chunk_index
            """)
            rows = await cursor.fetchall()

            chunks = []
            for row in rows:
                chunks.append({
                    "chunk_id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                    "content": row["content"],
                    "embedding": json.loads(row["embedding"]),
                    "filename": row["filename"],
                    "file_path": row["file_path"],
                    "created_at": row["created_at"]
                })
            return chunks

    async def delete_document(self, doc_id: int) -> bool:
        """删除文档"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            await db.commit()
            return cursor.rowcount > 0

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

        if title is not None:
            updates.append("title = ?")
            values.append(title)

        if content is not None:
            updates.append("content = ?")
            values.append(content)

        if embedding is not None:
            updates.append("embedding = ?")
            values.append(json.dumps(embedding))

        if metadata is not None:
            updates.append("metadata = ?")
            values.append(json.dumps(metadata))

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(doc_id)

        query = f"UPDATE documents SET {', '.join(updates)} WHERE id = ?"

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, values)
            await db.commit()
            return cursor.rowcount > 0

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
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO files (file_id, original_name, file_name, file_path, file_type, file_size)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (file_id, original_name, file_name, file_path, file_type, file_size))
            await db.commit()
            return cursor.lastrowid

    async def get_file_by_id(self, file_id: str) -> Optional[dict]:
        """根据文件ID获取文件信息"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM files WHERE file_id = ?
            """, (file_id,))
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "file_id": row[1],
                    "original_name": row[2],
                    "file_name": row[3],
                    "file_path": row[4],
                    "file_type": row[5],
                    "file_size": row[6],
                    "created_at": row[7]
                }
            return None

    async def get_all_files(self) -> List[dict]:
        """获取所有文件信息"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT * FROM files ORDER BY created_at DESC
            """)
            rows = await cursor.fetchall()
            files = []
            for row in rows:
                files.append({
                    "id": row[0],
                    "file_id": row[1],
                    "original_name": row[2],
                    "file_name": row[3],
                    "file_path": row[4],
                    "file_type": row[5],
                    "file_size": row[6],
                    "created_at": row[7]
                })
            return files

    async def delete_file(self, file_id: str) -> bool:
        """删除文件记录"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM files WHERE file_id = ?
            """, (file_id,))
            await db.commit()
            return cursor.rowcount > 0


# 全局数据库管理器实例
db_manager = DatabaseManager()
