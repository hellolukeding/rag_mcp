# RAG-MCP 文档向量化服务

基于 FastAPI 的文档上传、文本提取和向量化服务，支持调用在线 embedding 模型并将文档块和向量存储到本地 SQLite 数据库。

## 项目功能

- 🔥 **文件上传**：支持上传 `.docx`、`.pdf`、`.txt`、`.md` 格式的文档
- 📄 **文档解析**：自动提取文档中的文本内容
- 🧠 **智能向量化**：调用在线 embedding 模型生成文本向量
- 💾 **数据存储**：将文档和向量数据存储到 SQLite 数据库
- 🌐 **REST API**：提供完整的 RESTful API 接口
- 📚 **自动文档**：集成 Swagger UI 交互式 API 文档

## 系统要求

- Python 3.12+
- 依赖包详见 `pyproject.toml` (FastAPI, uvicorn, python-docx, pypdf2, python-dotenv, openai 等)

## 快速开始

### 1. 安装依赖

推荐使用 Poetry 管理依赖：

```bash
poetry install
poetry shell
```

或使用 pip：

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件（项目已包含示例文件），配置以下环境变量：

```env
# OpenAI 兼容的 API 配置
OPENAI_API_KEY=sk-xxxx
OPENAI_URL=https://api.siliconflow.cn/v1

# 可选：embedding 模型名称（默认为 Qwen/Qwen3-Embedding-8B）
MODEL_NAME=Qwen/Qwen3-Embedding-8B
```

### 3. 启动服务

```bash
python main.py
```

或使用 uvicorn：

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问 API 文档

打开浏览器访问：http://localhost:8000/docs 查看交互式 API 文档

## API 接口说明

### 文件上传接口

**POST** `/api/v1/files` - 上传文档文件

支持的文件格式：

- `.docx` - Word 文档
- `.pdf` - PDF 文档
- `.txt` - 纯文本文件
- `.md` - Markdown 文档

**请求示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/files" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.docx"
```

**响应示例：**

```json
{
  "code": 200,
  "msg": "文件上传成功",
  "data": {
    "file_id": "b9cbbc03-6608-4b17-95e5-281a5a8f4e83",
    "original_name": "document.docx",
    "file_size": 12345,
    "file_type": ".docx"
  }
}
```

### 文件向量化接口

**POST** `/api/v1/vectorize` - 向量化已上传的文件

**请求示例：**

```bash
curl -X POST "http://localhost:8000/api/v1/vectorize" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "upload/b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx"}'
```

**响应示例：**

```json
{
  "success": true,
  "message": "文件向量化成功",
  "data": {
    "document_id": 1,
    "filename": "document.docx",
    "file_path": "upload/b9cbbc03-6608-4b17-95e5-281a5a8f4e83.docx",
    "total_chunks": 10,
    "text_length": 12345,
    "file_type": ".docx"
  }
}
```

### 其他接口

- **GET** `/api/v1/files` - 获取所有文件列表
- **GET** `/api/v1/files/{file_id}` - 获取指定文件信息
- **DELETE** `/api/v1/files/{file_id}` - 删除指定文件

## 数据库

项目使用 SQLite 作为本地数据库，存储以下数据：

- **文件信息表**：存储上传文件的基本信息
- **文档表**：存储解析后的文档数据
- **文档块表**：存储分割后的文本块和对应的向量数据

数据库在应用启动时自动初始化，相关代码见 `database/models.py`。

## 工作流程

1. **文件上传**：通过 `/api/v1/files` 接口上传文档文件
2. **文档解析**：系统自动识别文件类型并提取文本内容
3. **文本分块**：将长文档分割成适合向量化的文本块
4. **向量生成**：调用配置的 embedding 模型生成文本向量
5. **数据存储**：将文档信息、文本块和向量数据存储到数据库

## 故障排除

### 向量化失败

- 检查 `OPENAI_API_KEY` 和 `OPENAI_URL` 配置是否正确
- 确认网络连接正常，可以访问 embedding 服务
- 查看服务日志获取详细错误信息

### 文件解析失败

- 确认文件格式是否在支持列表中
- 检查文件是否损坏或加密
- 对于 PDF 文件，尝试使用其他 PDF 查看器确认文件完整性

### 数据库相关问题

- 确认项目目录有写入权限
- 检查 SQLite 数据库文件是否正常创建
- 重启服务以重新初始化数据库

## 开发计划

- [ ] 支持更多文件格式（如 .txt, .rtf 等）
- [ ] 批量向量化处理优化
- [ ] 添加文本相似度搜索功能
- [ ] 支持自定义文本分块策略
- [ ] 添加用户认证和权限管理
- [ ] 完善单元测试和集成测试

## 技术栈

- **Web 框架**：FastAPI
- **异步运行时**：Uvicorn
- **数据库**：SQLite + aiosqlite
- **文档处理**：python-docx, PyPDF2
- **向量服务**：OpenAI 兼容 API
- **环境管理**：python-dotenv
- **依赖管理**：Poetry
