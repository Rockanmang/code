# AI文献管理系统

基于FastAPI和Google Gemini的智能文献管理与RAG问答系统。

## 🚀 核心功能

- **📚 文献管理**：上传、组织和共享学术文献
- **👥 研究小组**：创建和管理研究团队，控制文献访问权限
- **🤖 AI问答**：基于RAG技术的智能文献问答
- **🔍 语义检索**：向量化存储和相似度检索
- **💬 协作功能**：文献批注和讨论

## 🛠️ 技术栈

- **后端**：FastAPI + SQLAlchemy + SQLite
- **AI**：Google Gemini API + ChromaDB
- **文本处理**：自研分块算法 + 向量嵌入

## ⚡ 快速开始

### 安装与配置

```bash
# 克隆项目
git clone https://github.com/Rockanmang/code.git
cd ai_code

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env_example.txt .env
# 编辑.env文件，添加API密钥
```

### 运行系统

```bash
python run.py
# 访问 http://localhost:8001
```

## 📂 项目结构

```
ai_code/
├── app/              # 应用核心代码
│   ├── models/      # 数据模型
│   ├── utils/       # 工具模块
│   └── main.py      # 应用入口
├── test/            # 测试文件
├── uploads/         # 上传文件存储
├── vector_db/       # 向量数据库
└── requirements.txt # 依赖包
```

## 📊 主要特性

- **文献解析**：自动提取标题、作者、摘要
- **智能标签**：自动生成文献标签
- **语义搜索**：基于内容的相似度搜索
- **RAG问答**：针对文献内容的精准回答
- **引用追踪**：自动标注答案来源
- **多轮对话**：支持连续提问和上下文理解

## 🧪 测试

```bash
# 运行基础测试
python test/test_ai_basic.py

# 运行综合测试
python test/test_comprehensive.py
```

## 📝 项目状态

- ✅ 基础文献管理
- ✅ 用户认证和权限
- ✅ 文本提取和向量化
- 🚧 RAG问答系统
- 🚧 协作批注功能
- 📋 知识图谱集成（计划中）