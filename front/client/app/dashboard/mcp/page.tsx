"use client";

import { SolarRefreshOutline } from '@/components/icons';
import { getMcpLogs, getMcpStatus, startMcpServer, stopMcpServer, streamMcpLogs } from '@/services/mcp';
import { ClearOutlined, DownloadOutlined, PoweroffOutlined, StopOutlined } from '@ant-design/icons';
import { Alert, Badge, Button, Card, Space, Switch, Tag, Tooltip } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';

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
        <div>
            <h2 className="text-2xl font-bold mb-6 text-gray-800">MCP 管理</h2>
            {error && (
                <Alert
                    title="错误"
                    description={error}
                    type="error"
                    showIcon
                    closable
                    onClose={() => setError(null)}
                    className="mb-4"
                />
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card>
                    <Space orientation="vertical">
                        <div className="flex items-center justify-between">
                            <div>
                                <div className="text-sm text-gray-500">MCP 状态</div>
                                <div className="mt-1 font-semibold flex items-center gap-2">
                                    <Badge dot status={status.running ? 'success' : 'default'} />
                                    {status.running ? (
                                        <div className="flex items-center gap-2">
                                            <div>Running</div>
                                            <Tag color="green">PID: {status.pid}</Tag>
                                        </div>
                                    ) : (
                                        <Tag color="red">Stopped</Tag>
                                    )}
                                </div>
                                <div className="text-xs text-gray-400 mt-1">{lastUpdated ? `上次检查: ${lastUpdated.toLocaleTimeString()}` : ''}</div>
                                {status.uptime_seconds !== undefined && status.uptime_seconds !== null && (
                                    <div className="text-xs text-gray-400">已运行: {formatUptime(status.uptime_seconds)}</div>
                                )}
                            </div>
                            <div className="space-x-2">
                                <Tooltip title="刷新状态">
                                    <Button icon={<SolarRefreshOutline />} loading={refreshing} onClick={onRefreshStatus} />
                                </Tooltip>
                                {!status.running ? (
                                    <Tooltip title="启动 MCP">
                                        <Button type="primary" icon={<PoweroffOutlined />} loading={loadingStart} onClick={onStart} disabled={status.running}>
                                            启动
                                        </Button>
                                    </Tooltip>
                                ) : (
                                    <Tooltip title="停止 MCP">
                                        <Button danger icon={<StopOutlined />} loading={loadingStop} onClick={onStop} disabled={!status.running}>
                                            停止
                                        </Button>
                                    </Tooltip>
                                )}
                            </div>
                        </div>
                    </Space>
                </Card>

                <Card title="MCP 日志" className="md:col-span-2" extra={<Space>
                    <Tag color={logsConnected ? 'green' : logsConnecting ? 'gold' : isPolling ? 'blue' : 'red'}>
                        {logsConnected ? '实时 (SSE)' : logsConnecting ? '连接中...' : isPolling ? '轮询' : '已断开'}
                    </Tag>
                    <Button size="small" onClick={async () => { setError(null); setLogSseAttempts(0); stopPolling(); await connectToLogs(0); }}>重连</Button>
                    <Tooltip title="自动滚动">
                        <Switch checked={autoScroll} onChange={(v) => setAutoScroll(v)} size="small" />
                    </Tooltip>
                    <Button size="small" icon={<ClearOutlined />} onClick={onClearLogs}>清空</Button>
                    <Button size="small" icon={<DownloadOutlined />} onClick={onDownloadLogs}>下载</Button>
                </Space>}>
                    <div ref={logContainerRef} className="h-96 overflow-auto bg-black text-white p-3 font-mono rounded-md">
                        {logs.length === 0 && <div className="text-gray-400">无日志</div>}
                        {logs.map((line, idx) => (
                            <div key={idx} className="leading-tight text-xs wrap-break-word">
                                <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span> {line}
                            </div>
                        ))}
                    </div>
                </Card>
            </div>
        </div>
    );
}
