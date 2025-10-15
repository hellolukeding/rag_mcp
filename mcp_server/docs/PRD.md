# RAG MCP Server with SSE Support - Product Requirements Document (PRD)

## 1. 项目概述

### 1.1 产品名称

RAG MCP Server with Server-Sent Events (SSE) Support

### 1.2 产品定位

基于 Model Context Protocol (MCP)标准的 RAG (Retrieval-Augmented Generation)服务器，支持实时流式响应和向量检索功能。

### 1.3 目标用户

- AI 应用开发者
- 需要集成 RAG 功能的系统开发团队
- 希望使用 MCP 标准进行 AI 服务集成的开发者

## 2. 核心功能需求

### 2.1 MCP Server 基础功能

#### 2.1.1 MCP 协议支持

- **工具声明**: 支持 MCP 工具注册和发现
- **资源管理**: 管理文档资源的访问和检索
- **提示模板**: 提供 RAG 查询的标准提示模板
- **能力声明**: 声明服务器的 RAG 和 SSE 能力

#### 2.1.2 基础工具集

| 工具名称            | 功能描述         | 输入参数                                 | 输出格式     |
| ------------------- | ---------------- | ---------------------------------------- | ------------ |
| `search_documents`  | 语义检索相关文档 | query: str, limit: int, threshold: float | 文档块列表   |
| `get_document_info` | 获取文档详细信息 | document_id: int                         | 文档元信息   |
| `list_documents`    | 列出所有可用文档 | page: int, size: int                     | 文档列表     |
| `rag_query`         | RAG 增强查询     | query: str, stream: bool                 | 生成的回答   |
| `rag_query_stream`  | 流式 RAG 查询    | query: str                               | SSE 流式响应 |

### 2.2 RAG 核心功能

#### 2.2.1 向量检索

- **语义搜索**: 基于 embedding 的相似度搜索
- **多种检索策略**:
  - 纯向量检索
  - 混合检索（向量+关键词）
  - 重排序机制
- **检索参数可配置**:
  - 相似度阈值 (threshold): 0.1-1.0
  - 返回结果数量 (limit): 1-50
  - 检索上下文窗口大小

#### 2.2.2 生成增强

- **上下文拼接**: 智能合并检索到的文档片段
- **提示工程**:
  - 预设的 RAG 提示模板
  - 支持自定义提示模板
  - 上下文长度管理
- **LLM 集成**: 支持多种 LLM API
  - OpenAI API
  - 自定义 API 端点
  - 流式和非流式响应

### 2.3 SSE 流式响应

#### 2.3.1 实时流式输出

- **分块传输**: 按 token 或句子分块传输
- **状态通知**: 实时传输处理状态
  - `searching`: 正在检索文档
  - `generating`: 正在生成回答
  - `completed`: 生成完成
  - `error`: 处理错误
- **元数据传输**: 同时传输相关元信息
  - 检索到的文档信息
  - 相似度分数
  - 处理耗时

#### 2.3.2 SSE 事件格式

```
event: status
data: {"status": "searching", "message": "正在检索相关文档..."}

event: documents
data: {"documents": [...], "total": 3}

event: content
data: {"chunk": "这是生成的部分内容", "index": 0}

event: completed
data: {"total_time": 2.5, "tokens": 150}
```

## 3. 技术架构

### 3.1 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │◄──►│   MCP Server    │◄──►│  Vector Store   │
│                 │    │                 │    │                 │
│ - AI Assistant  │    │ - Tool Registry │    │ - Document      │
│ - Chat App      │    │ - SSE Handler   │    │   Chunks        │
│ - IDE Plugin    │    │ - RAG Engine    │    │ - Embeddings    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   LLM Service   │
                       │                 │
                       │ - OpenAI API    │
                       │ - Custom API    │
                       │ - Stream Mode   │
                       └─────────────────┘
```

### 3.2 技术栈

- **MCP 框架**: `mcp` Python 库
- **异步处理**: `asyncio`, `aiohttp`
- **向量检索**: 现有的 embedding 和向量搜索服务
- **流式处理**: `asyncio.Queue` + SSE
- **数据库**: 现有的 SQLite + document_chunks 表
- **LLM 集成**: `httpx`异步 HTTP 客户端

### 3.3 文件结构

```
mcp/
├── __init__.py
├── server.py              # MCP服务器主入口
├── tools.py               # MCP工具定义
├── rag_engine.py          # RAG核心引擎
├── sse_handler.py         # SSE流式处理
├── config.py              # 配置管理
├── schemas.py             # 数据结构定义
└── utils.py               # 工具函数
```

## 4. 详细功能设计

### 4.1 MCP 工具设计

#### 4.1.1 search_documents

```python
{
    "name": "search_documents",
    "description": "根据查询语句检索相关文档片段",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索查询"},
            "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            "threshold": {"type": "number", "default": 0.7, "minimum": 0.1, "maximum": 1.0}
        },
        "required": ["query"]
    }
}
```

#### 4.1.2 rag_query_stream

```python
{
    "name": "rag_query_stream",
    "description": "执行流式RAG查询，返回实时生成的回答",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "用户查询"},
            "context_limit": {"type": "integer", "default": 3},
            "temperature": {"type": "number", "default": 0.7},
            "max_tokens": {"type": "integer", "default": 1000}
        },
        "required": ["query"]
    }
}
```

### 4.2 RAG 处理流程

#### 4.2.1 检索阶段

1. **查询预处理**: 查询语句清洗和标准化
2. **向量化**: 将查询转换为 embedding 向量
3. **相似度计算**: 与文档库中的 chunks 进行相似度计算
4. **结果排序**: 按相似度分数排序并过滤
5. **上下文合并**: 智能合并相邻的文档片段

#### 4.2.2 生成阶段

1. **提示构建**: 将检索结果和用户查询组合成提示
2. **LLM 调用**: 调用语言模型生成回答
3. **流式处理**: 实时返回生成的内容块
4. **后处理**: 内容格式化和质量检查

### 4.3 SSE 实现机制

#### 4.3.1 事件流设计

```python
async def stream_rag_response(query: str):
    # 发送开始事件
    yield SSEEvent("status", {"status": "starting"})

    # 检索阶段
    yield SSEEvent("status", {"status": "searching"})
    documents = await search_documents(query)
    yield SSEEvent("documents", {"documents": documents})

    # 生成阶段
    yield SSEEvent("status", {"status": "generating"})
    async for chunk in llm_stream_generate(context):
        yield SSEEvent("content", {"chunk": chunk})

    # 完成事件
    yield SSEEvent("completed", {"status": "completed"})
```

#### 4.3.2 错误处理

- **连接管理**: 客户端断开检测和资源清理
- **超时处理**: 设置合理的超时时间
- **错误恢复**: 部分失败时的降级策略

## 5. 配置和环境

### 5.1 环境变量配置

```env
# LLM配置
OPENAI_API_KEY=sk-xxx
OPENAI_URL=https://api.openai.com/v1
MODEL_NAME=gpt-3.5-turbo

# MCP服务器配置
MCP_SERVER_NAME=rag-mcp-server
MCP_SERVER_VERSION=1.0.0
MCP_PORT=3000

# RAG配置
DEFAULT_SIMILARITY_THRESHOLD=0.7
DEFAULT_CONTEXT_LIMIT=5
MAX_CONTEXT_LENGTH=4000
```

### 5.2 启动配置

```json
{
  "mcpServers": {
    "rag-server": {
      "command": "python",
      "args": ["-m", "mcp.server"],
      "cwd": "/path/to/rag_mcp"
    }
  }
}
```

## 6. API 接口规范

### 6.1 MCP 标准接口

- `initialize`: 初始化服务器
- `list_tools`: 列出可用工具
- `call_tool`: 调用指定工具
- `list_resources`: 列出可用资源
- `read_resource`: 读取资源内容
- `list_prompts`: 列出提示模板

### 6.2 扩展 SSE 接口

- `GET /sse/rag`: SSE 流式 RAG 查询入点
- `POST /sse/query`: 发起流式查询请求

## 7. 性能指标

### 7.1 响应时间目标

- 文档检索: < 200ms
- 首个内容块: < 1s
- 完整响应: < 10s (取决于内容长度)

### 7.2 并发能力

- 支持同时处理: 20 个并发 RAG 查询
- SSE 连接数: 100 个并发连接
- 内存使用: < 1GB (正常负载)

## 8. 测试策略

### 8.1 单元测试

- MCP 工具注册和调用
- 向量检索准确性
- SSE 事件流完整性
- 错误处理机制

### 8.2 集成测试

- 完整 RAG 流程测试
- 多客户端并发测试
- 长时间连接稳定性测试

### 8.3 性能测试

- 大量文档检索性能
- 流式响应延迟测试
- 内存泄漏检测

## 9. 部署和运维

### 9.1 部署方式

- **开发模式**: 直接 Python 运行
- **生产模式**: Docker 容器化部署
- **集群模式**: 多实例负载均衡

### 9.2 监控指标

- 请求成功率
- 平均响应时间
- 并发连接数
- 向量检索命中率
- LLM 调用成功率

### 9.3 日志记录

- 请求跟踪日志
- 错误详细日志
- 性能监控日志
- SSE 连接状态日志

## 10. 后续扩展计划

### 10.1 功能增强

- 支持多模态检索（图片+文本）
- 增加缓存机制提升性能
- 支持用户个性化配置
- 增加更多 LLM 提供商支持

### 10.2 协议扩展

- 支持 MCP 协议新版本特性
- 增加自定义工具热插拔
- 支持插件化架构

---

**文档版本**: 1.0  
**创建时间**: 2025-10-15  
**作者**: Assistant  
**审核状态**: 待审核
