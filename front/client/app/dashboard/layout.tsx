"use client";

import {
    DashboardOutlined,
    DatabaseOutlined,
    FileTextOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined
} from '@ant-design/icons';
import { Button, Layout, Menu, theme } from 'antd';
import Image from 'next/image';
import { usePathname, useRouter } from 'next/navigation';
import React, { useState } from 'react';

const { Header, Sider, Content } = Layout;

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [collapsed, setCollapsed] = useState(false);
    const {
        token: { colorBgContainer, borderRadiusLG },
    } = theme.useToken();
    const router = useRouter();
    const pathname = usePathname();

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sider trigger={null} collapsible collapsed={collapsed} theme="light" className="border-r border-gray-200">
                <div className="demo-logo-vertical h-16 flex items-center justify-center border-b border-gray-100 transition-all duration-200">
                    <Image src={"/logo.png"} alt="Logo" width={40} height={40} className='' />
                    <b className={`transition-all duration-200 ${collapsed ? 'hidden' : 'text-xl ml-4'}`}>RAG_MCP</b>
                </div>
                <Menu
                    theme="light"
                    mode="inline"
                    defaultSelectedKeys={[pathname]}
                    selectedKeys={[pathname]}
                    onClick={({ key }) => router.push(key)}
                    className="border-none"
                    items={[
                        {
                            key: '/dashboard',
                            icon: <DashboardOutlined />,
                            label: '概览',
                        },
                        {
                            key: '/dashboard/files',
                            icon: <FileTextOutlined />,
                            label: '文件管理',
                        },
                        {
                            key: '/dashboard/knowledge',
                            icon: <DatabaseOutlined />,
                            label: '知识库',
                        },
                    ]}
                />
            </Sider>
            <Layout>
                <Header style={{ padding: 0, background: colorBgContainer }} className="flex items-center justify-between px-4 border-b border-gray-200">
                    <Button
                        type="text"
                        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                        onClick={() => setCollapsed(!collapsed)}
                        style={{
                            fontSize: '16px',
                            width: 64,
                            height: 64,
                        }}
                    />
                    <div className="mr-4">
                        {/* User profile or other header items can go here */}
                        <span>Admin</span>
                    </div>
                </Header>
                <Content
                    style={{
                        margin: '24px 16px',
                        padding: 24,
                        minHeight: 280,
                        background: colorBgContainer,
                        borderRadius: borderRadiusLG,
                    }}
                >
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
