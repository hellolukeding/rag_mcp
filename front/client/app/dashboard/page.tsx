"use client";

import { ApiOutlined, CloudUploadOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Card, Col, Row, Statistic } from 'antd';

export default function DashboardPage() {
    return (
        <div>
            <h2 className="text-2xl font-bold mb-6 text-gray-800">仪表盘概览</h2>
            <Row gutter={[16, 16]}>
                <Col xs={24} sm={8}>
                    <Card variant="borderless" className="shadow-sm hover:shadow-md transition-shadow">
                        <Statistic
                            title="总文件数"
                            value={128}
                            precision={0}
                            styles={{ content: { color: '#3f8600' } }}
                            prefix={<CloudUploadOutlined />}
                            suffix="个"
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card variant="borderless" className="shadow-sm hover:shadow-md transition-shadow">
                        <Statistic
                            title="向量化完成率"
                            value={98.5}
                            precision={1}
                            styles={{ content: { color: '#cf1322' } }}
                            prefix={<ThunderboltOutlined />}
                            suffix="%"
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={8}>
                    <Card variant="borderless" className="shadow-sm hover:shadow-md transition-shadow">
                        <Statistic
                            title="API 调用次数"
                            value={9342}
                            precision={0}
                            prefix={<ApiOutlined />}
                            suffix=""
                        />
                    </Card>
                </Col>
            </Row>

            <div className="mt-8">
                <Card title="最近活动" variant="borderless" className="shadow-sm">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between border-b pb-2 border-gray-100">
                            <span className="text-gray-600">系统初始化完成</span>
                            <span className="text-gray-400 text-sm">2025-12-03 10:00</span>
                        </div>
                        <div className="flex items-center justify-between border-b pb-2 border-gray-100">
                            <span className="text-gray-600">上传了文件 <span className="font-medium text-blue-600">document.pdf</span></span>
                            <span className="text-gray-400 text-sm">2025-12-03 10:05</span>
                        </div>
                        <div className="flex items-center justify-between border-b pb-2 border-gray-100">
                            <span className="text-gray-600">向量化任务 <span className="font-mono bg-gray-100 px-1 rounded">#123</span> 完成</span>
                            <span className="text-gray-400 text-sm">2025-12-03 10:06</span>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
