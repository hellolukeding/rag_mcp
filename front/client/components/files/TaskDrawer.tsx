"use client";

import { getAllTasks, VectorizeTask } from "@/services/vectorize";
import { CheckCircleOutlined, ClockCircleOutlined, CloseCircleOutlined, SyncOutlined } from "@ant-design/icons";
import { Drawer, Progress, Tag, Typography } from "antd";
import { useCallback, useEffect, useRef, useState } from "react";

const { Text } = Typography;

interface TaskDrawerProps {
    open: boolean;
    onClose: () => void;
    onTaskUpdate?: () => void;
}

const TaskDrawer: React.FC<TaskDrawerProps> = ({ open, onClose, onTaskUpdate }) => {
    const [tasks, setTasks] = useState<VectorizeTask[]>([]);
    const [loading, setLoading] = useState(false);
    const prevStatusesRef = useRef<Record<string, string>>({});

    const fetchTasks = useCallback(async () => {
        try {
            const res = await getAllTasks();
            if (res.success && res.data && res.data.tasks) {
                // Convert object to array if needed, or just use the array
                const tasksData = res.data.tasks;
                // If tasks is an object (dict), convert to array
                const tasksArray = Array.isArray(tasksData)
                    ? tasksData
                    : Object.values(tasksData);

                // Check for status changes
                let shouldUpdate = false;
                const newStatuses: Record<string, string> = {};

                tasksArray.forEach((task: any) => {
                    newStatuses[task.task_id] = task.status;
                    const prevStatus = prevStatusesRef.current[task.task_id];

                    if (prevStatus && prevStatus !== task.status) {
                        if (task.status === 'completed' || task.status === 'failed') {
                            shouldUpdate = true;
                        }
                    }
                });

                prevStatusesRef.current = newStatuses;

                if (shouldUpdate && onTaskUpdate) {
                    onTaskUpdate();
                }

                // Sort by created_at desc
                tasksArray.sort((a: VectorizeTask, b: VectorizeTask) =>
                    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                );

                setTasks(tasksArray as VectorizeTask[]);
            }
        } catch (error) {
            console.error("Failed to fetch tasks", error);
        }
    }, [onTaskUpdate]);

    useEffect(() => {
        if (open) {
            fetchTasks();
            const interval = setInterval(fetchTasks, 2000); // Poll every 2 seconds
            return () => clearInterval(interval);
        }
    }, [open, fetchTasks]);

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <CheckCircleOutlined className="text-green-500" />;
            case 'processing':
                return <SyncOutlined spin className="text-blue-500" />;
            case 'failed':
                return <CloseCircleOutlined className="text-red-500" />;
            default:
                return <ClockCircleOutlined className="text-gray-400" />;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'success';
            case 'processing': return 'processing';
            case 'failed': return 'error';
            default: return 'default';
        }
    };

    return (
        <Drawer
            title="向量化任务列表"
            placement="right"
            onClose={onClose}
            open={open}
            size="default"
        >
            <div className="flex flex-col">
                {tasks.map((item) => (
                    <div key={item.task_id} className="py-3 border-b border-gray-100 last:border-0">
                        <div className="flex items-start gap-3">
                            <div className="mt-1">
                                {getStatusIcon(item.status)}
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-center mb-1">
                                    <Text ellipsis style={{ maxWidth: 200 }} className="font-medium">
                                        {item.original_name}
                                    </Text>
                                    <Tag color={getStatusColor(item.status)} className="mr-0">
                                        {item.status}
                                    </Tag>
                                </div>

                                <div className="space-y-2 mt-2">
                                    <div className="flex justify-between text-xs text-gray-500">
                                        <span>进度: {item.chunks_processed}/{item.chunks_total} chunks</span>
                                        <span>{Math.round(item.progress)}%</span>
                                    </div>
                                    <Progress
                                        percent={item.progress}
                                        size="small"
                                        status={item.status === 'failed' ? 'exception' : item.status === 'completed' ? 'success' : 'active'}
                                        showInfo={false}
                                    />
                                    {item.error_message && (
                                        <div className="text-xs text-red-500 mt-1">
                                            错误: {item.error_message}
                                        </div>
                                    )}
                                    <div className="text-xs text-gray-400">
                                        创建于: {new Date(item.created_at).toLocaleString()}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </Drawer>
    );
};

export default TaskDrawer;
