# 🤖 AI论文小助手

智能文献管理与学术辅助平台，支持PDF文献上传、AI对话问答、智能体任务处理、综述生成、数据可视化等功能。

## ✨ 功能特性

### 📚 智能文献管理
- PDF文献批量上传与解析
- 自动提取标题、作者、摘要、关键词
- 文本分块与向量化索引
- 支持文件替换和删除

### 💬 AI智能对话
- 基于RAG技术的文献问答
- 多轮对话上下文理解
- 引用溯源，答案可追溯原文
- 支持智谱AI、Kimi、DeepSeek等API

### 🤖 智能体
- **自动任务拆解**：将复杂查询自动拆解为多个可执行子任务
- **多步骤执行**：依次执行任务，前一个任务的输出作为后一个任务的输入
- **结果整合**：自动汇总所有任务结果，提供完整答案
- **任务追溯**：显示每个任务的执行过程和结果
- **灵活应用**：支持检索、分析、总结、生成等多种任务类型

### 📝 综述生成
- 自动分析多篇文献
- 生成结构化学术综述
- 支持自定义字数和语言
- 流式输出，实时预览

### 📊 图表生成
- CSV/Excel数据导入
- 支持折线图、柱状图、散点图、饼图
- 灵活配置X/Y轴
- 实时预览和下载

### 🔐 用户系统（多人版）
- JWT Token认证
- 用户注册/登录
- 数据隔离，每位用户独立
- 适合部署到服务器多人使用

## 🛠️ 技术架构

```
后端：FastAPI + SQLAlchemy + SQLite
智能体：自研Agent框架（任务拆解与多步骤执行）
向量检索：FAISS (IndexFlatIP)
文本嵌入：简单哈希/Sentence-Transformers
AI接口：OpenAI兼容格式（智谱AI/Kimi/DeepSeek）
PDF解析：pdfplumber
前端：原生HTML/JavaScript
```

## 📦 安装部署

### 1. 克隆项目

```bash
git clone <项目地址>
cd 论文小助手
```

### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建 `backend/.env` 文件：

```env
# AI API配置（智谱AI）
KIMI_API_KEY=your_api_key_here
KIMI_MODEL=glm-4
KIMI_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 或使用 Kimi
# KIMI_MODEL=moonshot-v1-128k
# KIMI_BASE_URL=https://api.moonshot.cn/v1

# 服务器配置
HOST=0.0.0.0
PORT=8000
DEBUG=false

# 数据存储（多人部署时改为false）
USE_TEMP_STORAGE=false
```

### 5. 启动服务

```bash
cd backend
python run.py
```

访问 http://localhost:8000

## 🚀 使用说明

### 默认账号
- 用户名：`admin`
- 密码：`admin123`

首次启动会自动创建默认管理员账号。

### 快速开始

1. **注册/登录**：使用默认账号或注册新账号
2. **上传文献**：在"文献管理"页面上传PDF文件
3. **智能对话**：切换到"智能对话"，基于上传的文献进行问答
4. **智能体**：切换到"智能体"，输入复杂查询，自动拆解任务并执行
5. **生成综述**：在"综述生成"页面自动生成学术综述
6. **数据可视化**：在"图表生成"页面上传CSV/Excel生成图表

### 智能体使用示例

**示例1：分析特定领域的研究趋势**
```
输入："分析2023-2024年人工智能在医疗领域的应用"

智能体会自动拆解为：
1. 检索2023-2024年人工智能在医疗领域的应用相关信息
2. 分析检索到的信息
3. 总结人工智能在医疗领域的应用关键发现
4. 生成详细总结报告

结果：显示每个任务的执行过程和最终整合的答案
```

**示例2：对比多篇文献的研究方法**
```
输入："对比上传的文献中关于机器学习算法的研究方法"

智能体会自动拆解为：
1. 检索关于机器学习算法的研究方法
2. 分析不同文献中的算法对比
3. 总结各种方法的优缺点
4. 生成对比分析报告

结果：提供详细的方法对比和总结
```

## ⚙️ 配置说明

### 数据库配置

在 `backend/app/config.py` 中：

```python
# 临时存储模式（每次重启数据清空，适合个人测试）
USE_TEMP_STORAGE = True

# 持久化存储（适合多人部署）
USE_TEMP_STORAGE = False
```

### AI API配置

支持以下API服务商：

| 服务商 | 模型 | Base URL |
|--------|------|----------|
| 智谱AI | glm-4 | https://open.bigmodel.cn/api/paas/v4 |
| Kimi | moonshot-v1-128k | https://api.moonshot.cn/v1 |
| DeepSeek | deepseek-chat | https://api.deepseek.com/v1 |

### 文件限制

- 单个PDF最大：50MB
- 最大页数：500页
- 支持格式：PDF、CSV、XLSX、XLS

## 📡 API接口

### 认证接口

```http
POST /api/auth/register    # 注册
POST /api/auth/login       # 登录
GET  /api/auth/me          # 获取当前用户
POST /api/auth/logout      # 退出
```

### 文献接口

```http
POST   /api/papers/upload       # 上传PDF
GET    /api/papers              # 获取文献列表
GET    /api/papers/{id}         # 获取文献详情
DELETE /api/papers/{id}         # 删除文献
GET    /api/papers/{id}/chunks  # 获取文本块
```

### 对话接口

```http
POST /api/chat/sessions         # 创建会话
GET  /api/chat/sessions         # 获取会话列表
GET  /api/chat/sessions/{id}    # 获取会话详情
POST /api/chat/messages         # 发送消息（流式）
```

### 智能体接口

```http
POST /api/chat/agent/process   # 处理智能体查询
POST /api/chat/agent/create    # 创建智能体
GET  /api/chat/agent/count    # 获取智能体数量
DELETE /api/chat/agent/{id}    # 删除智能体
```

### 综述接口

```http
POST /api/review/generate       # 生成综述（流式）
```

### 图表接口

```http
POST /api/charts/datasets/upload  # 上传数据文件
GET  /api/charts/datasets         # 获取数据集列表
POST /api/charts/generate         # 生成图表
```

## 🔒 安全说明

### 部署前必须修改

1. **修改JWT密钥**：
   ```python
   # backend/app/core/auth.py
   SECRET_KEY = "your-secret-key-here"  # 生产环境请修改
   ```

2. **修改默认管理员密码**：
   首次登录后请立即修改默认密码。

3. **配置CORS**：
   ```python
   # backend/app/main.py
   allow_origins=["https://your-domain.com"]  # 限制具体域名
   ```

### 数据存储

- 数据库：`backend/data/papers.db`
- 上传文件：`backend/data/uploads/{user_id}/`
- 向量索引：`backend/data/vectors/faiss.index`
- 图表文件：`backend/data/charts/`

## 🐛 常见问题

### 1. 注册/登录失败

- 检查后端服务是否正常运行
- 查看浏览器F12控制台错误信息
- 确认bcrypt版本：`pip install bcrypt==4.0.1`

### 2. AI对话无响应

- 检查API Key是否正确配置
- 查看终端日志确认API调用情况
- 确认已上传文献且状态为"已处理"

### 3. 向量检索不到文献

- 确认文献已处理完成（状态显示"已处理"）
- 降低相似度阈值或重新上传文献
- 查看终端日志确认FAISS索引状态

### 4. 图表生成失败

- 确认CSV/Excel格式正确
- 检查X/Y轴列名是否正确
- 确保数值列类型为int或float

## 📁 项目结构

```
论文小助手/
├── backend/               # 后端代码
│   ├── app/
│   │   ├── api/          # API路由
│   │   ├── core/         # 核心模块
│   │   ├── models/       # 数据库模型
│   │   ├── main.py       # 应用入口
│   │   └── config.py     # 配置文件
│   └── run.py            # 启动脚本
├── frontend/             # 前端代码
│   └── app.html          # 主页面
├── requirements.txt      # Python依赖
└── README.md            # 项目说明
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

## 📄 开源协议

MIT License

---

**注意**：本项目仅供学习研究使用，请遵守相关API服务商的使用条款。