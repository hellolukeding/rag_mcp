# RAG MCP 服务器使用指南

## 概述

这是一个基于 MCP (Model Context Protocol) 的 RAG (Retrieval Augmented Generation) 服务器，专门用于文档检索功能。该服务器不包含对话生成功能，仅提供高效的文档内容检索服务，可以被其他 AI 模型使用。

## 功能特性

- ✅ **语义搜索**: 基于向量相似度的文档检索
- ✅ **文档管理**: 列出和获取文档详情
- ✅ **统计信息**: 提供搜索和文档统计数据
- ✅ **MCP 协议**: 标准 MCP 接口，易于集成
- ✅ **高性能**: 使用 SQLite 数据库和余弦相似度算法

## 安装与配置

### 1. 环境要求

- Python 3.8+
- Poetry (推荐) 或 pip
- SQLite 数据库

### 2. 安装依赖

```bash
# 使用Poetry (推荐)
poetry install

# 或使用pip
pip install -r requirements.txt
```

### 3. 环境变量配置

创建 `.env` 文件或设置环境变量:

```bash
# OpenAI API配置 (用于向量化)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_URL=https://api.openai.com/v1
EMBEDDING_MODEL_NAME=text-embedding-ada-002

# 数据库配置
DATABASE_PATH=rag_mcp.db

# 搜索配置
DEFAULT_SIMILARITY_THRESHOLD=0.7
DEFAULT_SEARCH_LIMIT=5
MAX_SEARCH_RESULTS=50
```

## 使用方法

### 1. 启动服务器

```bash
# 使用启动脚本 (推荐)
PYTHONPATH=. poetry run python mcp/scripts/start_server.py

# 或直接运行服务器
PYTHONPATH=. poetry run python mcp/server/simple_mcp_server.py
```

### 2. 测试服务器

```bash
# 运行完整测试
PYTHONPATH=. poetry run python mcp/scripts/test_mcp_server.py

# 运行演示
PYTHONPATH=. poetry run python mcp/scripts/demo.py
```

## MCP 工具说明

该服务器提供以下 4 个 MCP 工具:

### 1. `rag_search` - 语义搜索

根据查询文本搜索相关文档块。

**参数:**

- `query` (必需): 搜索查询字符串
- `limit` (可选): 返回结果数量，默认 5
- `threshold` (可选): 相似度阈值，默认 0.7
- `document_ids` (可选): 限制搜索的文档 ID 列表

**返回:**

```json
{
  "results": [
    {
      "chunk_id": 8,
      "document_id": 12,
      "document_name": "AI心理咨询系统需求文档.md",
      "content": "文档内容...",
      "similarity_score": 0.85,
      "chunk_index": 0
    }
  ],
  "total_results": 1,
  "query_time_ms": 150,
  "success": true
}
```

### 2. `list_documents` - 文档列表

获取所有可搜索的文档列表。

**参数:** 无

**返回:**

```json
{
  "documents": [
    {
      "id": 12,
      "filename": "AI心理咨询系统需求文档.md",
      "file_type": ".md",
      "file_size": 25600,
      "chunk_count": 9,
      "created_at": "2025-01-15 10:30:00"
    }
  ],
  "total_documents": 3,
  "success": true
}
```

### 3. `get_document` - 文档详情

获取指定文档的详细信息和所有文档块。

**参数:**

- `document_id` (必需): 文档 ID

**返回:**

```json
{
  "document": {
    "id": 12,
    "filename": "AI心理咨询系统需求文档.md",
    "file_type": ".md",
    "content": "完整文档内容...",
    "metadata": {},
    "created_at": "2025-01-15 10:30:00",
    "file_size": 25600,
    "chunks": [
      {
        "id": 8,
        "chunk_index": 0,
        "content": "文档块内容..."
      }
    ]
  },
  "success": true
}
```

### 4. `search_statistics` - 搜索统计

获取搜索和文档统计信息。

**参数:** 无

**返回:**

```json
{
  "total_documents": 3,
  "total_chunks": 13,
  "file_types": { ".md": 1, ".pdf": 1, ".docx": 1 },
  "average_chunks_per_document": 4.33,
  "similarity_threshold": 0.7,
  "default_search_limit": 5,
  "success": true
}
```

## 集成示例

### Python 客户端示例

```python
import asyncio
import json
from mcp.simple_mcp_server import MCPServer

async def search_documents(query: str):
    server = MCPServer()

    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "rag_search",
            "arguments": {
                "query": query,
                "limit": 5,
                "threshold": 0.7
            }
        }
    }

    response = await server.handle_request(request)
    content = json.loads(response['result']['content'][0]['text'])

    return content['results']

# 使用示例
results = asyncio.run(search_documents("心理咨询"))
for result in results:
    print(f"相似度: {result['similarity_score']:.2f}")
    print(f"内容: {result['content'][:100]}...")
```

### MCP 客户端集成

如果你的应用支持 MCP 协议，可以直接连接到服务器:

```bash
# 启动服务器 (stdio模式)
python mcp/simple_mcp_server.py
```

## 文件结构

```
mcp/
├── __init__.py                    # 包初始化
├── README.md                      # 使用指南
├── core/                          # 核心业务逻辑
│   ├── __init__.py
│   ├── config.py                  # 配置管理
│   ├── rag_handler.py             # RAG处理逻辑
│   └── schemas.py                 # 数据模型
├── server/                        # 服务器实现
│   ├── __init__.py
│   ├── mcp_server.py              # 标准MCP服务器
│   └── simple_mcp_server.py       # 简化MCP服务器
├── scripts/                       # 工具脚本
│   ├── __init__.py
│   ├── start_server.py            # 启动脚本
│   ├── demo.py                    # 演示脚本
│   └── test_mcp_server.py         # 测试脚本
└── docs/                          # 文档文件
    ├── PRD.md                     # 产品需求文档
    ├── RAG_MCP_PRD.md             # 详细需求文档
    └── SUMMARY.md                 # 项目总结
```

## 性能指标

- 单次搜索响应时间: < 500ms
- 支持并发请求: >= 10
- 内存使用: < 1GB
- 支持文档数量: >= 1000

## 错误处理

服务器会返回标准的错误响应:

```json
{
  "error": "Query cannot be empty",
  "tool": "rag_search",
  "arguments": { "query": "" },
  "success": false
}
```

## 开发和扩展

### 添加新的工具

1. 在 `rag_handler.py` 中添加新的处理方法
2. 在 `simple_mcp_server.py` 中注册新工具
3. 更新工具列表和处理逻辑

### 自定义搜索算法

可以修改 `core/services.py` 中的 `VectorSearchService` 类来实现自定义的相似度计算。

## 故障排除

### 常见问题

1. **ModuleNotFoundError**: 确保使用 `poetry run` 或激活虚拟环境
2. **API Key 错误**: 检查 `OPENAI_API_KEY` 环境变量
3. **数据库错误**: 确保 `rag_mcp.db` 文件存在且有内容
4. **搜索结果为空**: 降低 `threshold` 参数或检查查询文本

### 调试模式

设置环境变量启用详细日志:

```bash
export DEBUG=true
python mcp/simple_mcp_server.py
```

## 更新日志

- **v1.0.0** (2025-01-15): 初始版本
  - 实现基本 RAG 搜索功能
  - 支持 MCP 协议
  - 提供 4 个核心工具
  - 完整的测试覆盖

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request!

---

**注意**: 该服务器专注于文档检索功能，不包含对话生成能力。如需完整的 RAG 对话功能，请参考项目中的其他组件。
