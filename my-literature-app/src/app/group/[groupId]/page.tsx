'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAuth } from '@/context/AuthContext';
import ProtectedRoute from '@/components/ProtectedRoute';
import api from '@/lib/api';
import { toast } from 'sonner';
import { BsSearch, BsDownload, BsEye, BsTrash, BsPeople, BsFiles, BsArrowLeft } from "react-icons/bs";

// 接口定义
interface GroupInfo {
  id: string;
  name: string;
  institution: string;
  description: string;
  research_area: string;
}

interface GroupMember {
  id: string;
  username: string;
  phone_number: string;
}

interface Literature {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  upload_time: string;
  uploader_name: string;
}

export default function GroupPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const groupId = params.groupId as string;

  // 状态管理
  const [groupInfo, setGroupInfo] = useState<GroupInfo | null>(null);
  const [groupMembers, setGroupMembers] = useState<GroupMember[]>([]);
  const [literature, setLiterature] = useState<Literature[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState<'literature' | 'members'>('literature');

  // 获取课题组信息
  const fetchGroupInfo = async () => {
    try {
      const response = await api.get(`/groups/${groupId}/info`);
      setGroupInfo(response.data);
    } catch (error) {
      console.error('获取课题组信息失败:', error);
      toast.error('获取课题组信息失败');
    }
  };

  // 获取课题组成员
  const fetchGroupMembers = async () => {
    try {
      const response = await api.get(`/groups/${groupId}/members`);
      setGroupMembers(response.data.members);
    } catch (error) {
      console.error('获取课题组成员失败:', error);
      toast.error('获取课题组成员失败');
    }
  };

  // 获取课题组文献
  const fetchGroupLiterature = async () => {
    try {
      const response = await api.get(`/literature/public/${groupId}`);
      setLiterature(response.data.literature);
    } catch (error) {
      console.error('获取课题组文献失败:', error);
      toast.error('获取课题组文献失败');
    }
  };

  // 页面初始化
  useEffect(() => {
    if (!isAuthenticated) {
      router.replace('/login');
      return;
    }

    if (groupId) {
      Promise.all([
        fetchGroupInfo(),
        fetchGroupMembers(),
        fetchGroupLiterature()
      ]).finally(() => {
        setLoading(false);
      });
    }
  }, [groupId, isAuthenticated, router]);

  // 文献搜索过滤
  const filteredLiterature = literature.filter(item =>
    item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.uploader_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // 文件大小格式化
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 下载文献
  const handleDownload = async (literatureId: string, filename: string) => {
    try {
      toast.loading('正在准备下载...');
      
      // 使用axios发起带认证的请求
      const response = await api.get(`/literature/download/${literatureId}`, {
        responseType: 'blob' // 重要：指定响应类型为blob
      });
      
      // 创建blob URL
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      
      // 创建下载链接
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      
      // 清理
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('下载成功');
    } catch (error: any) {
      console.error('下载失败:', error);
      toast.error('下载失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 查看文献
  const handleView = async (literatureId: string) => {
    try {
      toast.loading('正在打开文献...');
      
      // 使用axios发起带认证的请求
      const response = await api.get(`/literature/view/file/${literatureId}`, {
        responseType: 'blob' // 重要：指定响应类型为blob
      });
      
      // 创建blob URL
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      
      // 在新窗口中打开
      const newWindow = window.open(url, '_blank');
      if (!newWindow) {
        toast.error('请允许弹窗以查看文献');
        return;
      }
      
      toast.success('文献已打开');
      
      // 延迟清理URL（给浏览器时间加载文件）
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
      }, 1000);
    } catch (error: any) {
      console.error('查看失败:', error);
      toast.error('查看失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  if (!isAuthenticated || loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (!groupInfo) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-600 mb-2">课题组不存在</h2>
          <Button onClick={() => router.push('/home')}>返回主页</Button>
        </div>
      </div>
    );
  }

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-gray-50">
        {/* 顶部导航 */}
        <header className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => router.push('/home')}
                  className="flex items-center space-x-2"
                >
                  <BsArrowLeft className="w-4 h-4" />
                  <span>返回主页</span>
                </Button>
                <div className="h-6 w-px bg-gray-300" />
                <h1 className="text-2xl font-bold text-gray-900">{groupInfo.name}</h1>
                <Badge variant="secondary">{groupInfo.research_area}</Badge>
              </div>
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-500">{groupInfo.institution}</span>
              </div>
            </div>
          </div>
        </header>

        {/* 主要内容 */}
        <div className="max-w-7xl mx-auto px-4 py-6">
          {/* 课题组描述 */}
          {groupInfo.description && (
            <Card className="mb-6">
              <CardContent className="p-4">
                <p className="text-gray-700">{groupInfo.description}</p>
              </CardContent>
            </Card>
          )}

          {/* 标签页切换 */}
          <div className="flex space-x-1 mb-6">
            <Button
              variant={activeTab === 'literature' ? 'default' : 'ghost'}
              onClick={() => setActiveTab('literature')}
              className="flex items-center space-x-2"
            >
              <BsFiles className="w-4 h-4" />
              <span>文献库 ({literature.length})</span>
            </Button>
            <Button
              variant={activeTab === 'members' ? 'default' : 'ghost'}
              onClick={() => setActiveTab('members')}
              className="flex items-center space-x-2"
            >
              <BsPeople className="w-4 h-4" />
              <span>成员 ({groupMembers.length})</span>
            </Button>
          </div>

          {/* 文献库标签页 */}
          {activeTab === 'literature' && (
            <div className="space-y-4">
              {/* 搜索栏 */}
              <div className="flex items-center space-x-4">
                <div className="relative flex-1 max-w-md">
                  <Input
                    type="text"
                    placeholder="搜索文献..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                  <BsSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                </div>
                <Button onClick={() => router.push('/main')} variant="outline">
                  上传文献
                </Button>
              </div>

              {/* 文献列表 */}
              <Card>
                <CardHeader>
                  <CardTitle>文献列表</CardTitle>
                </CardHeader>
                <CardContent>
                  {filteredLiterature.length === 0 ? (
                    <div className="text-center py-8">
                      <BsFiles className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                      <p className="text-gray-500">
                        {searchQuery ? '没有找到匹配的文献' : '暂无文献，点击上传添加第一篇文献'}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {filteredLiterature.map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50"
                        >
                          <div className="flex-1">
                            <h3 className="font-medium text-gray-900 mb-1">{item.title}</h3>
                            <div className="flex items-center space-x-4 text-sm text-gray-500">
                              <span>{item.filename}</span>
                              <span>{formatFileSize(item.file_size)}</span>
                              <span>上传者: {item.uploader_name}</span>
                              <span>{new Date(item.upload_time).toLocaleDateString()}</span>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleView(item.id)}
                              title="查看文献"
                            >
                              <BsEye className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => handleDownload(item.id, item.filename)}
                              title="下载文献"
                            >
                              <BsDownload className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* 成员标签页 */}
          {activeTab === 'members' && (
            <Card>
              <CardHeader>
                <CardTitle>课题组成员</CardTitle>
              </CardHeader>
              <CardContent>
                {groupMembers.length === 0 ? (
                  <div className="text-center py-8">
                    <BsPeople className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p className="text-gray-500">暂无成员信息</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {groupMembers.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center space-x-3 p-4 border rounded-lg"
                      >
                        <Avatar>
                          <AvatarFallback>
                            {member.username.charAt(0).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <h4 className="font-medium text-gray-900">{member.username}</h4>
                          <p className="text-sm text-gray-500">{member.phone_number}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
} 