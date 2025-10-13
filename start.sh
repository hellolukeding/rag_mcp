#!/bin/bash

echo "启动 RAG-MCP API 服务..."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python -m venv .venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt 2>/dev/null || echo "requirements.txt 不存在，跳过安装"

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
MODEL_NAME=text-embedding-ada-002
OPENAI_URL=https://api.openai.com/v1
MCP_URL=http://localhost:3000
EOF
    echo "请编辑 .env 文件设置正确的API密钥"
fi

# 启动服务
echo "启动API服务..."
python main.py
