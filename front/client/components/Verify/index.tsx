"use client"

import { Button, Form, Input } from "antd";
import Image from "next/image";
import AnimatedShader from "../ShaderViewer";

interface VerifyProps { }

const Verify: React.FC<VerifyProps> = (props) => {
    return (
        <div className="relative w-full h-full overflow-hidden">
            {/* Background Shader */}
            <div className="absolute inset-0 z-0">
                <AnimatedShader />
            </div>

            {/* Login Card */}
            <section className="relative z-10 w-full h-full flex flex-col items-center justify-center px-4">
                <div className="bg-white/90 dark:bg-gray-900/90 backdrop-blur-md p-8 rounded-2xl shadow-2xl w-full max-w-md border border-white/20">
                    <div className="flex items-center justify-center mb-8">
                        <Image src={"/logo.png"} alt="Logo" width={48} height={48} className="rounded-lg" />
                        <b className="text-3xl font-bold ml-4 text-gray-800 dark:text-white">RAG_MCP</b>
                    </div>

                    <Form
                        layout="vertical"
                        size="large"
                        className="w-full"
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

                        <Form.Item className="mb-0">
                            <Button type="primary" htmlType="submit" block className="h-10 text-lg font-medium">
                                登录
                            </Button>
                        </Form.Item>
                    </Form>
                </div>
            </section>
        </div>
    );
};

export default Verify;
