import { API_BASE_URL } from './config';

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

interface RecentFilesResponse {
  recent_files: RecentFile[];
}

/**
 * 获取仪表盘统计数据
 */
export const getDashboardStats = async (): Promise<DashboardStats> => {
  let stats: any = null;
  try {
    const response = await fetch(`${API_BASE_URL}/dashboard/stats`);
    if (!response.ok) {
      throw new Error(`${response.status} ${response.statusText}`);
    }
    stats = await response.json();
  } catch (err) {
    // log more details to help debugging (network/CORS/backend down)
    console.error('getDashboardStats failed fetching', `${API_BASE_URL}/dashboard/stats`, err);
    // return a safe default so UI can still render
    return {
      total_files: 0,
      completed_files: 0,
      pending_files: 0,
      completion_rate: 0,
      total_documents: 0,
      mcp_calls: 0,
    };
  }

  // Fetch MCP call count from the new endpoint and merge into stats.
  try {
    const callsResp = await fetch(`${API_BASE_URL}/mcp/calls`);
    if (callsResp.ok) {
      const callsJson = await callsResp.json();
      stats.mcp_calls = callsJson.count ?? stats.mcp_calls ?? 0;
    } else {
      console.warn('getDashboardStats: /mcp/calls returned', callsResp.status, callsResp.statusText);
    }
  } catch (e) {
    console.warn('getDashboardStats: failed to fetch /mcp/calls', e);
  }

  return stats;
};

/**
 * 获取 MCP 调用次数（可选按分钟范围筛选）
 */
export const getMcpCallCount = async (minutes?: number, tool?: string): Promise<number> => {
  const params = new URLSearchParams();
  if (minutes !== undefined) params.set('minutes', String(minutes));
  if (tool) params.set('tool', tool);

  try {
    const response = await fetch(`${API_BASE_URL}/mcp/calls?${params.toString()}`);
    if (!response.ok) {
      console.error('getMcpCallCount failed:', response.status, response.statusText);
      return 0;
    }
    const data = await response.json();
    return data.count ?? 0;
  } catch (e) {
    console.error('getMcpCallCount error fetching', `${API_BASE_URL}/mcp/calls?${params.toString()}`, e);
    return 0;
  }
};

/**
 * 获取最近上传的文件
 */
export const getRecentFiles = async (limit: number = 5): Promise<RecentFilesResponse> => {
  try {
    const url = `${API_BASE_URL}/dashboard/recent-files?limit=${limit}`;
    const response = await fetch(url);
    if (!response.ok) {
      console.error('getRecentFiles failed:', response.status, response.statusText, url);
      return { recent_files: [] };
    }
    return await response.json();
  } catch (err) {
    console.error('getRecentFiles network error', `${API_BASE_URL}/dashboard/recent-files?limit=${limit}`, err);
    return { recent_files: [] };
  }
};