# RAG MCP 服务器产品需求文档 (PRD)

## 1. 产品概述

### 1.1 产品定义

RAG MCP 服务器是一个基于 Model Context Protocol (MCP) 的检索增强生成服务，专门用于为其他 AI 模型提供文档检索能力。该服务器不包含对话功能，仅提供高效的文档内容检索服务。

### 1.2 目标用户

- 需要文档检索能力的 AI 应用开发者
- 使用 MCP 协议的 AI 模型
- 需要 RAG 功能的聊天机器人系统

### 1.3 核心价值

- 提供高效的语义检索功能
- 支持多种文档格式
- 无缝集成 MCP 协议
- 支持 SSE 实时响应

## 2. 功能需求

### 2.1 核心功能

#### 2.1.1 文档检索 (rag_search)

- **输入参数：**

  - `query`: 搜索查询字符串
  - `limit`: 返回结果数量限制 (默认: 5)
  - `threshold`: 相似度阈值 (默认: 0.7)
  - `document_ids`: 可选的文档 ID 列表，用于限制搜索范围

- **输出格式：**

```json
{
  "results": [
    {
      "chunk_id": "integer",
      "document_id": "integer",
      "document_name": "string",
      "content": "string",
      "similarity_score": "float",
      "chunk_index": "integer"
    }
  ],
  "total_results": "integer",
  "query_time_ms": "integer"
}
```

#### 2.1.2 文档列表 (list_documents)

- **功能：** 获取所有可搜索的文档列表
- **输出格式：**

```json
{
  "documents": [
    {
      "id": "integer",
      "filename": "string",
      "file_type": "string",
      "file_size": "integer",
      "chunk_count": "integer",
      "created_at": "string"
    }
  ]
}
```

#### 2.1.3 文档详情 (get_document)

- **输入参数：**

  - `document_id`: 文档 ID

- **输出格式：**

```json
{
  "document": {
    "id": "integer",
    "filename": "string",
    "file_type": "string",
    "content": "string",
    "metadata": "object",
    "chunks": [
      {
        "id": "integer",
        "chunk_index": "integer",
        "content": "string"
      }
    ]
  }
}
```

### 2.2 工具功能

#### 2.2.1 MCP Tools 定义

1. **rag_search** - 语义搜索工具
2. **list_documents** - 文档列表工具
3. **get_document** - 文档详情工具

### 2.3 SSE 支持

- 支持 Server-Sent Events 实时推送搜索结果
- 适用于大规模文档检索的流式响应
- 提供搜索进度反馈

## 3. 技术规格

### 3.1 技术栈

- **语言：** Python 3.8+
- **协议：** MCP (Model Context Protocol)
- **数据库：** SQLite (现有 rag_mcp.db)
- **向量计算：** 余弦相似度
- **嵌入模型：** OpenAI text-embedding-ada-002 (可配置)

### 3.2 性能要求

- 单次搜索响应时间 < 500ms
- 支持并发请求数 >= 10
- 内存使用 < 1GB
- 支持文档数量 >= 1000

### 3.3 配置参数

```python
MCP_RAG_CONFIG = {
    "server_name": "rag-mcp-server",
    "server_version": "1.0.0",
    "default_search_limit": 5,
    "default_similarity_threshold": 0.7,
    "max_search_results": 50,
    "enable_sse": True,
    "database_path": "rag_mcp.db"
}
```

## 4. 接口设计

### 4.1 MCP Tool Schemas

```json
{
  "rag_search": {
    "name": "rag_search",
    "description": "Search for relevant document chunks using semantic similarity",
    "inputSchema": {
      "type": "object",
      "properties": {
        "query": { "type": "string", "description": "Search query" },
        "limit": {
          "type": "integer",
          "default": 5,
          "minimum": 1,
          "maximum": 50
        },
        "threshold": {
          "type": "number",
          "default": 0.7,
          "minimum": 0.0,
          "maximum": 1.0
        },
        "document_ids": { "type": "array", "items": { "type": "integer" } }
      },
      "required": ["query"]
    }
  }
}
```

### 4.2 错误处理

- 数据库连接异常
- 嵌入服务不可用
- 查询参数验证失败
- 搜索结果为空

## 5. 实现计划

### 5.1 文件结构

```
mcp/
├── __init__.py
├── config.py          # 配置文件
├── mcp_server.py       # 主服务器文件
├── rag_handler.py      # RAG处理逻辑
├── schemas.py          # 数据模型
└── RAG_MCP_PRD.md     # 本文档
```

### 5.2 开发阶段

1. **Phase 1**: 基础 MCP 服务器框架
2. **Phase 2**: RAG 搜索功能实现
3. **Phase 3**: SSE 支持和性能优化
4. **Phase 4**: 错误处理和测试

## 6. 验收标准

### 6.1 功能测试

- [ ] rag_search 工具正常返回搜索结果
- [ ] list_documents 工具正常返回文档列表
- [ ] get_document 工具正常返回文档详情
- [ ] 支持 MCP 协议标准交互

### 6.2 性能测试

- [ ] 搜索响应时间 < 500ms
- [ ] 支持并发 10 个请求
- [ ] 内存使用稳定

### 6.3 兼容性测试

- [ ] 与现有数据库结构兼容
- [ ] 支持 MCP 客户端连接
- [ ] 错误处理完善

---

**版本：** v1.0  
**更新日期：** 2025-01-15  
**负责人：** RAG Team
