"""
数据库模型定义
使用SQLAlchemy ORM
"""
import json
from datetime import datetime
from typing import Generator, List, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, event, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.sql import func

from app.config import config

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)  # 1=激活, 0=禁用
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime)
    
    # 关系
    papers = relationship("Paper", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    datasets = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")


class Paper(Base):
    """文献表"""
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    title = Column(String(500))
    authors = Column(Text)  # JSON格式
    abstract = Column(Text)
    keywords = Column(Text)  # JSON格式
    upload_time = Column(DateTime, default=datetime.now)
    page_count = Column(Integer)
    chunk_count = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active, processing, deleted
    
    # 联合唯一约束：同一用户的文件路径唯一
    __table_args__ = (
        UniqueConstraint('user_id', 'file_path', name='uix_user_file_path'),
    )
    
    # 关系
    user = relationship("User", back_populates="papers")
    chunks = relationship("Chunk", back_populates="paper", cascade="all, delete-orphan")


class Chunk(Base):
    """文本块表"""
    __tablename__ = "chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    faiss_id = Column(Integer)  # FAISS中的向量ID
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    paper = relationship("Paper", back_populates="chunks")


class ChatSession(Base):
    """对话会话表"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_name = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """对话消息表"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    references = Column(Text)  # JSON格式，引用文献信息
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    session = relationship("ChatSession", back_populates="messages")


class Dataset(Base):
    """数据集表"""
    __tablename__ = "datasets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # excel, csv
    sheet_name = Column(String(100))  # Excel的sheet名
    columns = Column(Text)  # JSON格式
    row_count = Column(Integer)
    upload_time = Column(DateTime, default=datetime.now)
    
    # 关系
    user = relationship("User", back_populates="datasets")
    charts = relationship("ChartConfig", back_populates="dataset", cascade="all, delete-orphan")


class ChartConfig(Base):
    """图表配置表"""
    __tablename__ = "chart_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    chart_name = Column(String(200))
    chart_type = Column(String(20), nullable=False)  # line, bar, scatter, pie
    x_column = Column(String(100), nullable=False)
    y_column = Column(String(100), nullable=False)
    x_range = Column(Text)  # JSON格式
    y_range = Column(Text)  # JSON格式
    filter_config = Column(Text)  # JSON格式
    style_config = Column(Text)  # JSON格式
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    dataset = relationship("Dataset", back_populates="charts")


# ========== 埋点数据模型 ==========

class EventLog(Base):
    """用户行为事件表"""
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_name = Column(String(50), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # click/page/api/error
    page_path = Column(String(200))
    session_id = Column(String(100))
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    properties = Column(Text)  # JSON格式扩展字段
    created_at = Column(DateTime, default=datetime.now, index=True)


class PerformanceLog(Base):
    """性能监控表"""
    __tablename__ = "performance_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    operation = Column(String(50), nullable=False)  # 操作类型
    duration_ms = Column(Integer)  # 耗时（毫秒）
    status = Column(String(20))  # success/error/timeout
    error_message = Column(Text)
    resource_size = Column(Integer)  # 资源大小（字节）
    meta_data = Column(Text)  # JSON格式附加信息（原名metadata，避免保留字冲突）
    created_at = Column(DateTime, default=datetime.now)


class BusinessMetric(Base):
    """业务指标表（用于计费/限流）"""
    __tablename__ = "business_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    metric_type = Column(String(30), nullable=False)  # chat_count/token_count/upload_count
    metric_value = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 联合唯一约束
    __table_args__ = (
        UniqueConstraint('user_id', 'metric_date', 'metric_type', name='uix_user_metric'),
    )


# 创建数据库引擎
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=config.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """获取数据库会话的依赖函数（用于FastAPI Depends）"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """获取数据库会话（用于依赖注入）"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
