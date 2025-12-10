import { API_BASE_URL, ApiResponse } from './config';

export interface McpStatus {
    running: boolean;
    pid?: number;
    uptime_seconds?: number | null;
}

export const getMcpStatus = async (): Promise<ApiResponse<McpStatus>> => {
    try {
        const res = await fetch(`${API_BASE_URL}/mcp/status`);
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            return { code: res.status, msg: `Server returned ${res.status}: ${text}`, data: { running: false } } as ApiResponse<McpStatus>;
        }
        const data = await res.json();
        return { code: 0, msg: 'ok', data } as ApiResponse<McpStatus>;
    } catch (e: any) {
        console.warn('getMcpStatus error', e);
        return { code: -1, msg: String(e?.message ?? e), data: { running: false } } as ApiResponse<McpStatus>;
    }
};

export const startMcpServer = async (): Promise<ApiResponse<{ pid?: number }>> => {
    try {
        const res = await fetch(`${API_BASE_URL}/mcp/start`, { method: 'POST' });
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            return { code: res.status, msg: `Server returned ${res.status}: ${text}`, data: {} } as ApiResponse<{ pid?: number }>;
        }
        const data = await res.json();
        return { code: 0, msg: 'ok', data } as ApiResponse<{ pid?: number }>;
    } catch (e: any) {
        console.warn('startMcpServer error', e);
        return { code: -1, msg: String(e?.message ?? e), data: {} } as ApiResponse<{ pid?: number }>;
    }
};

export const stopMcpServer = async (): Promise<ApiResponse<{ pid?: number }>> => {
    try {
        const res = await fetch(`${API_BASE_URL}/mcp/stop`, { method: 'POST' });
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            return { code: res.status, msg: `Server returned ${res.status}: ${text}`, data: {} } as ApiResponse<{ pid?: number }>;
        }
        const data = await res.json();
        return { code: 0, msg: 'ok', data } as ApiResponse<{ pid?: number }>;
    } catch (e: any) {
        console.warn('stopMcpServer error', e);
        return { code: -1, msg: String(e?.message ?? e), data: {} } as ApiResponse<{ pid?: number }>;
    }
};

export const streamMcpLogs = (onMessage: (line: string) => void) => {
    const es = new EventSource(`${API_BASE_URL}/mcp/logs/stream`);
    es.onmessage = (e) => {
        if (e.data) onMessage(e.data);
    };
    es.onerror = (err) => {
        console.error('EventSource error', err);
    };
    return es;
};

export const getMcpLogs = async (): Promise<ApiResponse<{ logs: string }>> => {
    try {
        const res = await fetch(`${API_BASE_URL}/mcp/logs`);
        if (!res.ok) {
            const text = await res.text().catch(() => '');
            return { code: res.status, msg: `Server returned ${res.status}: ${text}`, data: { logs: '' } } as ApiResponse<{ logs: string }>;
        }
        const data = await res.json();
        return { code: 0, msg: 'ok', data } as ApiResponse<{ logs: string }>;
    } catch (e: any) {
        console.warn('getMcpLogs error', e);
        return { code: -1, msg: String(e?.message ?? e), data: { logs: '' } } as ApiResponse<{ logs: string }>;
    }
};
