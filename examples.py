import asyncio
import httpx
import json


class RAGMCPAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    async def create_document(self, title: str, content: str, metadata: dict = None):
        """创建文档示例"""
        async with httpx.AsyncClient() as client:
            data = {
                "title": title,
                "content": content,
                "metadata": metadata
            }
            response = await client.post(f"{self.base_url}/api/v1/documents", json=data)
            return response.json()
    
    async def search_documents(self, query: str, limit: int = 10, threshold: float = 0.7):
        """搜索文档示例"""
        async with httpx.AsyncClient() as client:
            data = {
                "query": query,
                "limit": limit,
                "threshold": threshold
            }
            response = await client.post(f"{self.base_url}/api/v1/search", json=data)
            return response.json()
    
    async def mcp_query(self, query: str, use_context: bool = True, max_documents: int = 5):
        """MCP增强查询示例"""
        async with httpx.AsyncClient() as client:
            data = {
                "query": query,
                "use_context": use_context,
                "max_documents": max_documents
            }
            response = await client.post(f"{self.base_url}/api/v1/mcp/query", json=data)
            return response.json()
    
    async def get_documents(self):
        """获取所有文档"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/documents")
            return response.json()
    
    async def get_stats(self):
        """获取统计信息"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/v1/stats")
            return response.json()


async def demo_basic_operations():
    """演示基本操作"""
    client = RAGMCPAPIClient()
    
    print("=== RAG-MCP API 示例 ===\n")
    
    # 1. 创建示例文档
    print("1. 创建示例文档...")
    documents = [
        {
            "title": "Python 编程基础",
            "content": "Python是一种高级编程语言，具有简洁的语法和强大的功能。它广泛用于Web开发、数据科学、人工智能等领域。Python支持面向对象编程、函数式编程等多种编程范式。",
            "metadata": {"category": "programming", "language": "python"}
        },
        {
            "title": "机器学习入门",
            "content": "机器学习是人工智能的一个重要分支，通过算法让计算机从数据中学习模式。常见的机器学习算法包括线性回归、决策树、神经网络等。机器学习在图像识别、自然语言处理等领域有广泛应用。",
            "metadata": {"category": "ai", "level": "beginner"}
        },
        {
            "title": "FastAPI 框架",
            "content": "FastAPI是一个现代、快速的Python Web框架，用于构建API。它基于标准的Python类型提示，自动生成API文档，支持异步编程，性能优异。FastAPI特别适合构建RESTful API和微服务。",
            "metadata": {"category": "web", "framework": "fastapi"}
        }
    ]
    
    created_docs = []
    for doc in documents:
        try:
            result = await client.create_document(**doc)
            created_docs.append(result)
            print(f"✓ 创建文档: {doc['title']}")
        except Exception as e:
            print(f"✗ 创建文档失败: {e}")
    
    print(f"\n创建了 {len(created_docs)} 个文档\n")
    
    # 2. 获取统计信息
    print("2. 获取统计信息...")
    try:
        stats = await client.get_stats()
        print(f"✓ 总文档数: {stats['total_documents']}")
        print(f"✓ 总字符数: {stats['total_characters']}")
        print(f"✓ 平均文档长度: {stats['average_document_length']:.2f}\n")
    except Exception as e:
        print(f"✗ 获取统计信息失败: {e}\n")
    
    # 3. 搜索文档
    print("3. 搜索文档...")
    queries = [
        "Python编程",
        "机器学习算法",
        "API开发",
        "Web框架"
    ]
    
    for query in queries:
        try:
            results = await client.search_documents(query, limit=3, threshold=0.3)
            print(f"查询: '{query}'")
            print(f"找到 {results['total_results']} 个相关文档:")
            for result in results['results']:
                print(f"  - {result['title']} (相似度: {result['similarity_score']:.3f})")
            print()
        except Exception as e:
            print(f"✗ 搜索失败: {e}\n")
    
    # 4. MCP增强查询（需要MCP服务运行）
    print("4. MCP增强查询...")
    mcp_queries = [
        "如何开始学习Python？",
        "机器学习和深度学习有什么区别？",
        "FastAPI相比其他框架有什么优势？"
    ]
    
    for query in mcp_queries:
        try:
            result = await client.mcp_query(query, max_documents=2)
            print(f"MCP查询: '{query}'")
            print(f"使用了 {result['source_count']} 个文档作为上下文")
            print(f"回答: {result['response'][:200]}...")
            print()
        except Exception as e:
            print(f"✗ MCP查询失败 (可能MCP服务未运行): {e}\n")


async def demo_advanced_features():
    """演示高级功能"""
    client = RAGMCPAPIClient()
    
    print("=== 高级功能演示 ===\n")
    
    # 获取所有文档用于演示
    try:
        documents = await client.get_documents()
        if not documents:
            print("没有找到文档，请先运行基本操作演示")
            return
        
        print(f"当前有 {len(documents)} 个文档\n")
        
        # 演示关键词提取
        print("1. 关键词提取...")
        for doc in documents[:2]:  # 只演示前2个文档
            try:
                async with httpx.AsyncClient() as http_client:
                    response = await http_client.post(
                        f"http://localhost:8000/api/v1/mcp/keywords/{doc['id']}"
                    )
                    if response.status_code == 200:
                        result = response.json()
                        print(f"文档: {doc['title']}")
                        print(f"关键词: {', '.join(result['keywords'])}")
                        print()
                    else:
                        print(f"关键词提取失败: {response.status_code}")
            except Exception as e:
                print(f"✗ 关键词提取失败: {e}")
        
        # 演示文档摘要
        print("2. 文档摘要...")
        try:
            doc_ids = [doc['id'] for doc in documents[:3]]
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    "http://localhost:8000/api/v1/mcp/summarize",
                    json={"document_ids": doc_ids}
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"摘要基于 {result['document_count']} 个文档:")
                    print(f"{result['summary'][:300]}...")
                    print()
                else:
                    print(f"摘要生成失败: {response.status_code}")
        except Exception as e:
            print(f"✗ 摘要生成失败: {e}")
        
    except Exception as e:
        print(f"✗ 获取文档失败: {e}")


async def main():
    """主函数"""
    print("启动RAG-MCP API演示...")
    print("确保API服务正在运行 (python main.py)\n")
    
    try:
        # 检查API是否可用
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/api/v1/health")
            if response.status_code != 200:
                print("❌ API服务未运行，请先启动服务")
                return
        
        print("✅ API服务运行正常\n")
        
        # 运行基本操作演示
        await demo_basic_operations()
        
        # 运行高级功能演示
        await demo_advanced_features()
        
        print("演示完成！")
        print("\n可以访问 http://localhost:8000/docs 查看API文档")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
