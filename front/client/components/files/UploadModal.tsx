"use client";

import { uploadFile } from "@/services/file";
import { InboxOutlined } from "@ant-design/icons";
import { App, Modal, Upload } from "antd";
import type { UploadFile, UploadProps } from "antd/es/upload/interface";
import { useState } from "react";

const { Dragger } = Upload;

interface UploadModalProps {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const UploadModal: React.FC<UploadModalProps> = ({ open, onClose, onSuccess }) => {
    const { message } = App.useApp();
    const [fileList, setFileList] = useState<UploadFile[]>([]);
    const [uploading, setUploading] = useState(false);

    const handleUpload = async () => {
        if (fileList.length === 0) {
            message.warning("请先选择文件");
            return;
        }

        setUploading(true);
        try {
            // Upload files sequentially
            for (const file of fileList) {
                if (file.originFileObj) {
                    const res = await uploadFile(file.originFileObj);
                    if (res.code !== 200 && res.code !== 201) {
                        throw new Error(res.msg || `文件 ${file.name} 上传失败`);
                    }
                }
            }
            message.success("文件上传成功");
            setFileList([]);
            onSuccess();
            onClose();
        } catch (error) {
            message.error("文件上传失败");
            console.error(error);
        } finally {
            setUploading(false);
        }
    };

    const props: UploadProps = {
        onRemove: (file) => {
            const index = fileList.indexOf(file);
            const newFileList = fileList.slice();
            newFileList.splice(index, 1);
            setFileList(newFileList);
        },
        beforeUpload: (file) => {
            // Check file type
            const isAllowed =
                file.type === 'application/pdf' ||
                file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                file.name.endsWith('.md') ||
                file.name.endsWith('.markdown');

            if (!isAllowed) {
                message.error(`${file.name} 不是支持的文件格式 (PDF, DOCX, Markdown)`);
                return Upload.LIST_IGNORE;
            }

            setFileList((prev) => [...prev, file]);
            return false; // Prevent auto upload
        },
        fileList,
        multiple: true,
    };

    return (
        <Modal
            title="上传文件"
            open={open}
            onCancel={onClose}
            onOk={handleUpload}
            confirmLoading={uploading}
            okText={uploading ? "上传中..." : "开始上传"}
            cancelText="取消"
            width={600}
        >
            <div className="py-4">
                <Dragger {...props} style={{ padding: '20px' }}>
                    <p className="ant-upload-drag-icon">
                        <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                    <p className="ant-upload-hint">
                        支持单个或批量上传。支持的文件格式：PDF, Word (.docx), Markdown (.md)
                    </p>
                </Dragger>
            </div>
        </Modal>
    );
};

export default UploadModal;
