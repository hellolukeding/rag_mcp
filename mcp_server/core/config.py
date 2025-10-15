"""
Configuration management for MCP RAG Server
"""

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass
class EmbeddingConfig:
    """Embedding service configuration"""
    api_key: str
    base_url: str = "https://api.openai.com/v1"
    model_name: str = "text-embedding-ada-002"
    timeout: float = 30.0


@dataclass
class RAGConfig:
    """RAG configuration"""
    default_similarity_threshold: float = 0.7
    default_search_limit: int = 5
    max_search_results: int = 50
    database_path: str = "rag_mcp.db"


@dataclass
class ServerConfig:
    """Server configuration"""
    name: str = "rag-mcp-server"
    version: str = "1.0.0"
    port: int = 3000
    host: str = "localhost"
    debug: bool = False


class Config:
    """Main configuration class"""

    def __init__(self):

        self.embedding = EmbeddingConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_URL", "https://api.openai.com/v1"),
            model_name=os.getenv("MODEL_NAME",
                                 "text-embedding-ada-002"),
            timeout=float(os.getenv("EMBEDDING_TIMEOUT", "30.0"))
        )

        self.rag = RAGConfig(
            default_similarity_threshold=float(
                os.getenv("DEFAULT_SIMILARITY_THRESHOLD", "0.7")),
            default_search_limit=int(os.getenv("DEFAULT_SEARCH_LIMIT", "5")),
            max_search_results=int(os.getenv("MAX_SEARCH_RESULTS", "50")),
            database_path=os.getenv("DATABASE_PATH", "rag_mcp.db")
        )

        self.server = ServerConfig(
            name=os.getenv("MCP_SERVER_NAME", "rag-mcp-server"),
            version=os.getenv("MCP_SERVER_VERSION", "1.0.0"),
            port=int(os.getenv("MCP_PORT", "3000")),
            host=os.getenv("MCP_HOST", "localhost"),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )

    def validate(self) -> bool:
        """Validate configuration"""
        if not self.embedding.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        if self.rag.default_similarity_threshold < 0 or self.rag.default_similarity_threshold > 1:
            raise ValueError("Similarity threshold must be between 0 and 1")

        if self.rag.default_search_limit < 1 or self.rag.default_search_limit > self.rag.max_search_results:
            raise ValueError(
                f"Search limit must be between 1 and {self.rag.max_search_results}")

        return True


# Global config instance
config = Config()
