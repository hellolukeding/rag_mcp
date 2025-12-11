# 向量化服务测试脚本

English: [README_en.md](README_en.md)

本目录包含了用于测试 `core.vectorlize` 模块功能的各种测试脚本。

## 测试脚本说明

### 1. test_vectorize.py - 功能测试

全面测试向量化服务的各项功能，包括：

- 单任务添加和处理
- 多任务并发处理
- 任务状态监控
- 文件向量化状态查询
- 数据库记录检查

**使用方法：**

```bash
python test_vectorize.py
```

### 2. test_performance.py - 性能测试

测试向量化服务的性能指标，包括：

- 不同大小文件的处理时间
- 并发处理能力
- 内存使用情况监控
- 错误处理性能

**使用方法：**

```bash
python test_performance.py
```

**注意：** 性能测试中的内存监控功能需要安装 `psutil`：

```bash
pip install psutil
```

### 3. test_cli.py - 命令行工具

提供命令行界面来测试向量化功能，支持交互式操作。

**使用方法：**

添加单个文件任务：

```bash
python test_cli.py add --file sample_ai_document.txt
```

处理文件并等待完成：

```bash
python test_cli.py process --file sample_ai_document.txt
```

监控指定任务：

```bash
python test_cli.py monitor --task-id <task_id>
```

列出所有任务：

```bash
python test_cli.py list
```

检查文件向量化状态：

```bash
python test_cli.py status
python test_cli.py status --file-id <file_id>
```

批量处理目录：

```bash
python test_cli.py batch --directory /path/to/docs
python test_cli.py batch --directory /path/to/docs --pattern "*.txt"
```

### 4. sample_ai_document.txt - 测试文档

一个关于人工智能技术的样例文档，用于测试向量化功能。

## 环境要求

### 必需的环境变量

在运行测试之前，请确保设置了以下环境变量：

```bash
export OPENAI_API_KEY="your_api_key_here"
export MODEL_NAME="Qwen/Qwen3-Embedding-8B"  # 或其他支持的模型
export OPENAI_URL="https://api.siliconflow.cn/v1"  # 或其他API端点
```

### Python 依赖

确保已安装项目的所有依赖：

```bash
pip install -r ../requirements.txt
```

## 测试流程

### 基础功能测试流程

1. 首先运行功能测试，确保基本功能正常：

   ```bash
   python test_vectorize.py
   ```

2. 检查测试结果，确认所有测试通过

3. 可选：运行性能测试来评估系统性能：
   ```bash
   python test_performance.py
   ```

### 命令行工具使用流程

1. 使用样例文档进行快速测试：

   ```bash
   python test_cli.py process --file sample_ai_document.txt
   ```

2. 监控处理进度并查看结果

3. 检查文件向量化状态：
   ```bash
   python test_cli.py status
   ```

## 测试结果说明

### 成功的测试应该显示：

- ✓ 所有测试用例通过
- 任务状态正确转换（pending → processing → completed）
- 文件向量化状态正确更新
- 数据库中正确存储了文档和向量数据

### 常见问题解决

1. **环境变量未设置**

   ```
   错误：缺少必要的环境变量
   解决：检查并设置 OPENAI_API_KEY、MODEL_NAME、OPENAI_URL
   ```

2. **API 调用失败**

   ```
   错误：获取向量失败
   解决：检查API密钥是否正确，网络连接是否正常
   ```

3. **文件路径问题**

   ```
   错误：文件不存在
   解决：使用绝对路径或相对于当前工作目录的正确路径
   ```

4. **数据库连接问题**
   ```
   错误：数据库初始化失败
   解决：检查数据库文件权限，确保有写入权限
   ```

## 性能基准参考

基于测试环境的典型性能指标：

- 小文件（500 字符）：1-3 秒
- 中等文件（2000 字符）：3-8 秒
- 大文件（8000 字符）：8-20 秒
- 超大文件（15000 字符）：15-40 秒

_注：实际性能取决于网络延迟、API 响应时间和系统配置_

## 扩展测试

### 自定义测试文件

可以创建自己的测试文件来测试特定场景：

1. 创建包含特殊字符的文件
2. 创建不同编码的文件（UTF-8, GBK 等）

---

English version: [README_en.md](README_en.md) 3. 创建超大文件测试性能极限 4. 创建空文件或格式错误的文件测试错误处理

### 批量测试

使用命令行工具的批处理功能测试大量文件：

```bash
# 创建测试文件目录
mkdir test_docs
echo "测试文档1" > test_docs/doc1.txt
echo "测试文档2" > test_docs/doc2.txt

# 批量处理
python test_cli.py batch --directory test_docs
```

## 日志和调试

所有测试脚本都使用项目的 logger 进行日志输出。日志级别可以通过环境变量控制：

```bash
export LOG_LEVEL=DEBUG  # 显示详细调试信息
export LOG_LEVEL=INFO   # 显示一般信息（默认）
export LOG_LEVEL=ERROR  # 只显示错误信息
```

日志文件位置：`../logs/` 目录

## 注意事项

1. **API 配额限制**：注意 API 调用的配额和频率限制
2. **并发限制**：默认最大并发数为 2，可根据需要调整
3. **文件大小**：超大文件可能导致内存使用过高
4. **网络依赖**：所有测试都需要网络连接来调用向量化 API

## 贡献和反馈

如果发现测试脚本的问题或有改进建议，请：

1. 检查日志文件获取详细错误信息
2. 记录复现步骤和环境信息
3. 提交 issue 或 pull request
