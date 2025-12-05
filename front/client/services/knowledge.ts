import { API_BASE_URL, ApiResponse } from './config';

export interface SearchResult {
    document_id: number;
    title: string;
    content: string;
    similarity_score: number;
    metadata?: {
        chunk_id: number;
        chunk_index: number;
    };
}

export interface QueryResponse {
    query: string;
    results: SearchResult[];
    total_results: number;
}

export interface QueryRequest {
    query: string;
    limit?: number;
    threshold?: number;
}

export const searchKnowledge = async (params: QueryRequest): Promise<ApiResponse<QueryResponse>> => {
    const response = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
    });
    return response.json();
};
