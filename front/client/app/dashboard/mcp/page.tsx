"use client";

import { SolarRefreshOutline } from '@/components/icons';
import { getMcpLogs, getMcpStatus, startMcpServer, stopMcpServer, streamMcpLogs } from '@/services/mcp';
import { ClearOutlined, DownloadOutlined, PoweroffOutlined, StopOutlined } from '@ant-design/icons';
import { Alert, Badge, Button, Card, Col, Divider, Row, Space, Switch, Tag, Tooltip, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';

const { Title, Text } = Typography;

export default function McpManagementPage() {
    const [status, setStatus] = useState<{ running: boolean; pid?: number | null; uptime_seconds?: number | null }>({ running: false, pid: null, uptime_seconds: null });
    const [error, setError] = useState<string | null>(null);
    const [logs, setLogs] = useState<string[]>([]);
    const [loadingStart, setLoadingStart] = useState(false);
    const [loadingStop, setLoadingStop] = useState(false);
    const [autoScroll, setAutoScroll] = useState<boolean>(true);
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
    const [refreshing, setRefreshing] = useState(false);
    const esRef = useRef<EventSource | null>(null);
    const pollingRef = useRef<number | null>(null);
    const connectingTimerRef = useRef<number | null>(null);
    const [logsConnecting, setLogsConnecting] = useState(false);
    const [logsConnected, setLogsConnected] = useState(false);
    const [logSseAttempts, setLogSseAttempts] = useState(0);
    const [isPolling, setIsPolling] = useState(false);
    const unmountedRef = useRef(false);
    const logContainerRef = useRef<HTMLDivElement | null>(null);
    const connectToLogsRef = useRef<(attempt?: number) => void>(() => { });

    useEffect(() => {
        if (!autoScroll || !logContainerRef.current) return;
        const el = logContainerRef.current;
        // Scroll to bottom when logs update
        el.scrollTop = el.scrollHeight;
    }, [logs, autoScroll]);

    function formatUptime(seconds: number | null | undefined) {
        if (seconds === null || seconds === undefined) return '--';
        const s = Number(seconds);
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = s % 60;
        return `${h}h ${m}m ${sec}s`;
    }

    useEffect(() => {
        const fetchStatus = async () => {
            const res = await getMcpStatus();
            setStatus(res.data);
            setLastUpdated(new Date());
            if (res.code !== 0) {
                setError(res.msg);
            } else {
                setError(null);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const startPolling = () => {
        if (pollingRef.current) return;
        // use window.setInterval to get a number in browser
        pollingRef.current = window.setInterval(async () => {
            try {
                const initial = await getMcpLogs();
                if (initial.data && initial.data.logs) {
                    const lines = initial.data.logs.split('\n').filter(Boolean);
                    setLogs(lines.slice(-200));
                }
            } catch (e) {
                console.warn('Polling failed to fetch logs', e);
            }
        }, 3000);
        setIsPolling(true);
    };

    const stopPolling = () => {
        if (pollingRef.current) {
            window.clearInterval(pollingRef.current);
            pollingRef.current = null;
        }
        setIsPolling(false);
    };

    const connectToLogs = useCallback(async (attempt = 0) => {
        if (unmountedRef.current) return;
        // close existing es if any
        if (esRef.current) {
            try { esRef.current.close(); } catch (_) { }
            esRef.current = null;
        }
        setLogsConnecting(true);
        setLogsConnected(false);
        setLogSseAttempts(attempt);
        setError(null);

        // fetch initial logs
        try {
            const initial = await getMcpLogs();
            if (initial.data && initial.data.logs) {
                const lines = initial.data.logs.split('\n').filter(Boolean);
                setLogs(lines.slice(-200));
            }
        } catch (e) {
            console.warn('Unable to fetch logs initially', e);
        }

        try {
            const es = streamMcpLogs((line: string) => {
                setLogs((prev) => {
                    const next = prev.slice(-199).concat([line]);
                    return next;
                });
            });
            es.onopen = () => {
                setLogsConnected(true);
                setLogsConnecting(false);
                setLogSseAttempts(0);
                // clear connecting timeout
                if (connectingTimerRef.current) {
                    window.clearTimeout(connectingTimerRef.current);
                    connectingTimerRef.current = null;
                }
                stopPolling();
                // clear error on successful connection
                setError(null);
            };
            es.onerror = (err) => {
                console.warn('EventSource error', err);
                setLogsConnected(false);
                setLogsConnecting(false);
                if (connectingTimerRef.current) {
                    window.clearTimeout(connectingTimerRef.current);
                    connectingTimerRef.current = null;
                }
                setError('无法打开 SSE 连接以接收日志');
                try { es.close(); } catch (_) { }
                // exponential backoff and retry
                const nextAttempt = attempt + 1;
                setLogSseAttempts(nextAttempt);
                if (nextAttempt >= 5) {
                    // fallback to polling
                    setError('SSE 连接失败，已切换到轮询以确保日志更新');
                    startPolling();
                    return;
                }
                const backoff = Math.min(2000 * Math.pow(2, nextAttempt - 1), 30000);
                setTimeout(() => connectToLogsRef.current(nextAttempt), backoff);
            };
            esRef.current = es;
            // set a safety timeout: if not open within 8s, fallback to polling
            if (connectingTimerRef.current) {
                window.clearTimeout(connectingTimerRef.current);
                connectingTimerRef.current = null;
            }
            connectingTimerRef.current = window.setTimeout(() => {
                if (!esRef.current) return;
                console.warn('SSE connection timeout, falling back to polling');
                try { esRef.current.close(); } catch (_) { }
                esRef.current = null;
                setLogsConnecting(false);
                setError('SSE连接超时，已切换到轮询');
                startPolling();
            }, 8000);
        } catch (err) {
            console.warn('Failed to create EventSource', err);
            setLogsConnected(false);
            setLogsConnecting(false);
            setError('无法打开 SSE 连接以接收日志');
            // fallback to polling
            startPolling();
        }
    }, []);

    useEffect(() => {
        unmountedRef.current = false;
        const run = async () => { await connectToLogs(); };
        run();
        return () => {
            unmountedRef.current = true;
            try {
                if (esRef.current) {
                    esRef.current.close();
                    esRef.current = null;
                }
            } catch (_) { }
            if (pollingRef.current) {
                window.clearInterval(pollingRef.current);
                pollingRef.current = null;
            }
            if (connectingTimerRef.current) {
                window.clearTimeout(connectingTimerRef.current);
                connectingTimerRef.current = null;
            }
        };
    }, [connectToLogs]);

    useEffect(() => {
        connectToLogsRef.current = connectToLogs;
    }, [connectToLogs]);

    const onStart = async () => {
        setLoadingStart(true);
        try {
            const res = await startMcpServer();
            if (res.code !== 0) {
                setError(res.msg);
            } else {
                setError(null);
            }
            // status will update in poll
            // refresh immediately
            const statusRes = await getMcpStatus();
            setStatus(statusRes.data);
            setLastUpdated(new Date());
        } catch (e) {
            console.error(e);
        }
        setLoadingStart(false);
    };

    const onStop = async () => {
        setLoadingStop(true);
        try {
            const res = await stopMcpServer();
            if (res.code !== 0) {
                setError(res.msg);
            } else {
                setError(null);
            }
            // refresh immediately
            const statusRes = await getMcpStatus();
            setStatus(statusRes.data);
            setLastUpdated(new Date());
        } catch (e) {
            console.error(e);
        }
        setLoadingStop(false);
    };

    // clear logs
    const onClearLogs = () => setLogs([]);

    // download logs
    const onDownloadLogs = () => {
        const blob = new Blob([logs.join('\n')], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `mcp_logs_${new Date().toISOString().replace(/[:.]/g, '-')}.log`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const onRefreshStatus = async () => {
        setRefreshing(true);
        try {
            const res = await getMcpStatus();
            setStatus(res.data);
            setLastUpdated(new Date());
            if (res.code !== 0) {
                setError(res.msg);
            } else {
                setError(null);
            }
        } catch (e) {
            console.error(e);
            setError('无法刷新状态');
        }
        setRefreshing(false);
    };

    return (
        <div className="p-4">
            <Title level={2} className="mb-6 text-gray-800">MCP 管理</Title>

            {error && (
                <Alert
                    message="错误"
                    description={error}
                    type="error"
                    showIcon
                    closable
                    onClose={() => setError(null)}
                    className="mb-6"
                />
            )}

            <Row gutter={[16, 16]}>
                {/* 状态卡片 */}
                <Col xs={24} lg={8}>
                    <Card title="服务状态" className="h-full">
                        <div className="flex flex-col h-full">
                            <div className="flex-grow">
                                <div className="flex items-center justify-between mb-4">
                                    <Text strong>当前状态:</Text>
                                    <Badge status={status.running ? 'success' : 'default'} text={status.running ? '运行中' : '已停止'} />
                                </div>

                                {status.running ? (
                                    <>
                                        <div className="mb-2">
                                            <Text type="secondary">进程ID:</Text>
                                            <Tag color="green" className="ml-2">{status.pid}</Tag>
                                        </div>
                                        <div className="mb-2">
                                            <Text type="secondary">运行时间:</Text>
                                            <Text className="ml-2">{formatUptime(status.uptime_seconds)}</Text>
                                        </div>
                                    </>
                                ) : (
                                    <Text type="secondary">服务当前未运行</Text>
                                )}

                                <div className="mt-4">
                                    <Text type="secondary">最后更新:</Text>
                                    <Text className="ml-2">{lastUpdated ? lastUpdated.toLocaleTimeString() : '--'}</Text>
                                </div>
                            </div>

                            <div className="flex space-x-2 mt-4">
                                <Tooltip title="刷新状态">
                                    <Button
                                        icon={<SolarRefreshOutline />}
                                        loading={refreshing}
                                        onClick={onRefreshStatus}
                                    />
                                </Tooltip>

                                {!status.running ? (
                                    <Button
                                        type="primary"
                                        icon={<PoweroffOutlined />}
                                        loading={loadingStart}
                                        onClick={onStart}
                                        className="flex-grow"
                                    >
                                        启动服务
                                    </Button>
                                ) : (
                                    <Button
                                        danger
                                        icon={<StopOutlined />}
                                        loading={loadingStop}
                                        onClick={onStop}
                                        className="flex-grow"
                                    >
                                        停止服务
                                    </Button>
                                )}
                            </div>
                        </div>
                    </Card>
                </Col>

                {/* 连接说明卡片 */}
                <Col xs={24} lg={16}>
                    <Card title="客户端连接说明" className="h-full">
                        <div className="h-full flex flex-col">
                            <div className="flex-grow">
                                <Text type="secondary">
                                    当 MCP 服务已启动时，LLM 客户端可以直接通过 MCP 协议调用已注册的工具。
                                </Text>

                                <Divider plain>连接步骤</Divider>
                                <ol className="list-decimal list-inside space-y-2 mb-4">
                                    <li>确保后端 MCP 已启动（状态显示为运行中）</li>
                                    <li>在你的应用中配置 MCP 客户端连接参数</li>
                                    <li>使用支持 MCP 协议的 LLM 客户端库进行连接</li>
                                </ol>

                                <Divider plain>JSON 配置示例 (SSE / Streamable HTTP)</Divider>
                                <div className="bg-gray-900 text-white rounded-md p-3 text-xs overflow-auto">
                                    <pre className="whitespace-pre-wrap"><code>{`// SSE 示例
{
    "servers": {
        "rag-mcp": {
            "type": "sse",
            "url": "http://localhost:8000/api/v1/mcp/sse"
        }
    },
    "inputs": []
}

// Streamable HTTP 示例 (推荐)
{
    "servers": {
        "rag-mcp": {
            "type": "streamable_http",
            "url": "http://127.0.0.1:18080/jsonrpc"
        }
    },
    "inputs": []
}`}</code></pre>
                                </div>
                                <div className="mt-3 text-xs text-gray-500">
                                    说明: 上面给出了使用 SSE (日志/事件) 和 Streamable HTTP（JSON-RPC over HTTP）两种连接方式的配置示例。Streamable HTTP 是更通用、推荐的方式，适用于 MCP 协议客户端。请根据你的客户端选择适当的配置。
                                </div>
                            </div>

                            <div className="mt-4 text-xs text-gray-500">
                                说明: 上例使用仓库内的 `mcp.simple_mcp_server.MCPServer` 封装来方便本地调用；
                                在生产中，你的 LLM 客户端可以通过相同的 MCP 协议构造 JSON-RPC 请求并与 MCP 服务器通信（stdio、socket 或 Streamable HTTP，视服务器启动方式而定）。
                            </div>
                        </div>
                    </Card>
                </Col>

                {/* 日志面板 */}
                <Col span={24}>
                    <Card
                        title="MCP 日志"
                        extra={
                            <Space>
                                <Tag color={logsConnected ? 'green' : logsConnecting ? 'gold' : isPolling ? 'blue' : 'red'}>
                                    {logsConnected ? '实时 (SSE)' : logsConnecting ? '连接中...' : isPolling ? '轮询' : '已断开'}
                                </Tag>
                                <Button size="small" onClick={async () => { setError(null); setLogSseAttempts(0); stopPolling(); await connectToLogs(0); }}>
                                    重连
                                </Button>
                                <Tooltip title="自动滚动">
                                    <Switch checked={autoScroll} onChange={(v) => setAutoScroll(v)} size="small" />
                                </Tooltip>
                                <Button size="small" icon={<ClearOutlined />} onClick={onClearLogs}>
                                    清空
                                </Button>
                                <Button size="small" icon={<DownloadOutlined />} onClick={onDownloadLogs}>
                                    下载
                                </Button>
                            </Space>
                        }
                    >
                        <div ref={logContainerRef} className="h-96 overflow-auto bg-black text-white p-3 font-mono rounded-md">
                            {logs.length === 0 && <div className="text-gray-400">暂无日志信息</div>}
                            {logs.map((line, idx) => (
                                <div key={idx} className="leading-tight text-xs wrap-break-word">
                                    <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {line}
                                </div>
                            ))}
                        </div>
                    </Card>
                </Col>
            </Row>
        </div>
    );
}