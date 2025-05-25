# 人工智能驱动的协同文献管理系统

一个基于Python FastAPI的智能文献管理和协作平台，专为高校研究团队设计。

## 🚀 项目简介

本系统是一个集成了人工智能功能的协同文献管理平台，旨在帮助研究团队更高效地管理、分享和讨论学术文献。系统提供了智能文献解析、实时协作注释、AI问答助手等功能。

## ✨ 主要功能

### 👥 用户管理
- 用户注册与登录
- 个人资料管理
- 安全认证系统

### 🏢 研究小组管理
- 创建和管理研究小组
- 邀请码加入机制
- 小组成员管理

### 📚 文献管理
- 支持PDF和Word文档上传
- AI自动解析文档标题、作者、摘要
- 智能标签系统
- 在线文档阅读器

### 🤝 协作功能
- 实时文献注释
- @成员提及功能
- 评论和讨论系统
- 实时同步更新

### 🤖 AI助手
- 基于文献内容的智能问答
- 文献关联推荐
- 核心论点总结
- 跨文献知识关联

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代、快速的Web框架
- **SQLAlchemy** - ORM数据库操作
- **SQLite** - 轻量级数据库
- **Pydantic** - 数据验证和序列化
- **Python-Jose** - JWT令牌处理
- **Passlib** - 密码加密
- **Python-multipart** - 文件上传处理

### AI集成
- **LangChain** - AI应用开发框架
- **OpenAI API** - 大语言模型服务

## 📁 项目结构

```
ai_code/
├── app/                    # 应用主目录
│   ├── models/            # 数据模型
│   └── utils/             # 工具函数
├── test/                  # 测试文件
├── uploads/               # 文件上传目录
├── requirements.txt       # Python依赖
├── run.py                # 应用启动文件
└── literature_system.db  # SQLite数据库
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip包管理器

### 安装步骤

1. 克隆项目
```bash
git clone <repository-url>
cd ai_code
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 启动应用
```bash
python run.py
```

4. 访问应用
打开浏览器访问 `http://localhost:8000`

## 📋 API文档

启动应用后，可以访问以下地址查看API文档：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🔧 配置说明

### 环境变量
创建 `.env` 文件并配置以下变量：
```
OPENAI_API_KEY=your_openai_api_key
SECRET_KEY=your_secret_key
DATABASE_URL=sqlite:///./literature_system.db
```

## 📖 使用指南

### 用户注册
1. 访问注册页面
2. 填写用户名、手机号、密码
3. 完成注册后自动登录

### 创建研究小组
1. 登录后点击"创建课题组"
2. 填写小组信息和自定义邀请码
3. 邀请其他成员加入

### 上传文献
1. 选择私人文献库或公共文献库
2. 点击"上传"按钮
3. 选择PDF或Word文件
4. AI自动解析文档信息

### 使用AI助手
1. 点击右下角浮动球体图标
2. 输入问题或选择预设问题
3. 获得基于文献内容的智能回答

## 🤝 贡献指南

欢迎提交Issue和Pull Request来帮助改进项目。

## 📄 许可证

本项目采用MIT许可证。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件

---

**注意**: 本项目仍在开发中，部分功能可能还在完善阶段。