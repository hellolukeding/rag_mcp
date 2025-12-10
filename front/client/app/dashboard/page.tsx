"use client";

import { getDashboardStats, getRecentFiles } from '@/services/dashboard';
import { ApiOutlined, CloudUploadOutlined, FileDoneOutlined, FileSearchOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { Alert, Card, Col, Row, Spin, Statistic, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useEffect, useState } from 'react';

interface DashboardStats {
  total_files: number;
  completed_files: number;
  pending_files: number;
  completion_rate: number;
  total_documents: number;
  mcp_calls: number;
}

interface RecentFile {
  id: number;
  file_id: string;
  original_name: string;
  file_name: string;
  file_path: string;
  file_type: string;
  file_size: number;
  vectorized: string;
  vectorized_at: string | null;
  created_at: string;
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentFiles, setRecentFiles] = useState<RecentFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [statsData, filesData] = await Promise.all([
          getDashboardStats(),
          getRecentFiles(5)
        ]);
        setStats(statsData);
        setRecentFiles(filesData.recent_files);
        setError(null);
      } catch (err) {
        setError('获取数据失败，请稍后重试');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // 设置定时刷新数据
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const columns: ColumnsType<RecentFile> = [
    {
      title: '文件名',
      dataIndex: 'original_name',
      key: 'original_name',
      render: (text) => <span className="font-medium">{text}</span>
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 100,
      render: (text) => (
        <Tag color={text === 'pdf' ? 'red' : text === 'docx' ? 'blue' : 'green'}>
          {text.toUpperCase()}
        </Tag>
      )
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 120,
      render: (size) => `${(size / 1024).toFixed(1)} KB`
    },
    {
      title: '状态',
      dataIndex: 'vectorized',
      key: 'vectorized',
      width: 120,
      render: (status) => {
        let color = 'default';
        let text = '';
        switch (status) {
          case 'completed':
            color = 'success';
            text = '已完成';
            break;
          case 'pending':
            color = 'warning';
            text = '待处理';
            break;
          case 'failed':
            color = 'error';
            text = '失败';
            break;
          default:
            text = '未知';
        }
        return <Tag color={color}>{text}</Tag>;
      }
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (date) => format(new Date(date), 'yyyy-MM-dd HH:mm', { locale: zhCN })
    }
  ];

  if (loading && !stats) {
    return (
      <div className="flex justify-center items-center h-full">
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4">
        <Alert message="错误" description={error} type="error" showIcon />
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">仪表盘概览</h2>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={8}>
          <Card
            className="shadow-sm hover:shadow-md transition-shadow"
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title="总文件数"
              value={stats?.total_files || 0}
              precision={0}
              styles={{ content: { color: '#3f8600' } }}
              prefix={<CloudUploadOutlined />}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card
            className="shadow-sm hover:shadow-md transition-shadow"
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title="向量化完成率"
              value={stats?.completion_rate || 0}
              precision={1}
              styles={{ content: { color: stats && stats.completion_rate > 80 ? '#3f8600' : '#cf1322' } }}
              prefix={<ThunderboltOutlined />}
              suffix="%"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card
            className="shadow-sm hover:shadow-md transition-shadow"
            styles={{ body: { padding: '16px' } }}
          >
            <Statistic
              title="MCP 调用次数"
              value={stats?.mcp_calls || 0}
              precision={0}
              styles={{ content: { color: '#1890ff' } }}
              prefix={<ApiOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 进度详情卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} md={12}>
          <Card
            title={<span><FileDoneOutlined /> 已完成向量化</span>}
            className="shadow-sm"
          >
            <div className="text-3xl font-bold text-green-600">
              {stats?.completed_files || 0}
            </div>
            <div className="text-gray-500 mt-2">
              共 {stats?.total_files || 0} 个文件
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card
            title={<span><FileSearchOutlined /> 待处理文件</span>}
            className="shadow-sm"
          >
            <div className="text-3xl font-bold text-orange-500">
              {stats?.pending_files || 0}
            </div>
            <div className="text-gray-500 mt-2">
              需要向量化处理
            </div>
          </Card>
        </Col>
      </Row>

      {/* 最近文件表格 */}
      <Row>
        <Col span={24}>
          <Card
            title="最近上传文件"
            className="shadow-sm"
          >
            <Table
              dataSource={recentFiles}
              columns={columns}
              pagination={false}
              rowKey="id"
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}