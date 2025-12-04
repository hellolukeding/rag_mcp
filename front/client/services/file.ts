import { API_BASE_URL, ApiResponse } from './config';

export interface FileInfo {
    file_id: string;
    original_name: string;
    file_name: string;
    file_path: string;
    file_type: string;
    file_size: number;
    created_at: string;
    vectorized_status: string;
    vectorized_at?: string;
}

export interface FileListResponse {
    files: FileInfo[];
    total: number;
}

export const getFiles = async (): Promise<ApiResponse<FileListResponse>> => {
    const response = await fetch(`${API_BASE_URL}/files`);
    return response.json();
};

export interface FileUploadResponse {
    file_id: string;
    original_name: string;
    file_size: number;
    file_type: string;
}

export const uploadFile = async (file: File): Promise<ApiResponse<FileUploadResponse>> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/files`, {
        method: 'POST',
        body: formData,
    });
    return response.json();
};

export const deleteFile = async (fileId: string): Promise<ApiResponse<null>> => {
    const response = await fetch(`${API_BASE_URL}/files/${fileId}`, {
        method: 'DELETE',
    });
    return response.json();
};
