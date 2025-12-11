# RAG MCP 项目

English: [README_en.md](README_en.md)

## 概述

RAG MCP（Model Context Protocol）项目是一个综合系统，旨在通过模块化和可扩展的架构来管理和与大型语言模型（LLMs）交互。它提供了向量化、存储和数据检索的工具，以及与客户端应用程序无缝集成的 API。

## 功能

- **向量化**：将文本数据转换为向量表示，以实现高效的相似性搜索。
- **存储**：使用数据库后端存储和管理向量化数据。
- **搜索**：执行相似性搜索以检索相关数据。
- **API 集成**：提供 RESTful API 供客户端交互。
- **前端仪表盘**：基于 Next.js 的仪表盘，用于管理和监控系统。
- **Docker 化环境**：预配置的 Docker 设置，便于部署。

## 项目结构

```
rag_mcp/
├── api/                # 向量化、上传和搜索的后端 API
├── assets/             # 静态资源
├── core/               # 核心服务和模式
├── database/           # 数据库模型和初始化
├── docker/             # Docker 配置文件
├── front/              # 基于 Next.js 的前端仪表盘
├── logs/               # 日志文件
├── mcp_server/         # MCP 服务器实现
├── test/               # 系统测试用例
├── upload/             # 上传的文件
├── utils/              # 工具函数
```

## 安装

### 前置条件

- Python 3.9+
- Node.js 18+
- Docker
- PostgreSQL

### 步骤

1. 克隆仓库：
   ```bash
   git clone https://github.com/hellolukeding/rag_mcp.git
   cd rag_mcp
   ```
2. 设置 Python 环境：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. 安装前端依赖：
   ```bash
   cd front/client
   npm install
   ```
4. 启动 Docker 容器：
   ```bash
   cd ../../docker
   docker-compose up -d
   ```
5. 运行后端服务器：
   ```bash
   cd ../mcp_server/server
   python mcp_server.py
   ```
6. 启动前端：
   ```bash
   cd ../../front/client
   npm run dev
   ```

## 使用方法

### 访问仪表盘

打开浏览器并导航到 `http://localhost:3000` 访问前端仪表盘。

### API 接口

- **启动验证码**：`POST /api/v1/auth/captcha/start`
- **上传文件**：`POST /api/v1/upload`
- **搜索**：`GET /api/v1/search`

详细的 API 文档请参考 `api/` 目录。

## 连接 MCP 服务器

MCP 服务器提供了一个 JSON-RPC 接口，允许客户端与其交互。以下是连接 MCP 服务器的步骤：

### 启动 MCP 服务器

确保 MCP 服务器已启动并运行，默认监听地址（Streamable HTTP 模式）为 `http://127.0.0.1:18080`。如果你需要使用 stdio 或其他 transport，请使用对应的启动参数。

### 使用 Python 客户端连接

以下是一个使用 Python 的示例代码：

```python
import requests
import json

# MCP 服务器地址
MCP_SERVER_URL = "http://127.0.0.1:18080/jsonrpc"

# 定义 JSON-RPC 请求
payload = {
    "jsonrpc": "2.0",
    "method": "vectorize",
    "params": {
        "text": "这是一个示例文本"
    },
    "id": 1
}

# 发送请求
response = requests.post(MCP_SERVER_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})

# 处理响应
if response.status_code == 200:
    result = response.json()
    print("向量化结果:", result)
else:
    print("请求失败，状态码:", response.status_code)
```

### 参数说明

- `method`: 调用的 MCP 方法，例如 `vectorize`。
- `params`: 方法的参数，例如文本内容。
- `id`: 请求的唯一标识符。

### 可用方法

- `vectorize`: 将文本转换为向量。
- `search`: 根据向量执行相似性搜索。
- `upload`: 上传文件。

更多方法和参数请参考 `api/` 目录中的文档。

## 测试

运行测试套件以确保所有组件正常工作：

```bash
pytest
```

## 贡献

1. Fork 此仓库。
2. 创建新分支：
   ```bash
   git checkout -b feature-branch
   ```
3. 提交更改：
   ```bash
   git commit -m "添加新功能"
   ```
4. 推送到分支：
   ```bash
   git push origin feature-branch
   ```
5. 打开 Pull Request。

## 许可证

此项目基于 MIT 许可证授权。详情请参阅 LICENSE 文件。

---

English version: [README_en.md](README_en.md)

## 鸣谢

- [Next.js](https://nextjs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker](https://www.docker.com/)
