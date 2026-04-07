# AI论文小助手 - 产品需求文档 (PRD)

**版本**: v2.0  
**日期**: 2026年  
**状态**: 正式版

---

## 目录

1. [产品概述](#1-产品概述)
2. [系统架构](#2-系统架构)
3. [功能模块设计](#3-功能模块设计)
4. [数据模型](#4-数据模型)
5. [接口规范](#5-接口规范)
6. [项目结构](#6-项目结构)
7. [核心实现](#7-核心实现)
8. [部署配置](#8-部署配置)
9. [验收标准](#9-验收标准)
10. [Roadmap](#10-roadmap)

---

## 1. 产品概述

### 1.1 产品定位

AI论文小助手是一款面向学术研究人员、高校学生和科研工作者的智能文献管理与学术辅助平台。通过RAG（检索增强生成）技术和智能体（Agent）技术，结合大语言模型的能力，实现PDF文献的智能解析、问答交互、综述生成、数据可视化及复杂任务自动化处理。

### 1.2 目标用户

| 用户群体 | 核心需求 | 使用场景 |
|---------|---------|---------|
| 研究生/博士生 | 快速理解文献、撰写综述、数据分析 | 文献调研、论文写作、实验分析 |
| 科研人员 | 管理大量文献、知识提取、自动化研究 | 项目研究、成果整理、学术写作 |
| 高校教师 | 课程资料整理、教学辅助、学术指导 | 备课、指导学生、学术评审 |
| 企业研发人员 | 技术调研、竞品分析、专利分析 | 技术研究、产品开发 |

### 1.3 核心功能

| 功能模块 | 功能描述 | 价值主张 |
|---------|---------|---------|
| 文献智能库 | 多PDF导入、向量化存储、语义检索 | 统一管理文献，支持全文检索 |
| 智能对话 | 基于文献内容的问答系统 | 快速获取文献关键信息 |
| 智能体 | 自动任务拆解、多步骤执行、结果整合 | 处理复杂查询，自动化研究流程 |
| 综述生成 | 自动生成结构化文献综述 | 大幅提升综述写作效率 |
| 图表生成 | Excel/CSV数据可视化 | 一键生成学术图表 |
| 用户系统 | 多用户支持、数据隔离 | 适合团队协作和部署 |

### 1.4 技术栈

| 层级 | 技术选型 | 说明 |
|-----|---------|-----|
| 后端框架 | Python + FastAPI | 高性能异步Web框架 |
| 大模型 | Kimi/智谱AI/DeepSeek | 支持多种LLM API |
| 智能体 | 自研Agent框架 | 任务拆解与多步骤执行 |
| 向量数据库 | FAISS | Facebook开源向量检索库 |
| 文档解析 | pdfplumber | 精准提取PDF文本 |
| 文本向量化 | sentence-transformers | 轻量级embedding模型 |
| 数据可视化 | matplotlib + seaborn | 学术级图表绘制 |
| 前端 | 原生HTML/JavaScript | 响应式用户界面 |
| 数据存储 | SQLite | 轻量级本地数据库 |
| 认证授权 | JWT + bcrypt | 安全的用户认证 |

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Frontend)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  文献管理页面  │  │  对话问答页面  │  │    智能体页面       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  综述生成页面  │  │  图表生成页面  │  │    用户管理页面       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 网关层 (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 文献管理API  │  │ 对话问答API  │  │    智能体API         │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 综述生成API  │  │ 图表生成API  │  │    认证授权API       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     核心服务层 (Core Services)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ PDF解析服务  │  │ RAG检索服务  │  │   智能体服务        │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 文本向量化   │  │ 综述生成服务 │  │   LLM调用服务       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ 数据可视化   │  │ 认证授权服务 │  │   分析统计服务       │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层 (Storage)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   SQLite     │  │    FAISS     │  │    本地文件系统       │   │
│  │ (元数据存储) │  │ (向量索引)   │  │  (PDF/Excel/CSV)     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

#### 文献导入流程
```
用户上传PDF → PDF解析 → 文本分块 → 向量化 → FAISS存储 + SQLite元数据
```

#### 对话问答流程
```
用户提问 → 问题向量化 → FAISS相似度检索 → 获取相关文本块 → 
构建Prompt → LLM API调用 → 流式返回答案
```

#### 智能体执行流程
```
用户输入复杂查询 → 智能体任务拆解 → 多步骤任务执行 → 
任务结果整合 → 返回完整答案
```

#### 综述生成流程
```
选择文献范围 → 批量检索相关段落 → 构建综述Prompt → 
LLM生成综述 → 返回结构化文本
```

---

## 3. 功能模块设计

### 3.1 文献管理模块

#### 3.1.1 PDF导入功能

**支持格式**
- PDF文件（单文件或多文件批量上传）

**限制条件**
| 参数 | 限制值 | 说明 |
|-----|-------|-----|
| 单文件大小 | 50MB | 大文件自动分块处理 |
| 批量上传数量 | 20个文件 | 并发处理 |

**解析内容**
| 字段 | 提取方式 | 存储位置 |
|-----|---------|---------|
| 标题 | 首段文本提取 | SQLite |
| 作者 | 正则匹配 | SQLite (JSON) |
| 摘要 | Abstract章节提取 | SQLite |
| 关键词 | 正则匹配 | SQLite (JSON) |
| 正文内容 | 按段落分块 | FAISS向量库 |
| 页码信息 | pdfplumber获取 | SQLite |

#### 3.1.2 文献库管理功能

| 功能 | 描述 |
|-----|-----|
| 列表展示 | 分页、排序、搜索、筛选 |
| 文献删除 | 软删除，同步清理向量数据 |
| 标签分类 | 支持自定义标签体系 |
| 批量操作 | 批量删除、批量导出 |

### 3.2 RAG对话模块

#### 3.2.1 文本向量化策略

**分块策略**
| 策略 | 参数 | 适用场景 |
|-----|-----|---------|
| 按段落分割 | - | 默认策略，保留语义完整性 |
| 固定token数 | 512 tokens/块，重叠128 tokens | 长文档优化 |

**向量模型配置**
| 模型 | 维度 | 特点 |
|-----|-----|-----|
| all-MiniLM-L6-v2 | 384维 | 轻量级，英文优化 |
| BAAI/bge-large-zh-v1.5 | 1024维 | 中文优化，精度更高 |

**FAISS索引配置**
```python
retrieval_config = {
    "top_k": 5,                    # 返回最相关的5个文本块
    "similarity_threshold": 0.7,   # 相似度阈值
    "rerank_enabled": True,        # 是否启用重排序
    "context_window": 3            # 上下文窗口（前后各3个段落）
}
```

#### 3.2.2 对话管理

| 功能 | 说明 |
|-----|-----|
| 多轮对话 | 保留对话历史，支持上下文关联 |
| 答案溯源 | 显示引用来源文献及页码 |
| 文献范围限定 | 支持指定特定文献进行问答 |

#### 3.2.3 Prompt模板

```
【系统提示】
你是一位专业的学术助手，擅长分析和总结学术论文。请基于以下提供的文献内容，回答用户的问题。
如果提供的文献内容不足以回答问题，请明确告知。

【文献内容】
{retrieved_context}

【对话历史】
{chat_history}

【用户问题】
{user_question}

【回答要求】
1. 基于文献内容作答，不要编造信息
2. 如涉及多个文献，请分别说明
3. 引用格式：[文献标题, 第X页]
```

### 3.3 智能体模块

#### 3.3.1 智能体概述

智能体（Agent）是系统的核心创新功能，能够自动将复杂的学术查询拆解为多个可执行的子任务，并按照逻辑顺序依次执行，最终整合所有任务的结果，为用户提供完整的答案。

#### 3.3.2 任务拆解

**拆解能力**
| 任务类型 | 描述 | 适用场景 |
|---------|-----|---------|
| retrieve | 检索相关信息 | 获取文献内容 |
| analyze | 分析信息 | 深度分析检索结果 |
| summarize | 总结信息 | 提炼关键信息 |
| generate | 生成内容 | 创建报告或文档 |

**拆解示例**
```
用户查询: "分析2023-2024年人工智能在医疗领域的应用"

拆解为:
- task_1: 检索2023-2024年人工智能在医疗领域的应用相关信息
- task_2: 分析检索到的信息
- task_3: 总结人工智能在医疗领域的应用关键发现
- task_4: 生成详细总结报告
```

#### 3.3.3 任务执行

**执行流程**
```
1. 任务拆解 → 生成任务列表
2. 依次执行每个任务
3. 任务间数据传递 → 前一个任务的输出作为后一个任务的输入
4. 结果整合 → 汇总所有任务结果
5. 生成最终答案
```

**数据传递机制**
- 自动将前一个任务的结果传递给下一个任务
- 支持多种数据格式：列表（检索结果）、字符串（总结/生成）、字典（分析结果）
- 智能处理不同类型的结果，确保数据正确传递

#### 3.3.4 结果整合

**整合策略**
- 任务状态跟踪：pending、in_progress、completed、failed
- 结果格式化：将不同类型的任务结果转换为统一格式
- 摘要生成：基于所有任务结果生成执行摘要

**展示内容**
```
📋 执行摘要
任务执行完成：4个任务成功，0个任务失败

🔄 执行的任务
- 任务 1: 检索相关信息
  类型: retrieve
  状态: completed

- 任务 2: 分析信息
  类型: analyze
  状态: completed

📊 任务结果
- 任务 task_1 - 检索结果
  [具体的检索结果...]

- 任务 task_2 - 分析结果
  [具体的分析结果...]
```

#### 3.3.5 智能体优势

| 优势 | 说明 |
|-----|-----|
| 自动化 | 无需手动拆解任务，自动完成复杂查询 |
| 多步骤 | 支持复杂的推理链，逐步深入分析 |
| 结果整合 | 自动汇总多个任务结果，提供完整答案 |
| 灵活性 | 支持各种类型的学术查询和研究任务 |
| 可追溯 | 显示每个任务的执行过程和结果 |

### 3.4 综述生成模块

#### 3.3.1 生成模式

| 模式 | 描述 | 适用场景 |
|-----|-----|---------|
| 全文综述 | 基于整个文献库生成领域综述 | 领域调研 |
| 选文综述 | 基于选定的若干文献生成综述 | 专题研究 |
| 主题综述 | 基于特定主题词检索相关文献生成综述 | 热点追踪 |

#### 3.3.2 综述结构模板

```
1. 研究背景与意义
2. 相关研究综述
   2.1 [细分主题1]
   2.2 [细分主题2]
   ...
3. 研究方法对比
4. 主要发现与结论
5. 研究不足与展望
6. 参考文献列表
```

#### 3.3.3 综述Prompt模板

```
【系统提示】
你是一位资深的学术综述撰写专家。请基于以下文献内容，撰写一篇结构化的学术综述。

【任务要求】
- 综述主题：{topic}
- 文献数量：{paper_count}篇
- 字数要求：{word_count}字
- 输出语言：{language}

【文献内容摘要】
{papers_summary}

【详细内容】
{retrieved_content}

【输出格式】
请按以下结构输出：
1. 标题（简洁明确）
2. 摘要（200-300字）
3. 正文（分章节论述）
4. 总结与展望
```

### 3.5 图表生成模块

#### 3.4.1 数据导入

| 参数 | 配置 |
|-----|-----|
| 支持格式 | Excel (.xlsx, .xls)、CSV (.csv) |
| 文件大小限制 | 10MB |
| 数据预览 | 显示前10行 |

#### 3.4.2 图表配置

| 配置项 | 选项 |
|--------|------|
| 图表类型 | 折线图、柱状图、散点图、饼图 |
| X轴 | 选择数据列 / 设置范围 / 设置标签 |
| Y轴 | 选择数据列 / 设置范围 / 设置标签 |
| 数据筛选 | 行范围选择 / 条件筛选 |
| 样式设置 | 颜色主题、标题、图例、网格线 |
| 导出格式 | PNG、JPG、SVG、PDF |

---

## 4. 数据模型

### 4.1 SQLite 数据库设计

```sql
-- 文献表
CREATE TABLE papers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    title TEXT,
    authors TEXT,  -- JSON格式存储
    abstract TEXT,
    keywords TEXT,  -- JSON格式存储
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    page_count INTEGER,
    chunk_count INTEGER,
    status TEXT DEFAULT 'active',  -- active, deleted, processing
    UNIQUE(file_path)
);

-- 文本块表（向量化后的文本片段）
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    page_number INTEGER,
    faiss_id INTEGER,  -- FAISS中的向量ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (paper_id) REFERENCES papers(id) ON DELETE CASCADE
);

-- 对话会话表
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 对话消息表
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    references TEXT,  -- JSON格式，引用文献信息
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- 数据集表
CREATE TABLE datasets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- excel, csv
    sheet_name TEXT,  -- Excel的sheet名
    columns TEXT,  -- JSON格式，列信息
    row_count INTEGER,
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 图表配置表
CREATE TABLE chart_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id INTEGER NOT NULL,
    chart_name TEXT,
    chart_type TEXT NOT NULL,  -- line, bar, scatter, pie
    x_column TEXT NOT NULL,
    y_column TEXT NOT NULL,
    x_range TEXT,  -- JSON格式 [min, max]
    y_range TEXT,
    filter_config TEXT,  -- JSON格式筛选配置
    style_config TEXT,  -- JSON格式样式配置
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dataset_id) REFERENCES datasets(id) ON DELETE CASCADE
);
```

### 4.2 FAISS 索引设计

```python
class VectorIndex:
    def __init__(self, dim=384):
        self.dim = dim
        # 使用内积作为相似度度量（已归一化的向量等价于余弦相似度）
        self.index = faiss.IndexFlatIP(dim)
        # ID映射：FAISS ID -> (paper_id, chunk_id)
        self.id_map = {}
    
    def add_vectors(self, vectors, metadata):
        """
        Args:
            vectors: numpy array of shape (n, dim)
            metadata: list of dict [{'paper_id': x, 'chunk_id': y}, ...]
        """
        start_id = self.index.ntotal
        self.index.add(vectors)
        for i, meta in enumerate(metadata):
            self.id_map[start_id + i] = meta
    
    def search(self, query_vector, k=5):
        """
        Returns:
            distances, indices, metadata
        """
        distances, indices = self.index.search(query_vector, k)
        metadata = [self.id_map.get(idx) for idx in indices[0]]
        return distances[0], indices[0], metadata
```

---

## 5. 接口规范

### 5.1 文献管理接口

#### 上传PDF
```yaml
POST /api/papers/upload
Content-Type: multipart/form-data
Body:
  files: [File]  # 支持多文件
Response:
  {
    "code": 200,
    "data": {
      "uploaded": [{
        "id": 1,
        "file_name": "paper1.pdf",
        "status": "processing"
      }],
      "failed": []
    }
  }
```

#### 获取文献列表
```yaml
GET /api/papers?page=1&size=20&keyword=&sort_by=upload_time
Response:
  {
    "code": 200,
    "data": {
      "total": 100,
      "items": [{
        "id": 1,
        "title": "...",
        "authors": [...],
        "upload_time": "2024-01-01T00:00:00",
        "status": "active"
      }]
    }
  }
```

#### 删除文献
```yaml
DELETE /api/papers/{id}
```

#### 获取文献详情
```yaml
GET /api/papers/{id}
```

### 5.2 对话接口

#### 创建会话
```yaml
POST /api/chat/sessions
Body:
  { "session_name": "新会话" }
```

#### 获取会话列表
```yaml
GET /api/chat/sessions
```

#### 发送消息（流式响应）
```yaml
POST /api/chat/messages
Body:
  {
    "session_id": 1,
    "message": "请总结这篇论文的主要贡献",
    "paper_ids": [1, 2, 3]  # 可选，指定文献范围
  }
Response (SSE Stream):
  { "type": "content", "data": "..." }
  { "type": "reference", "data": {...} }
  { "type": "done" }
```

#### 获取历史消息
```yaml
GET /api/chat/sessions/{id}/messages
```

### 5.3 综述生成接口

#### 生成综述（流式响应）
```yaml
POST /api/review/generate
Body:
  {
    "topic": "深度学习在医学影像中的应用",
    "paper_ids": [1, 2, 3],  # 可选，不传则使用全部文献
    "word_count": 3000,
    "language": "zh",
    "structure": "standard"  # standard / custom
  }
Response (SSE Stream):
  { "type": "content", "data": "..." }
```

#### 导出综述
```yaml
POST /api/review/export
Body:
  {
    "content": "...",
    "format": "pdf"  # pdf / docx / markdown
  }
```

### 5.4 智能体接口

#### 处理智能体查询
```yaml
POST /api/chat/agent/process
Body:
  {
    "query": "分析2023-2024年人工智能在医疗领域的应用"
  }
Response:
  {
    "code": 200,
    "data": {
      "summary": "任务执行完成：4个任务成功，0个任务失败",
      "response": "任务执行完成",
      "tasks": [
        {
          "id": "task_1",
          "description": "检索2023-2024年人工智能在医疗领域的应用相关信息",
          "type": "retrieve",
          "params": {"query": "..."},
          "status": "completed",
          "result": [...]
        },
        {
          "id": "task_2",
          "description": "分析检索到的信息",
          "type": "analyze",
          "params": {},
          "status": "completed",
          "result": {"analysis": "..."}
        }
      ],
      "results": {
        "task_1": [...],
        "task_2": {"analysis": "..."}
      }
    }
  }
```

#### 创建智能体
```yaml
POST /api/chat/agent/create
Response:
  {
    "agent_id": "agent_123"
  }
```

#### 获取智能体数量
```yaml
GET /api/chat/agent/count
Response:
  {
    "count": 5
  }
```

#### 删除智能体
```yaml
DELETE /api/chat/agent/{agent_id}
Response:
  {
    "success": true
  }
```

### 5.5 图表生成接口

#### 上传数据文件
```yaml
POST /api/charts/datasets
Content-Type: multipart/form-data
Body:
  file: File
Response:
  {
    "code": 200,
    "data": {
      "id": 1,
      "columns": [
        {"name": "年份", "type": "int"},
        {"name": "销量", "type": "float"}
      ],
      "preview": [...]
    }
  }
```

#### 生成图表
```yaml
POST /api/charts/generate
Body:
  {
    "dataset_id": 1,
    "chart_type": "line",
    "x_column": "年份",
    "y_column": "销量",
    "x_range": [2010, 2024],
    "y_range": null,
    "style": {
      "title": "年度销量趋势",
      "color": "#1890ff"
    }
  }
Response:
  {
    "code": 200,
    "data": {
      "chart_url": "/static/charts/chart_123.png",
      "chart_data": {...}
    }
  }
```

#### 导出图表
```yaml
GET /api/charts/{id}/export?format=png
```

---

## 6. 项目结构

```
论文小助手/
├── backend/                    # 后端服务
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置文件
│   │   ├── api/               # API路由
│   │   │   ├── __init__.py
│   │   │   ├── papers.py      # 文献接口
│   │   │   ├── chat.py        # 对话接口
│   │   │   ├── review.py      # 综述接口
│   │   │   └── charts.py      # 图表接口
│   │   ├── core/              # 核心业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── pdf_parser.py  # PDF解析
│   │   │   ├── embedder.py    # 文本向量化
│   │   │   ├── retriever.py   # FAISS检索
│   │   │   ├── kimi_client.py # Kimi API封装
│   │   │   ├── reviewer.py    # 综述生成
│   │   │   └── chart_gen.py   # 图表生成
│   │   ├── models/            # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── database.py    # SQLAlchemy模型
│   │   │   └── schemas.py     # Pydantic模型
│   │   └── services/          # 服务层
│   │       ├── __init__.py
│   │       ├── paper_service.py
│   │       ├── chat_service.py
│   │       └── chart_service.py
│   ├── data/                  # 数据存储
│   │   ├── uploads/           # 上传文件
│   │   ├── vectors/           # FAISS索引文件
│   │   └── charts/            # 生成图表
│   ├── requirements.txt
│   └── run.py
│
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── components/        # 组件
│   │   ├── views/             # 页面
│   │   ├── api/               # API封装
│   │   ├── stores/            # 状态管理
│   │   └── utils/             # 工具函数
│   ├── package.json
│   └── vite.config.js
│
├── docs/                       # 文档
│   └── PRD.md
│
└── README.md
```

---

## 7. 核心实现

### 7.1 FAISS向量检索

```python
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple
import pickle
import os

class FAISSRetriever:
    def __init__(self, dim: int = 384, index_path: str = None):
        self.dim = dim
        self.index_path = index_path
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        self.index = None
        self.metadata = {}  # faiss_id -> chunk_info
        
        if index_path and os.path.exists(index_path):
            self.load_index()
        else:
            self.index = faiss.IndexFlatIP(dim)  # 内积相似度
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """文本向量化"""
        embeddings = self.encoder.encode(texts, convert_to_numpy=True)
        # L2归一化，使内积等价于余弦相似度
        faiss.normalize_L2(embeddings)
        return embeddings.astype('float32')
    
    def add_documents(self, chunks: List[Dict]):
        """
        添加文档到索引
        chunks: [{"paper_id": 1, "chunk_id": 1, "content": "..."}, ...]
        """
        if not chunks:
            return
        
        texts = [c["content"] for c in chunks]
        embeddings = self.encode(texts)
        
        start_id = self.index.ntotal
        self.index.add(embeddings)
        
        # 保存metadata
        for i, chunk in enumerate(chunks):
            self.metadata[start_id + i] = {
                "paper_id": chunk["paper_id"],
                "chunk_id": chunk["chunk_id"],
                "content": chunk["content"],
                "page_number": chunk.get("page_number")
            }
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """检索相关文档"""
        query_vector = self.encode([query])
        
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1 and idx in self.metadata:
                result = self.metadata[idx].copy()
                result["score"] = float(dist)
                results.append(result)
        
        return results
    
    def save_index(self):
        """保存索引到磁盘"""
        if self.index_path:
            faiss.write_index(self.index, self.index_path)
            with open(self.index_path + ".meta", "wb") as f:
                pickle.dump(self.metadata, f)
    
    def load_index(self):
        """从磁盘加载索引"""
        self.index = faiss.read_index(self.index_path)
        meta_path = self.index_path + ".meta"
        if os.path.exists(meta_path):
            with open(meta_path, "rb") as f:
                self.metadata = pickle.load(f)
```

### 7.2 Kimi API 调用

```python
import openai
from typing import List, Dict, Iterator
import os

class KimiClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.moonshot.cn/v1"
        )
        self.model = "moonshot-v1-128k"  # 或 32k, 8k
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        temperature: float = 0.3
    ) -> Iterator[str]:
        """调用Kimi对话接口"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=stream,
                temperature=temperature
            )
            
            if stream:
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                yield response.choices[0].message.content
                
        except Exception as e:
            yield f"Error: {str(e)}"
    
    def build_rag_prompt(
        self,
        query: str,
        contexts: List[Dict],
        chat_history: List[Dict] = None
    ) -> List[Dict]:
        """构建RAG对话的Prompt"""
        # 构建上下文
        context_text = "\n\n".join([
            f"【文献 {i+1}】{ctx.get('title', 'Unknown')}, 第{ctx.get('page_number', '?')}页\n{ctx['content'][:1000]}"
            for i, ctx in enumerate(contexts)
        ])
        
        system_prompt = f"""你是一位专业的学术助手。请基于以下文献内容回答用户问题。
如果文献内容不足以回答问题，请明确告知。

【相关文献内容】
{context_text}

回答时请：
1. 基于文献内容作答，不要编造
2. 引用来源格式：[文献标题, 第X页]
3. 如涉及多个文献，请分别说明"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话
        if chat_history:
            messages.extend(chat_history)
        
        messages.append({"role": "user", "content": query})
        
        return messages
```

### 7.3 PDF解析

```python
import pdfplumber
from typing import List, Dict
import re

class PDFParser:
    def __init__(self):
        self.chunk_size = 512  # 每块大约字符数
        self.chunk_overlap = 128
    
    def parse(self, file_path: str) -> Dict:
        """解析PDF文件"""
        result = {
            "title": "",
            "authors": [],
            "abstract": "",
            "keywords": [],
            "chunks": [],
            "page_count": 0
        }
        
        with pdfplumber.open(file_path) as pdf:
            result["page_count"] = len(pdf.pages)
            full_text = ""
            
            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                full_text += f"\n\n--- Page {page_num} ---\n{text}"
            
            # 提取元数据
            result["title"] = self._extract_title(full_text)
            result["abstract"] = self._extract_abstract(full_text)
            result["chunks"] = self._split_into_chunks(full_text)
        
        return result
    
    def _extract_title(self, text: str) -> str:
        """提取标题（取第一段非空文本）"""
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        return lines[0] if lines else "Unknown"
    
    def _extract_abstract(self, text: str) -> str:
        """提取摘要"""
        match = re.search(r'Abstract[\s:]*(.+?)(?=\n\n|Keywords|Introduction)', 
                         text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _split_into_chunks(self, text: str) -> List[Dict]:
        """将文本分块"""
        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        chunks = []
        current_chunk = ""
        current_pages = []
        
        for para in paragraphs:
            # 提取页码信息
            page_match = re.search(r'--- Page (\d+) ---', para)
            if page_match:
                current_pages.append(int(page_match.group(1)))
                continue
            
            if len(current_chunk) + len(para) > self.chunk_size:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "page_number": current_pages[0] if current_pages else 1
                    })
                current_chunk = para
                current_pages = current_pages[-1:] if current_pages else []
            else:
                current_chunk += "\n\n" + para
        
        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "page_number": current_pages[0] if current_pages else 1
            })
        
        return chunks
```

### 7.4 图表生成

```python
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional
import io
import base64

class ChartGenerator:
    def __init__(self):
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
        sns.set_style("whitegrid")
    
    def load_data(self, file_path: str, sheet_name: str = None) -> pd.DataFrame:
        """加载数据文件"""
        if file_path.endswith('.csv'):
            return pd.read_csv(file_path)
        else:
            return pd.read_excel(file_path, sheet_name=sheet_name)
    
    def generate_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x_column: str,
        y_column: str,
        x_range: Optional[List] = None,
        y_range: Optional[List] = None,
        style: Dict = None
    ) -> str:
        """生成图表，返回base64编码的图片"""
        style = style or {}
        
        # 数据筛选
        if x_range:
            df = df[(df[x_column] >= x_range[0]) & (df[x_column] <= x_range[1])]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if chart_type == "line":
            ax.plot(df[x_column], df[y_column], 
                   marker='o', linewidth=2, 
                   color=style.get('color', '#1890ff'))
        elif chart_type == "bar":
            ax.bar(df[x_column], df[y_column], 
                  color=style.get('color', '#1890ff'),
                  alpha=0.8)
        elif chart_type == "scatter":
            ax.scatter(df[x_column], df[y_column], 
                      c=style.get('color', '#1890ff'),
                      alpha=0.6, s=50)
        
        # 设置标签和标题
        ax.set_xlabel(x_column, fontsize=12)
        ax.set_ylabel(y_column, fontsize=12)
        ax.set_title(style.get('title', f'{y_column} vs {x_column}'), fontsize=14)
        
        # 设置坐标轴范围
        if y_range:
            ax.set_ylim(y_range)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # 转为base64
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', dpi=150)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close(fig)
        
        return f"data:image/png;base64,{image_base64}"
```

---

## 8. 部署配置

### 8.1 环境变量

```bash
# .env 文件
KIMI_API_KEY=your_kimi_api_key_here
DB_PATH=./data/papers.db
VECTOR_INDEX_PATH=./data/vectors/faiss.index
UPLOAD_DIR=./data/uploads
CHART_DIR=./data/charts
MAX_FILE_SIZE=52428800  # 50MB
CHUNK_SIZE=512
CHUNK_OVERLAP=128
TOP_K_RETRIEVAL=5
```

### 8.2 依赖列表

```txt
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
sqlalchemy==2.0.23
faiss-cpu==1.7.4
sentence-transformers==2.2.2
pdfplumber==0.10.0
openai==1.3.6
pandas==2.1.3
matplotlib==3.8.2
seaborn==0.13.0
openpyxl==3.1.2
python-dotenv==1.0.0
pydantic==2.5.2
numpy==1.26.2
```

### 8.3 启动命令

```bash
# 后端启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端启动（开发模式）
cd frontend
npm install
npm run dev
```

---

## 9. 验收标准

### 9.1 文献管理

| 验收项 | 标准 | 优先级 |
|-------|-----|-------|
| 批量上传 | 单次最多20个PDF文件 | P0 |
| 解析准确率 | 标题、作者、摘要提取 > 90% | P0 |
| 处理性能 | 100页PDF处理时间 < 30秒 | P1 |
| 向量化存储 | 成功率 100% | P0 |

### 9.2 智能对话

| 验收项 | 标准 | 优先级 |
|-------|-----|-------|
| 响应时间 | 检索响应 < 5秒（不含大模型生成） | P0 |
| 答案溯源 | 引用准确率 > 95% | P0 |
| 多轮对话 | 支持上下文关联 | P1 |
| 文献限定 | 支持指定文献范围问答 | P1 |

### 9.3 综述生成

| 验收项 | 标准 | 优先级 |
|-------|-----|-------|
| 生成性能 | 3000字综述 < 60秒 | P1 |
| 结构完整性 | 包含背景、方法、结论等章节 | P0 |
| 引用溯源 | 引用来源准确可追踪 | P0 |
| 导出功能 | 支持PDF/Word/Markdown | P1 |

### 9.4 图表生成

| 验收项 | 标准 | 优先级 |
|-------|-----|-------|
| 数据导入 | 支持Excel/CSV | P0 |
| 图表类型 | 支持折线、柱状、散点、饼图 | P0 |
| 轴配置 | X/Y轴范围可配置 | P1 |
| 导出格式 | 支持PNG/JPG/SVG/PDF | P1 |

---

## 10. Roadmap

### Phase 1 - MVP（4周）
- [x] PDF解析与存储
- [x] FAISS向量检索
- [x] 基础对话功能
- [x] Kimi API集成

### Phase 2 - 功能完善（3周）
- [ ] 综述生成功能
- [ ] 图表生成模块
- [ ] 前端界面优化
- [ ] 对话历史管理

### Phase 3 - 增强优化（持续）
- [ ] 多模态支持（图表OCR）
- [ ] 协作功能（文献共享）
- [ ] AI助手增强（润色、翻译）
- [ ] 知识图谱构建

### 未来方向
1. **多模态支持**：图表、公式的OCR识别
2. **协作功能**：文献共享、评论、批注
3. **AI助手增强**：论文润色、翻译、格式检查
4. **知识图谱**：构建文献间的引用关系图谱
5. **移动端适配**：开发iOS/Android应用

---

## 附录

### A. 参考资料

| 资源 | 链接 |
|-----|-----|
| Kimi API文档 | https://platform.moonshot.cn/ |
| FAISS文档 | https://github.com/facebookresearch/faiss/wiki |
| FastAPI文档 | https://fastapi.tiangolo.com/ |

### B. 推荐前置知识

- Python异步编程 (async/await)
- FastAPI框架基础
- 向量检索原理
- LLM Prompt Engineering