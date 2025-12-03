import os
from io import BytesIO
from typing import BinaryIO, Optional

from minio import Minio
from minio.error import S3Error

from utils.logger import logger


class MinioStorage:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        self.access_key = os.getenv("MINIO_ROOT_USER", "admin")
        self.secret_key = os.getenv("MINIO_ROOT_PASSWORD", "admin123456")
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME", "rag-mcp-files")
        self.secure = os.getenv("MINIO_SECURE", "False").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )

        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"Error checking/creating bucket: {e}")
            raise

    async def upload_file(self, file_name: str, file_data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Upload a file to MinIO.

        Args:
            file_name: The name of the file in the bucket.
            file_data: The file content as bytes.
            content_type: The content type of the file.

        Returns:
            The object name (file_name).
        """
        try:
            data_stream = BytesIO(file_data)
            self.client.put_object(
                self.bucket_name,
                file_name,
                data_stream,
                length=len(file_data),
                content_type=content_type
            )
            logger.info(f"Uploaded file to MinIO: {file_name}")
            return file_name
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise

    async def get_file_content(self, file_name: str) -> bytes:
        """
        Get file content from MinIO.

        Args:
            file_name: The name of the file in the bucket.

        Returns:
            The file content as bytes.
        """
        try:
            response = self.client.get_object(self.bucket_name, file_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            logger.error(f"Error getting file from MinIO: {e}")
            raise

    async def delete_file(self, file_name: str):
        """
        Delete a file from MinIO.

        Args:
            file_name: The name of the file in the bucket.
        """
        try:
            self.client.remove_object(self.bucket_name, file_name)
            logger.info(f"Deleted file from MinIO: {file_name}")
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            raise

    def get_presigned_url(self, file_name: str, expires_hours: int = 1) -> str:
        """
        Get a presigned URL for a file.

        Args:
            file_name: The name of the file.
            expires_hours: Expiration time in hours.

        Returns:
            Presigned URL string.
        """
        try:
            from datetime import timedelta
            return self.client.get_presigned_url(
                "GET",
                self.bucket_name,
                file_name,
                expires=timedelta(hours=expires_hours)
            )
        except S3Error as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


# Global instance
minio_storage = MinioStorage()
