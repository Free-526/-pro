"""
Pydantic模型定义 - 用于API请求/响应验证
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ========== 通用响应模型 ==========

class ResponseModel(BaseModel):
    """通用响应模型"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None


class ListResponse(BaseModel):
    """列表响应模型"""
    total: int
    items: List[Any]


# ========== 文献相关模型 ==========

class PaperBase(BaseModel):
    """文献基础模型"""
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None


class PaperCreate(PaperBase):
    """创建文献模型"""
    file_name: str
    file_path: str
    file_size: Optional[int] = None


class PaperResponse(PaperBase):
    """文献响应模型"""
    id: int
    file_name: str
    upload_time: datetime
    page_count: Optional[int] = None
    chunk_count: int = 0
    status: str
    
    class Config:
        from_attributes = True


class PaperListResponse(BaseModel):
    """文献列表响应"""
    total: int
    items: List[PaperResponse]


# ========== 对话相关模型 ==========

class ChatSessionBase(BaseModel):
    """对话会话基础模型"""
    session_name: Optional[str] = "新会话"


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    """对话会话响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    """消息基础模型"""
    role: str
    content: str


class ChatMessageCreate(BaseModel):
    """创建消息模型"""
    session_id: int
    message: str
    paper_ids: Optional[List[int]] = None


class ChatMessageResponse(ChatMessageBase):
    """消息响应模型"""
    id: int
    session_id: int
    references: Optional[List[Dict]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    """对话历史响应"""
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]


# ========== 综述相关模型 ==========

class ReviewGenerateRequest(BaseModel):
    """综述生成请求"""
    topic: str = Field(..., description="综述主题")
    paper_ids: Optional[List[int]] = Field(None, description="指定文献ID列表，None表示使用全部")
    word_count: int = Field(3000, ge=500, le=10000, description="字数要求")
    language: str = Field("zh", description="输出语言: zh/en")
    structure: str = Field("standard", description="结构类型: standard/custom")


class ReviewExportRequest(BaseModel):
    """综述导出请求"""
    content: str
    format: str = Field("pdf", description="导出格式: pdf/docx/markdown")


# ========== 图表相关模型 ==========

class DatasetResponse(BaseModel):
    """数据集响应模型"""
    id: int
    file_name: str
    file_type: str
    sheet_name: Optional[str] = None
    columns: List[Dict[str, Any]]
    row_count: int
    upload_time: datetime
    
    class Config:
        from_attributes = True


class ChartGenerateRequest(BaseModel):
    """图表生成请求"""
    dataset_id: int
    chart_type: str = Field(..., description="图表类型: line/bar/scatter/pie")
    x_column: str
    y_column: str
    x_range: Optional[List[float]] = None
    y_range: Optional[List[float]] = None
    filter_config: Optional[Dict] = None
    style: Optional[Dict] = Field(default_factory=dict)


class ChartResponse(BaseModel):
    """图表响应模型"""
    chart_url: str
    chart_data: Dict[str, Any]


class ColumnInfo(BaseModel):
    """列信息"""
    name: str
    type: str  # int, float, str, datetime


# ========== 用户相关模型 ==========

class UserBase(BaseModel):
    """用户基础模型"""
    username: str
    email: str


class UserCreate(BaseModel):
    """用户注册模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserInfo(BaseModel):
    """当前用户信息"""
    id: int
    username: str
    email: str


# ========== 智能体相关模型 ==========

class ChatRequest(BaseModel):
    """聊天请求模型"""
    session_id: int
    query: str
    paper_ids: Optional[List[int]] = None
    chat_history: Optional[List[Dict]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    references: Optional[List[Dict]] = None


class AgentRequest(BaseModel):
    """智能体请求模型"""
    query: str
    user_id: Optional[str] = None


class AgentResponse(BaseModel):
    """智能体响应模型"""
    response: str
    tasks: Optional[List[Dict]] = None
    results: Optional[Dict[str, Any]] = None