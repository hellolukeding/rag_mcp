"use client"

import { login, startImageCaptcha, verifyImageCaptcha } from '@/services/auth';
import { Alert, Button, Form, Input } from "antd";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import AnimatedShader from "../ShaderViewer";
import { TablerRefresh } from '../icons';

interface VerifyProps { }

type EventRecord = { type: 'move' | 'click'; x: number; y: number; t: number };

const Verify: React.FC<VerifyProps> = (props) => {
    const router = useRouter();
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [expiresAt, setExpiresAt] = useState<string | null>(null);
    const eventsRef = useRef<EventRecord[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [verified, setVerified] = useState<boolean | null>(null);
    const [imageData, setImageData] = useState<string | null>(null);
    const [form] = Form.useForm();

    useEffect(() => {
        // load image captcha on mount
        (async () => {
            try {
                const resp = await startImageCaptcha();
                setSessionId(resp.session_id);
                setExpiresAt(resp.expires_at ?? null);
                setImageData(resp.image ?? null);
            } catch (e) {
                console.error('startImageCaptcha failed', e);
                setError('无法初始化图片验证码，登录体验可能受影响');
            }
        })();
    }, []);

    const onFinish = async (values: any) => {
        setError(null);
        setLoading(true);
        try {
            if (!sessionId) throw new Error('未获取到验证码会话');

            // verify image captcha first
            const answer = values.captcha_answer;
            if (!answer) throw new Error('请输入图片验证码答案');
            const sub = await verifyImageCaptcha(sessionId, answer);
            setVerified(!!sub.verified);
            if (!sub.verified) {
                setError('图片验证码未通过，请重试');
                // clear answer and reload a fresh captcha
                try {
                    form.resetFields(['captcha_answer']);
                } catch (e) {
                    // ignore
                }
                try {
                    const resp = await startImageCaptcha();
                    setSessionId(resp.session_id);
                    setExpiresAt(resp.expires_at ?? null);
                    setImageData(resp.image ?? null);
                } catch (e) {
                    console.error('reload captcha failed', e);
                }
                setLoading(false);
                return;
            }

            const tokenResp = await login(values.username, values.password, sessionId);
            if (typeof window !== 'undefined') localStorage.setItem('access_token', tokenResp.access_token);
            router.push('/dashboard');
        } catch (err: any) {
            const msg = err instanceof Error ? err.message : String(err);
            setError(msg || '登录失败');
            // on any login failure, clear captcha input and reload a new captcha
            try {
                form.resetFields(['captcha_answer']);
            } catch (e) { }
            try {
                const resp = await startImageCaptcha();
                setSessionId(resp.session_id);
                setExpiresAt(resp.expires_at ?? null);
                setImageData(resp.image ?? null);
            } catch (e) {
                console.error('reload captcha failed', e);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="relative w-full h-full overflow-hidden">
            {/* Background Shader */}
            <div className="absolute inset-0 z-0">
                <AnimatedShader />
            </div>

            {/* Login Card */}
            <section className="relative z-10 w-full h-full flex flex-col items-center justify-center px-4">
                <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md p-8 rounded-2xl shadow-2xl w-full max-w-md border border-white/20">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center">
                            <Image src={'/logo.png'} alt="Logo" width={48} height={48} className="rounded-lg" />
                            <b className="text-3xl font-bold ml-4 text-gray-800 dark:text-white">RAG_MCP</b>
                        </div>
                        <Link href="/" className="text-xs px-3 py-1 bg-yellow-100 text-yellow-900 rounded-md">限时试用 · 商业版</Link>

                    </div>

                    {error && <div className="mb-4"><Alert title={error} type="error" showIcon /></div>}


                    <Form
                        form={form}
                        layout="vertical"
                        size="large"
                        className="w-full"
                        onFinish={onFinish}
                    >
                        <Form.Item
                            name="username"
                            label={<span className="text-gray-700 dark:text-gray-300">用户名</span>}
                            rules={[{ required: true, message: '请输入用户名' }]}
                        >
                            <Input placeholder="请输入用户名" />
                        </Form.Item>

                        <Form.Item
                            name="password"
                            label={<span className="text-gray-700 dark:text-gray-300">密码</span>}
                            rules={[{ required: true, message: '请输入密码' }]}
                        >
                            <Input.Password placeholder="请输入密码" />
                        </Form.Item>

                        <Form.Item label={<span className="text-gray-700 dark:text-gray-300">图片验证码</span>}>
                            <div className="flex items-center gap-3">
                                {imageData ? (
                                    // eslint-disable-next-line @next/next/no-img-element
                                    <img src={imageData} alt="captcha" className="h-12 rounded-md border" />
                                ) : (
                                    <div className="h-16 w-40 bg-gray-100 dark:bg-gray-700 rounded-md flex items-center justify-center text-xs">加载中...</div>
                                )}
                                <div className="flex-1">
                                    <Form.Item name="captcha_answer" noStyle rules={[{ required: true, message: '请输入验证码' }]}>
                                        <Input placeholder="输入图片中字符" suffix={<Button size="small" type="link" icon={<TablerRefresh />} onClick={async () => {
                                            setError(null);
                                            try {
                                                const resp = await startImageCaptcha();
                                                setSessionId(resp.session_id);
                                                setExpiresAt(resp.expires_at ?? null);
                                                setImageData(resp.image ?? null);
                                            } catch (e) {
                                                console.error('reload captcha failed', e);
                                                setError('重载验证码失败');
                                            }
                                        }} />} />
                                    </Form.Item>

                                </div>
                            </div>

                        </Form.Item>

                        <Form.Item className="mb-0">
                            <Button type="primary" htmlType="submit" block className="h-10 text-lg font-medium" loading={loading}>
                                登录
                            </Button>
                        </Form.Item>
                    </Form>

                    {/* Simple ad / promotional content below form */}
                    <div className="mt-6 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-100 dark:border-gray-700">
                        <div className="text-sm font-medium">产品推荐</div>
                        <div className="text-xs text-gray-600 dark:text-gray-300">增强的私有检索、企业级向量处理与 SSO 集成。联系我们获取企业版优惠。</div>
                        <div className="mt-2">
                            <a className="text-indigo-600" href="#">查看定价 &rarr;</a>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Verify;
