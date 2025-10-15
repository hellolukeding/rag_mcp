"""
Data schemas for MCP RAG Server
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SearchRequest:
    """Document search request"""
    query: str
    limit: int = 5
    threshold: float = 0.7


@dataclass
class RAGRequest:
    """RAG query request"""
    query: str
    context_limit: int = 3
    temperature: float = 0.7
    max_tokens: int = 1000
    stream: bool = False


@dataclass
class DocumentInfo:
    """Document information"""
    id: int
    filename: str
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime
    chunk_count: Optional[int] = None


@dataclass
class DocumentChunkInfo:
    """Document chunk information"""
    id: int
    document_id: int
    chunk_index: int
    content: str
    similarity_score: Optional[float] = None


@dataclass
class SearchResult:
    """Search result"""
    chunks: List[DocumentChunkInfo]
    total_found: int
    query: str
    processing_time: float


@dataclass
class SSEEvent:
    """Server-Sent Event"""
    event: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None

    def to_string(self) -> str:
        """Convert to SSE format string"""
        lines = []
        if self.id:
            lines.append(f"id: {self.id}")
        if self.retry:
            lines.append(f"retry: {self.retry}")
        lines.append(f"event: {self.event}")

        # Handle data serialization
        import json
        data_str = json.dumps(self.data, ensure_ascii=False, default=str)
        lines.append(f"data: {data_str}")
        lines.append("")  # Empty line to end the event

        return "\n".join(lines)


@dataclass
class RAGResponse:
    """RAG response"""
    answer: str
    sources: List[DocumentChunkInfo]
    query: str
    processing_time: float
    total_tokens: Optional[int] = None


@dataclass
class StreamChunk:
    """Stream response chunk"""
    content: str
    index: int
    finished: bool = False
    metadata: Optional[Dict[str, Any]] = None
