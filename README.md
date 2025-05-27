# AI文献管理系统 - RAG问答功能

## 🎯 项目介绍

这是一个基于FastAPI开发的智能文献管理系统，集成了先进的RAG（检索增强生成）问答功能。用户可以上传学术文献，并通过自然语言与文献进行智能对话，获得准确的答案和引用来源。

## ✨ 核心特性

### 📚 文献管理
- 支持PDF、DOCX等多种格式文献上传
- 智能文本提取和预处理
- 按研究组织管理文献权限
- 文献元数据管理和搜索

### 🤖 RAG问答系统
- **智能问答**：基于文献内容的自然语言问答
- **引用追踪**：自动标注答案来源和引用位置
- **对话记忆**：支持多轮对话，保持上下文连贯性
- **预设问题**：提供常见学术问题模板
- **质量评估**：多维度答案质量评分和置信度计算

### 🔍 向量检索
- 基于ChromaDB的高性能向量数据库
- Google Gemini Embedding模型支持
- 智能文档分块和向量化
- 语义相似度检索优化

### ⚡ 性能优化
- 多层缓存策略（Embedding、答案、文档块）
- 异步处理提升响应速度
- 智能负载均衡和熔断机制
- 内存使用优化和垃圾回收

## 🏗️ 技术架构

### 后端技术栈
- **Web框架**: FastAPI + Uvicorn
- **数据库**: SQLAlchemy + SQLite
- **AI服务**: Google Gemini API
- **向量数据库**: ChromaDB
- **缓存**: cachetools (TTL Cache)
- **文本处理**: 自研分块算法
- **异步处理**: asyncio

### 前端技术栈
- HTML5 + CSS3 + JavaScript
- Bootstrap 5响应式设计
- Ajax异步交互
- 文件拖拽上传

## 📂 项目结构

```
ai_code/
├── app/                    # 应用核心代码
│   ├── models/            # 数据模型
│   ├── routers/           # API路由
│   ├── utils/             # 工具模块
│   │   ├── embedding_service.py    # Embedding服务
│   │   ├── vector_store.py        # 向量数据库
│   │   ├── text_processor.py      # 文本处理
│   │   ├── file_processor.py      # 文件处理
│   │   ├── rag_service.py         # RAG核心服务
│   │   ├── conversation_manager.py # 对话管理
│   │   ├── prompt_builder.py      # 提示词构建
│   │   ├── answer_processor.py    # 答案处理
│   │   └── cache_manager.py       # 缓存管理
│   ├── templates/         # HTML模板
│   ├── static/           # 静态资源
│   ├── config.py         # 配置文件
│   └── main.py          # 应用入口
├── test/                 # 测试文件
├── docs/                 # 项目文档
│   ├── 第5天RAG问答系统详细实现计划.md
│   ├── RAG实施步骤清单.md
│   ├── RAG技术选型与架构决策.md
│   └── RAG快速开始指南.md
├── requirements.txt      # 依赖包
├── run.py               # 启动脚本
└── README.md           # 项目说明
```

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- Google AI Studio API密钥

### 2. 安装依赖
```bash
# 克隆项目
git clone <repository-url>
cd ai_code

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境
```bash
# 复制环境变量模板
cp env_example.txt .env

# 编辑.env文件，添加你的API密钥
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
```

### 4. 运行系统
```bash
# 启动服务
python run.py

# 访问系统
# http://localhost:8001
```

### 5. 测试功能
```bash
# 运行基础功能测试
python test/test_ai_basic.py

# 运行综合测试
python test/test_comprehensive.py
```

## 📖 使用指南

### 文献上传
1. 注册/登录账户
2. 创建或加入研究组
3. 上传PDF/DOCX文献文件
4. 系统自动提取和向量化文本

### AI问答
1. 选择已上传的文献
2. 在问答界面输入问题
3. 系统返回基于文献内容的答案
4. 查看引用来源和置信度
5. 继续多轮对话深入讨论

### 预设问题
- "这篇文献的主要论点是什么？"
- "文献中使用了哪些研究方法？"
- "有什么创新点和贡献？"
- "存在哪些局限性？"
- "主要结论是什么？"

## 🔧 配置说明

### RAG配置参数
```python
# 核心参数
RAG_MAX_CONTEXT_TOKENS = 3000      # 最大上下文长度
RAG_TOP_K_RETRIEVAL = 5            # 检索文档块数量
RAG_CONVERSATION_MAX_TURNS = 10     # 最大对话轮次
RAG_CACHE_TTL = 3600               # 缓存过期时间(秒)

# 质量控制
RAG_MIN_CONFIDENCE = 0.3           # 最小置信度阈值
RAG_MAX_ANSWER_LENGTH = 2000       # 最大答案长度
```

### 性能配置
```python
# 缓存大小
RAG_CACHE_EMBEDDING_MAX_SIZE = 1000
RAG_CACHE_ANSWER_MAX_SIZE = 500
RAG_CACHE_CHUNK_MAX_SIZE = 2000
```

## 📊 性能指标

### 目标性能
- 问答响应时间: < 5秒
- Embedding生成: < 2秒
- 向量检索: < 1秒
- 缓存命中率: > 60%
- 并发用户: ≥ 20

### 质量指标
- 答案准确率: > 85%
- 引用准确性: > 90%
- 对话连贯性: > 80%

## 🧪 测试

### 单元测试
```bash
# 测试RAG核心功能
python test/test_rag_service.py

# 测试向量数据库
python test/test_vector_database.py

# 测试文本处理
python test/test_text_processing.py
```

### 集成测试
```bash
# 端到端测试
python test/test_comprehensive.py
```

## 🔄 开发状态

### 已完成功能 ✅
- [x] 基础文献管理系统
- [x] 用户认证和权限管理
- [x] 文件上传和处理
- [x] 文本提取和分块
- [x] 向量化和存储
- [x] 向量检索功能
- [x] Google Gemini API集成
- [x] RAG问答系统架构设计

### 开发中功能 🚧
- [ ] RAG核心服务实现
- [ ] 对话管理系统
- [ ] AI问答API接口
- [ ] 缓存优化系统
- [ ] 答案质量评估

### 计划功能 📋
- [ ] 流式响应支持
- [ ] 多语言文献支持
- [ ] 知识图谱集成
- [ ] 个性化推荐
- [ ] 高级分析功能

## 🤝 贡献指南

### 开发环境设置
1. Fork项目仓库
2. 创建功能分支
3. 遵循代码规范
4. 编写测试用例
5. 提交Pull Request

### 代码规范
- 使用中文注释
- 遵循PEP 8规范
- 函数和类需要文档字符串
- 关键功能需要单元测试

## 📝 更新日志

### v1.0.0 (开发中)
- 完成基础架构设计
- 实现文献管理功能
- 集成向量数据库
- 完成RAG系统规划

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件
- 参与讨论

## 🙏 致谢

感谢以下开源项目的支持：
- FastAPI
- ChromaDB
- Google Generative AI
- SQLAlchemy
- 其他依赖项目

---

**注意**: 本项目目前处于活跃开发阶段，部分功能可能尚未完全实现。请参考开发状态部分了解当前进度。