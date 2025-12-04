"use client";

import FileTable from "@/components/files/FileTable";
import UploadModal from "@/components/files/UploadModal";
import { deleteFile, FileInfo, getFiles } from "@/services/file";
import { CloudUploadOutlined, ReloadOutlined } from "@ant-design/icons";
import { App, Button } from "antd";
import { useEffect, useState } from "react";

export default function FilesPage() {
    const { message } = App.useApp();
    const [files, setFiles] = useState<FileInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploadModalOpen, setUploadModalOpen] = useState(false);

    const fetchFiles = async () => {
        setLoading(true);
        try {
            const res = await getFiles();
            if (res.code === 200) {
                setFiles(res.data.files);
            } else {
                message.error(res.msg || "获取文件列表失败");
            }
        } catch (error) {
            message.error("网络错误，无法获取文件列表");
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (fileId: string) => {
        try {
            const res = await deleteFile(fileId);
            if (res.code === 200) {
                message.success("文件删除成功");
                fetchFiles(); // Refresh list
            } else {
                message.error(res.msg || "删除失败");
            }
        } catch (error) {
            message.error("删除请求失败");
            console.error(error);
        }
    };

    useEffect(() => {
        fetchFiles();
    }, []);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">文件管理</h2>
                    <p className="text-gray-500 mt-1">管理您的知识库文件，支持上传、查看和删除</p>
                </div>
                <div className="space-x-3">
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={fetchFiles}
                        loading={loading}
                    >
                        刷新
                    </Button>
                    <Button
                        type="primary"
                        icon={<CloudUploadOutlined />}
                        onClick={() => setUploadModalOpen(true)}
                        className="bg-black hover:bg-gray-800"
                    >
                        上传文件
                    </Button>
                </div>
            </div>

            <FileTable
                files={files}
                loading={loading}
                onDelete={handleDelete}
            />

            <UploadModal
                open={uploadModalOpen}
                onClose={() => setUploadModalOpen(false)}
                onSuccess={fetchFiles}
            />
        </div>
    );
}
