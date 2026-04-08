"""
FastAPI 应用入口
AI论文小助手后端服务
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import config
from app.models.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    print("=" * 50)
    print("🚀 AI论文小助手 正在启动...")
    print("=" * 50)
    
    # 初始化数据库
    print("📦 初始化数据库...")
    init_db()
    print("✅ 数据库初始化完成")
    
    # 创建默认管理员账号
    from app.models.database import SessionLocal
    from app.core.auth import create_default_admin
    db = SessionLocal()
    try:
        create_default_admin(db)
    finally:
        db.close()
    
    # 检查必要的目录
    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    os.makedirs(config.CHART_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(config.VECTOR_INDEX_PATH), exist_ok=True)
    
    # 检查数据库文件
    db_exists = os.path.exists(config.DB_PATH)
    db_size = os.path.getsize(config.DB_PATH) if db_exists else 0
    print(f"📁 数据库路径: {os.path.abspath(config.DB_PATH)} (存在: {db_exists}, 大小: {db_size} bytes)")
    
    # 检查FAISS索引
    index_exists = os.path.exists(config.VECTOR_INDEX_PATH)
    index_size = os.path.getsize(config.VECTOR_INDEX_PATH) if index_exists else 0
    print(f"🔍 向量索引: {os.path.abspath(config.VECTOR_INDEX_PATH)} (存在: {index_exists}, 大小: {index_size} bytes)")
    
    # 检查上传目录中的文件
    upload_files = os.listdir(config.UPLOAD_DIR) if os.path.exists(config.UPLOAD_DIR) else []
    print(f"📄 上传目录文件数: {len(upload_files)}")
    if upload_files:
        print(f"   文件列表: {', '.join(upload_files[:5])}{'...' if len(upload_files) > 5 else ''}")
    
    # 检查Kimi API配置
    if not config.KIMI_API_KEY:
        print("⚠️ 警告: KIMI_API_KEY 未设置，对话功能将无法使用")
    else:
        print("✅ Kimi API 已配置")
    
    print("=" * 50)
    print(f"✨ 服务启动成功！访问: http://{config.HOST}:{config.PORT}")
    print("=" * 50)
    
    yield
    
    # 关闭时执行
    print("👋 服务正在关闭...")
    
    # 保存FAISS索引
    try:
        from app.core.faiss_retriever import get_retriever
        retriever = get_retriever()
        retriever.save_index()
        print("💾 FAISS索引已保存")
    except Exception as e:
        print(f"⚠️ 保存FAISS索引失败: {str(e)}")


# 创建FastAPI应用
app = FastAPI(
    title="AI论文小助手 API",
    description="智能文献管理、RAG对话、综述生成、图表生成",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(api_router)

# 静态文件服务（前端文件）
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

# 静态文件服务（图表文件）
if os.path.exists(config.CHART_DIR):
    app.mount("/static/charts", StaticFiles(directory=config.CHART_DIR), name="charts")


@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径 - 返回前端界面"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "app.html")
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found</h1>")


def get_frontend_html() -> str:
    """返回前端HTML内容（备用）"""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI论文小助手</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }
        
        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        
        .feature-card {
            background: white;
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            transition: transform 0.3s, box-shadow 0.3s;
            cursor: pointer;
        }
        
        .feature-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .feature-icon {
            font-size: 48px;
            margin-bottom: 16px;
        }
        
        .feature-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 8px;
            color: #333;
        }
        
        .feature-desc {
            color: #666;
            line-height: 1.6;
        }
        
        .upload-section {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
        }
        
        .upload-zone {
            border: 3px dashed #d9d9d9;
            border-radius: 12px;
            padding: 60px 40px;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .upload-zone:hover {
            border-color: #1890ff;
            background: #f6ffed;
        }
        
        .upload-zone.dragover {
            border-color: #52c41a;
            background: #f6ffed;
        }
        
        .upload-icon {
            font-size: 64px;
            margin-bottom: 16px;
        }
        
        .upload-text {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 8px;
        }
        
        .upload-hint {
            color: #999;
            font-size: 0.9em;
        }
        
        .btn {
            display: inline-block;
            padding: 12px 32px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            margin: 8px;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        
        .file-list {
            margin-top: 24px;
            text-align: left;
        }
        
        .file-item {
            display: flex;
            align-items: center;
            padding: 16px;
            background: #f6ffed;
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 4px solid #52c41a;
        }
        
        .file-icon {
            font-size: 24px;
            margin-right: 12px;
        }
        
        .file-info {
            flex: 1;
        }
        
        .file-name {
            font-weight: 500;
            margin-bottom: 4px;
        }
        
        .file-meta {
            font-size: 0.85em;
            color: #666;
        }
        
        .file-status {
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 500;
        }
        
        .status-done {
            background: #f6ffed;
            color: #52c41a;
        }
        
        .status-processing {
            background: #e6f7ff;
            color: #1890ff;
        }
        
        .chat-section {
            background: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-top: 24px;
        }
        
        .chat-messages {
            height: 300px;
            overflow-y: auto;
            padding: 16px;
            background: #f5f5f5;
            border-radius: 8px;
            margin-bottom: 16px;
        }
        
        .message {
            display: flex;
            gap: 12px;
            margin-bottom: 16px;
        }
        
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            flex-shrink: 0;
        }
        
        .message.user .message-avatar {
            background: #e6f7ff;
        }
        
        .message.assistant .message-avatar {
            background: #f6ffed;
        }
        
        .message-content {
            flex: 1;
            background: white;
            padding: 12px 16px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .chat-input-area {
            display: flex;
            gap: 12px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #d9d9d9;
            border-radius: 8px;
            font-size: 16px;
            outline: none;
            transition: border-color 0.3s;
        }
        
        .chat-input:focus {
            border-color: #1890ff;
        }
        
        .hidden {
            display: none;
        }
        
        .section-title {
            font-size: 1.5em;
            font-weight: 600;
            margin-bottom: 20px;
            color: #333;
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2em;
            }
            .features {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🤖 AI论文小助手</h1>
            <p>智能文献管理 · RAG对话 · 综述生成 · 图表可视化</p>
        </div>
        
        <!-- 功能卡片 -->
        <div class="features">
            <div class="feature-card" onclick="showSection(\'upload\')">
                <div class="feature-icon">📚</div>
                <div class="feature-title">文献管理</div>
                <div class="feature-desc">上传PDF论文，自动解析内容并建立向量索引，支持批量导入和智能检索</div>
            </div>
            <div class="feature-card" onclick="showSection(\'chat\')">
                <div class="feature-icon">💬</div>
                <div class="feature-title">智能对话</div>
                <div class="feature-desc">基于RAG技术与文献对话，精准回答论文相关问题，支持多轮对话和溯源</div>
            </div>
            <div class="feature-card" onclick="showSection(\'review\')">
                <div class="feature-icon">📝</div>
                <div class="feature-title">综述生成</div>
                <div class="feature-desc">自动分析多篇文献，生成结构化学术综述，包含背景、方法、结论等章节</div>
            </div>
            <div class="feature-card" onclick="showSection(\'chart\')">
                <div class="feature-icon">📊</div>
                <div class="feature-title">图表生成</div>
                <div class="feature-desc">导入Excel/CSV数据，灵活配置生成折线图、柱状图、散点图等可视化图表</div>
            </div>
        </div>
        
        <!-- 上传区域 -->
        <div id="upload-section" class="upload-section">
            <h2 class="section-title">📤 上传文献</h2>
            <div class="upload-zone" id="upload-zone">
                <div class="upload-icon">📁</div>
                <div class="upload-text">点击或拖拽PDF文件到此处上传</div>
                <div class="upload-hint">支持批量上传，单个文件不超过50MB</div>
            </div>
            <input type="file" id="file-input" multiple accept=".pdf" style="display:none">
            
            <div class="file-list" id="file-list">
                <div class="file-item">
                    <span class="file-icon">📄</span>
                    <div class="file-info">
                        <div class="file-name">示例论文：深度学习在医学影像中的应用研究.pdf</div>
                        <div class="file-meta">12页 · 上传于 2024-01-15</div>
                    </div>
                    <span class="file-status status-done">✓ 已处理</span>
                </div>
            </div>
        </div>
        
        <!-- 对话区域 -->
        <div id="chat-section" class="chat-section hidden">
            <h2 class="section-title">💬 智能对话</h2>
            <div class="chat-messages" id="chat-messages">
                <div class="message assistant">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">
                        您好！我是您的AI论文助手。我已读取您上传的文献，可以帮您解答问题、总结观点、对比研究方法。请问有什么可以帮助您的？
                    </div>
                </div>
            </div>
            <div class="chat-input-area">
                <input type="text" class="chat-input" id="chat-input" placeholder="输入您的问题，例如：请总结这篇论文的创新点...">
                <button class="btn btn-primary" onclick="sendMessage()">发送</button>
            </div>
        </div>
        
        <!-- 综述生成区域 -->
        <div id="review-section" class="upload-section hidden" style="margin-top: 24px;">
            <h2 class="section-title">📝 生成文献综述</h2>
            <p style="margin-bottom: 16px; color: #666;">AI将自动分析您的文献，生成包含引言、研究现状、方法对比、结论展望的完整综述</p>
            <button class="btn btn-primary" onclick="generateReview()">✨ 开始生成综述</button>
            <div id="review-output" style="margin-top: 24px; padding: 20px; background: #f6ffed; border-radius: 8px; text-align: left; display: none;"></div>
        </div>
        
        <!-- 图表生成区域 -->
        <div id="chart-section" class="upload-section hidden" style="margin-top: 24px;">
            <h2 class="section-title">📊 图表生成</h2>
            <div class="upload-zone" id="data-upload-zone">
                <div class="upload-icon">📊</div>
                <div class="upload-text">点击或拖拽Excel/CSV文件到此处</div>
                <div class="upload-hint">支持 .xlsx, .xls, .csv 格式</div>
            </div>
            <input type="file" id="data-input" accept=".csv,.xlsx,.xls" style="display:none">
        </div>
    </div>
    
    <script>
        // API基础URL
        const API_BASE = window.location.origin + '/api';
        let currentSessionId = null;
        
        // ========== 文件上传功能 ==========
        const uploadZone = document.getElementById('upload-zone');
        const fileInput = document.getElementById('file-input');
        
        uploadZone.addEventListener('click', () => fileInput.click());
        
        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });
        
        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });
        
        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });
        
        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });
        
        async function handleFiles(files) {
            if (files.length === 0) return;
            
            const formData = new FormData();
            for (let file of files) {
                if (file.name.endsWith('.pdf')) {
                    formData.append('files', file);
                }
            }
            
            try {
                uploadZone.innerHTML = '<div class="upload-icon">⏳</div><div class="upload-text">正在上传...</div>';
                
                const response = await fetch(`${API_BASE}/papers/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.code === 200) {
                    const count = result.data.uploaded ? result.data.uploaded.length : 0;
                    alert('上传成功！已处理 ' + count + ' 个文件');
                    loadPaperList();
                } else {
                    alert('上传失败：' + result.message);
                }
            } catch (error) {
                alert('上传出错：' + error.message);
            } finally {
                uploadZone.innerHTML = '<div class="upload-icon">📁</div><div class="upload-text">点击或拖拽PDF文件到此处上传</div><div class="upload-hint">支持批量上传，单个文件不超过50MB</div>';
            }
        }
        
        // 加载文献列表
        async function loadPaperList() {
            try {
                const response = await fetch(`${API_BASE}/papers`);
                const result = await response.json();
                
                if (result.code === 200) {
                    const fileList = document.getElementById('file-list');
                    if (result.data.items.length === 0) {
                        fileList.innerHTML = '<p style="color:#999;text-align:center;padding:20px;">暂无文献，请先上传</p>';
                        return;
                    }
                    
                    fileList.innerHTML = result.data.items.map(paper => `
                        <div class="file-item">
                            <span class="file-icon">📄</span>
                            <div class="file-info">
                                <div class="file-name">${paper.title || paper.file_name}</div>
                                <div class="file-meta">${paper.page_count || 0}页 · ${paper.status === 'active' ? '已处理' : '处理中'}</div>
                            </div>
                            <span class="file-status ${paper.status === 'active' ? 'status-done' : 'status-processing'}">
                                ${paper.status === 'active' ? '✓ 已处理' : '⏳ 处理中'}
                            </span>
                        </div>
                    `).join('');
                }
            } catch (error) {
                console.error('加载文献列表失败:', error);
            }
        }
        
        // ========== 对话功能 ==========
        async function createSession() {
            try {
                const response = await fetch(`${API_BASE}/chat/sessions`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({session_name: '新对话'})
                });
                const result = await response.json();
                if (result.code === 200) {
                    currentSessionId = result.data.id;
                }
            } catch (error) {
                console.error('创建会话失败:', error);
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('chat-input');
            const message = input.value.trim();
            if (!message) return;
            
            if (!currentSessionId) {
                await createSession();
            }
            
            const messagesDiv = document.getElementById('chat-messages');
            
            // 添加用户消息
            messagesDiv.innerHTML += `
                <div class="message user">
                    <div class="message-avatar">👤</div>
                    <div class="message-content">${message}</div>
                </div>
            `;
            
            input.value = '';
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            // 添加AI回复占位
            const aiMessageId = 'ai-' + Date.now();
            messagesDiv.innerHTML += `
                <div class="message assistant" id="${aiMessageId}">
                    <div class="message-avatar">🤖</div>
                    <div class="message-content">思考中...</div>
                </div>
            `;
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            try {
                const response = await fetch(`${API_BASE}/chat/messages`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        session_id: currentSessionId,
                        message: message
                    })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let aiResponse = '';
                
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'content') {
                                    aiResponse += data.data;
                                    document.querySelector(`#${aiMessageId} .message-content`).textContent = aiResponse;
                                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (error) {
                document.querySelector(`#${aiMessageId} .message-content`).textContent = '抱歉，发生了错误：' + error.message;
            }
        }
        
        // ========== 综述生成功能 ==========
        async function generateReview() {
            const output = document.getElementById('review-output');
            output.style.display = 'block';
            output.innerHTML = '<p>⏳ 正在生成综述，请稍候...</p>';
            
            try {
                const response = await fetch(`${API_BASE}/review/generate`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        topic: '文献综述',
                        word_count: 2000,
                        language: 'zh'
                    })
                });
                
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let reviewText = '';
                
                while (true) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'content') {
                                    reviewText += data.data;
                                    output.innerHTML = reviewText.replace(/\\n/g, '<br>');
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (error) {
                output.innerHTML = '<p style="color:red">生成失败：' + error.message + '</p>';
            }
        }
        
        // ========== 图表生成功能 ==========
        const dataUploadZone = document.getElementById('data-upload-zone');
        const dataInput = document.getElementById('data-input');
        
        dataUploadZone.addEventListener('click', () => dataInput.click());
        
        dataInput.addEventListener('change', async (e) => {
            if (e.target.files.length === 0) return;
            
            const formData = new FormData();
            formData.append('file', e.target.files[0]);
            
            try {
                dataUploadZone.innerHTML = '<div class="upload-icon">⏳</div><div class="upload-text">正在上传数据...</div>';
                
                const response = await fetch(`${API_BASE}/charts/datasets/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.code === 200) {
                    alert(`数据上传成功！包含 ${result.data.row_count} 行数据`);
                    showChartConfig(result.data);
                } else {
                    alert('上传失败：' + result.message);
                }
            } catch (error) {
                alert('上传出错：' + error.message);
            }
        });
        
        function showChartConfig(dataset) {
            const chartSection = document.getElementById('chart-section');
            const columnOptions = dataset.columns.map(c => `<option value="${c.name}">${c.name} (${c.type})</option>`).join('');
            
            chartSection.innerHTML += `
                <div style="margin-top:24px;text-align:left;">
                    <h3>图表配置</h3>
                    <div style="margin:12px 0;">
                        <label>图表类型：</label>
                        <select id="chart-type">
                            <option value="line">折线图</option>
                            <option value="bar">柱状图</option>
                            <option value="scatter">散点图</option>
                        </select>
                    </div>
                    <div style="margin:12px 0;">
                        <label>X轴：</label>
                        <select id="x-column">${columnOptions}</select>
                    </div>
                    <div style="margin:12px 0;">
                        <label>Y轴：</label>
                        <select id="y-column">${columnOptions}</select>
                    </div>
                    <button class="btn btn-primary" onclick="generateChart(${dataset.id})">生成图表</button>
                    <div id="chart-result" style="margin-top:16px;"></div>
                </div>
            `;
        }
        
        async function generateChart(datasetId) {
            const chartType = document.getElementById('chart-type').value;
            const xColumn = document.getElementById('x-column').value;
            const yColumn = document.getElementById('y-column').value;
            
            try {
                const response = await fetch(`${API_BASE}/charts/generate`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        dataset_id: datasetId,
                        chart_type: chartType,
                        x_column: xColumn,
                        y_column: yColumn
                    })
                });
                
                const result = await response.json();
                
                if (result.code === 200) {
                    document.getElementById('chart-result').innerHTML = `
                        <img src="${result.data.chart_base64}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.1);">
                    `;
                } else {
                    alert('生成图表失败：' + result.message);
                }
            } catch (error) {
                alert('生成图表出错：' + error.message);
            }
        }
        
        // ========== 页面切换 ==========
        function showSection(section) {
            document.getElementById('upload-section').classList.add('hidden');
            document.getElementById('chat-section').classList.add('hidden');
            document.getElementById('review-section').classList.add('hidden');
            document.getElementById('chart-section').classList.add('hidden');
            
            if (section === 'upload') {
                document.getElementById('upload-section').classList.remove('hidden');
                loadPaperList();
            } else if (section === 'chat') {
                document.getElementById('chat-section').classList.remove('hidden');
            } else if (section === 'review') {
                document.getElementById('review-section').classList.remove('hidden');
            } else if (section === 'chart') {
                document.getElementById('chart-section').classList.remove('hidden');
            }
        }
        
        // 回车发送消息
        document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        // 页面加载时获取文献列表
        loadPaperList();
    </script>
</body>
</html>
'''


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "database": "connected",
        "timestamp": "2024"
    }


@app.get("/api/stats")
async def get_stats(get_retriever=None):
    """获取系统统计信息"""
    from app.core.faiss_retriever import get_retriever
    from app.models.database import SessionLocal, Paper, ChatSession, Dataset
    
    db = SessionLocal()
    try:
        paper_count = db.query(Paper).filter(Paper.status == "active").count()
        session_count = db.query(ChatSession).count()
        dataset_count = db.query(Dataset).count()
        
        retriever = get_retriever()
        vector_stats = retriever.get_stats()
        
        return {
            "status": "success",
            "data": {
                "papers": {
                    "total": paper_count,
                    "status": "active"
                },
                "chat_sessions": session_count,
                "datasets": dataset_count,
                "vectors": vector_stats
            }
        }
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info" if config.DEBUG else "warning"
    )
