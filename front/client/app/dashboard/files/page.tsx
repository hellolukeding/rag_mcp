"use client";

import FileTable from "@/components/files/FileTable";
import TaskDrawer from "@/components/files/TaskDrawer";
import UploadModal from "@/components/files/UploadModal";
import { deleteFile, FileInfo, getFiles } from "@/services/file";
import { createVectorizeTask } from "@/services/vectorize";
import { CloudUploadOutlined, ReloadOutlined, UnorderedListOutlined } from "@ant-design/icons";
import { App, Button } from "antd";
import { useEffect, useState } from "react";

export default function FilesPage() {
    const { message } = App.useApp();
    const [files, setFiles] = useState<FileInfo[]>([]);
    const [loading, setLoading] = useState(false);
    const [uploadModalOpen, setUploadModalOpen] = useState(false);
    const [taskDrawerOpen, setTaskDrawerOpen] = useState(false);

    const fetchFilesData = async () => {
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
        }
    };

    const refreshFiles = async () => {
        setLoading(true);
        await fetchFilesData();
        setLoading(false);
    };

    const handleDelete = async (fileId: string) => {
        try {
            const res = await deleteFile(fileId);
            if (res.code === 200) {
                message.success("文件删除成功");
                refreshFiles(); // Refresh list
            } else {
                message.error(res.msg || "删除失败");
            }
        } catch (error) {
            message.error("删除请求失败");
            console.error(error);
        }
    };

    const handleVectorize = async (file: FileInfo) => {
        try {
            const res = await createVectorizeTask({
                file_id: file.file_id,
                file_path: file.file_path
            });

            if (res.success) {
                message.success("向量化任务已创建");
                setTaskDrawerOpen(true); // Open drawer to show progress
                refreshFiles(); // Refresh status
            } else {
                message.error(res.message || "创建任务失败");
            }
        } catch (error) {
            message.error("请求失败");
            console.error(error);
        }
    };

    useEffect(() => {
        refreshFiles();
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
                        icon={<UnorderedListOutlined />}
                        onClick={() => setTaskDrawerOpen(true)}
                    >
                        任务列表
                    </Button>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={refreshFiles}
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
                onVectorize={handleVectorize}
            />

            <UploadModal
                open={uploadModalOpen}
                onClose={() => setUploadModalOpen(false)}
                onSuccess={refreshFiles}
            />

            <TaskDrawer
                open={taskDrawerOpen}
                onClose={() => setTaskDrawerOpen(false)}
                onTaskUpdate={fetchFilesData}
            />
        </div>
    );
}
