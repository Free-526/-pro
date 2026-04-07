"""
API路由模块
"""
from fastapi import APIRouter

from .papers import router as papers_router
from .chat import router as chat_router
from .review import router as review_router
from .charts import router as charts_router
from .auth import router as auth_router
from .analytics import router as analytics_router


# 创建主路由
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(auth_router, prefix="/auth", tags=["用户认证"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["数据埋点"])
api_router.include_router(papers_router, prefix="/papers", tags=["文献管理"])
api_router.include_router(chat_router, prefix="/chat", tags=["对话问答"])
api_router.include_router(review_router, prefix="/review", tags=["综述生成"])
api_router.include_router(charts_router, prefix="/charts", tags=["图表生成"])
