# Core module for MCP Server
# Contains configuration and RAG handling logic

from .config import EmbeddingConfig, RAGConfig, ServerConfig
from .rag_handler import RAGHandler
from .schemas import (DocumentChunkInfo, DocumentInfo, SearchRequest,
                      SearchResult)

__all__ = [
    'RAGConfig',
    'EmbeddingConfig',
    'ServerConfig',
    'RAGHandler',
    'SearchRequest',
    'SearchResult',
    'DocumentInfo',
    'DocumentChunkInfo'
]

from .config import config
from .rag_handler import rag_handler

__all__ = ['config', 'rag_handler']
