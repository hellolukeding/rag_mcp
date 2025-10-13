from typing import Any, Dict, List, Optional
import httpx
import json


class MCPClient:
    """MCP (Model Context Protocol) 客户端"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        
    async def send_message(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """向MCP服务发送消息"""
        async with httpx.AsyncClient() as client:
            payload = {
                "message": message,
                "context": context or {}
            }
            
            response = await client.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=30.0
            )
            
            if response.status_code != 200:
                raise Exception(f"MCP request failed: {response.status_code}")
            
            return response.json()
    
    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用的工具列表"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/tools")
            
            if response.status_code != 200:
                raise Exception(f"Failed to get tools: {response.status_code}")
            
            return response.json().get("tools", [])
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定工具"""
        async with httpx.AsyncClient() as client:
            payload = {
                "tool": tool_name,
                "parameters": parameters
            }
            
            response = await client.post(
                f"{self.base_url}/tools/{tool_name}",
                json=payload,
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise Exception(f"Tool call failed: {response.status_code}")
            
            return response.json()


class RAGMCPIntegration:
    """RAG与MCP的集成服务"""
    
    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client
    
    async def enhanced_search(self, query: str, documents: List[Dict]) -> Dict[str, Any]:
        """使用MCP增强的文档搜索"""
        # 准备文档上下文
        context = {
            "documents": [
                {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"][:500] + "..." if len(doc["content"]) > 500 else doc["content"]
                }
                for doc in documents
            ],
            "query": query
        }
        
        # 向MCP发送查询
        message = f"基于以下文档回答问题: {query}"
        response = await self.mcp_client.send_message(message, context)
        
        return {
            "original_query": query,
            "mcp_response": response,
            "context_documents": documents
        }
    
    async def generate_summary(self, documents: List[Dict]) -> str:
        """生成文档摘要"""
        context = {
            "documents": [
                {
                    "title": doc["title"],
                    "content": doc["content"]
                }
                for doc in documents
            ]
        }
        
        message = "请为这些文档生成一个综合摘要"
        response = await self.mcp_client.send_message(message, context)
        
        return response.get("content", "")
    
    async def extract_keywords(self, content: str) -> List[str]:
        """提取关键词"""
        message = f"从以下内容中提取5-10个关键词: {content[:1000]}"
        response = await self.mcp_client.send_message(message)
        
        # 假设返回的内容包含关键词列表
        keywords_text = response.get("content", "")
        # 简单解析关键词（实际实现可能需要更复杂的解析）
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
        
        return keywords[:10]  # 限制最多10个关键词
