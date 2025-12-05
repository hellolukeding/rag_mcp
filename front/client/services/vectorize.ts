import { API_BASE_URL } from './config';

export interface VectorizeTaskRequest {
    file_id: string;
    file_path: string;
}

export interface VectorizeTaskResponse {
    success: boolean;
    message: string;
    task_id?: string;
    data?: any;
}

export interface TaskStatusResponse {
    success: boolean;
    message: string;
    data?: any;
}

export interface VectorizeTask {
    task_id: string;
    file_id: string;
    original_name: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    error_message?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
    chunks_total: number;
    chunks_processed: number;
}

export const createVectorizeTask = async (params: VectorizeTaskRequest): Promise<VectorizeTaskResponse> => {
    const response = await fetch(`${API_BASE_URL}/task/vectorize`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
    });
    return response.json();
};

export const getAllTasks = async (): Promise<TaskStatusResponse> => {
    const response = await fetch(`${API_BASE_URL}/tasks`);
    return response.json();
};
