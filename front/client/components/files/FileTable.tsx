"use client";

import { formatBytes } from "@/lib/utils";
import { FileInfo } from "@/services/file";
import { DeleteOutlined, FileMarkdownOutlined, FilePdfOutlined, FileTextOutlined, FileWordOutlined } from "@ant-design/icons";
import { Badge, Button, Popconfirm, Table, Tooltip } from "antd";
import type { ColumnsType } from "antd/es/table";

interface FileTableProps {
    files: FileInfo[];
    loading: boolean;
    onDelete: (fileId: string) => void;
}

const getFileIcon = (fileType: string) => {
    switch (fileType) {
        case '.pdf':
            return <FilePdfOutlined className="text-red-500 text-xl" />;
        case '.docx':
            return <FileWordOutlined className="text-blue-500 text-xl" />;
        case '.md':
        case '.markdown':
            return <FileMarkdownOutlined className="text-gray-800 text-xl" />;
        default:
            return <FileTextOutlined className="text-gray-500 text-xl" />;
    }
};

const getStatusBadge = (status: string) => {
    switch (status) {
        case 'completed':
            return <Badge status="success" text="已完成" />;
        case 'processing':
            return <Badge status="processing" text="处理中" />;
        case 'failed':
            return <Badge status="error" text="失败" />;
        default:
            return <Badge status="default" text="等待中" />;
    }
};

const FileTable: React.FC<FileTableProps> = ({ files, loading, onDelete }) => {
    const columns: ColumnsType<FileInfo> = [
        {
            title: '类型',
            dataIndex: 'file_type',
            key: 'file_type',
            width: 80,
            align: 'center',
            render: (type) => getFileIcon(type),
        },
        {
            title: '文件名',
            dataIndex: 'original_name',
            key: 'original_name',
            render: (text) => <span className="font-medium">{text}</span>,
        },
        {
            title: '大小',
            dataIndex: 'file_size',
            key: 'file_size',
            width: 120,
            render: (size) => formatBytes(size),
        },
        {
            title: '状态',
            dataIndex: 'vectorized_status',
            key: 'vectorized_status',
            width: 120,
            render: (status) => getStatusBadge(status),
        },
        {
            title: '上传时间',
            dataIndex: 'created_at',
            key: 'created_at',
            width: 180,
            render: (date) => new Date(date).toLocaleString(),
        },
        {
            title: '操作',
            key: 'action',
            width: 100,
            align: 'center',
            render: (_, record) => (
                <Popconfirm
                    title="确定要删除这个文件吗？"
                    description="删除后无法恢复，且相关的向量数据也会被清除。"
                    onConfirm={() => onDelete(record.file_id)}
                    okText="确定"
                    cancelText="取消"
                    okButtonProps={{ danger: true }}
                >
                    <Tooltip title="删除文件">
                        <Button type="text" danger icon={<DeleteOutlined />} />
                    </Tooltip>
                </Popconfirm>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={files}
            rowKey="file_id"
            loading={loading}
            pagination={{
                defaultPageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 个文件`,
            }}
            className="bg-white rounded-lg shadow-sm"
        />
    );
};

export default FileTable;
