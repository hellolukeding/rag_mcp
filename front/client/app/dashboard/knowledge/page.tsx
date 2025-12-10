"use client";

import { searchKnowledge, SearchResult } from "@/services/knowledge";
import { FileTextOutlined } from "@ant-design/icons";
import { App, Card, Empty, Input, Spin, Tag, Typography } from "antd";
import { useState } from "react";

const { Title, Paragraph, Text } = Typography;

export default function KnowledgePage() {
    const { message } = App.useApp();
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<SearchResult[]>([]);
    const [searched, setSearched] = useState(false);

    const handleSearch = async (value: string) => {
        if (!value.trim()) return;

        setLoading(true);
        setSearched(true);
        try {
            const res = await searchKnowledge({ query: value });
            if (res.code === 200) {
                setResults(res.data.results);
            } else {
                message.error(res.msg || "搜索失败");
            }
        } catch (error) {
            message.error("网络错误，无法执行搜索");
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6 max-w-5xl mx-auto">
            <div className="text-center space-y-4 py-8">
                <Title level={2}>知识库检索</Title>
                <Paragraph className="text-gray-500 text-lg">
                    基于 RAG 技术，从您的文档中检索相关信息
                </Paragraph>

                <div className="max-w-2xl mx-auto mt-8">
                    <Input.Search
                        placeholder="请输入您的问题或关键词..."
                        allowClear
                        enterButton="搜索"
                        size="large"
                        onSearch={handleSearch}
                        onChange={(e) => {
                            if (!e.target.value) {
                                setResults([]);
                                setSearched(false);
                            }
                        }}
                        loading={loading}
                        className="shadow-sm"
                    />
                </div>
            </div>

            <div className="mt-8">
                {loading ? (
                    <div className="text-center py-12">
                        <Spin size="large" tip="正在检索相关文档..." />
                    </div>
                ) : searched && results.length === 0 ? (
                    <Empty description="未找到相关内容，请尝试其他关键词" />
                ) : (
                    <div className="space-y-4">
                        {results.map((item, idx) => (
                            <div key={item.metadata?.chunk_id ?? `${idx}-${item.title?.slice(0, 20) || idx}`}>
                                <Card
                                    hoverable
                                    className="border-gray-200 shadow-sm hover:shadow-md transition-shadow"
                                >
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="flex items-center gap-2">
                                            <FileTextOutlined className="text-blue-500" />
                                            <Text strong className="text-lg">{item.title}</Text>
                                        </div>
                                        <Tag color={item.similarity_score > 0.8 ? "green" : "blue"}>
                                            相似度: {(item.similarity_score * 100).toFixed(1)}%
                                        </Tag>
                                    </div>

                                    <div className="bg-gray-50 p-4 rounded-md mb-3">
                                        <Paragraph
                                            ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
                                            className="text-gray-600 mb-0"
                                        >
                                            {item.content}
                                        </Paragraph>
                                    </div>

                                    <div className="flex justify-end text-xs text-gray-400">
                                        <span>Chunk ID: {item.metadata?.chunk_id}</span>
                                    </div>
                                </Card>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
