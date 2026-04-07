"""
埋点数据API
接收前端埋点数据，提供数据看板接口
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.models.database import get_db, User, EventLog, PerformanceLog, BusinessMetric
from app.core.auth import get_current_user, get_optional_user
from app.core.analytics import Tracker

router = APIRouter()


class TrackEventRequest(BaseModel):
    """前端埋点请求"""
    event_name: str
    event_type: str = "click"
    page_path: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class TrackPerformanceRequest(BaseModel):
    """性能数据上报请求"""
    operation: str
    duration_ms: int
    status: str = "success"
    metadata: Optional[Dict[str, Any]] = None


@router.post("/track/event")
async def track_event_endpoint(
    request: TrackEventRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    接收前端埋点事件
    
    前端在关键操作时调用此接口上报数据
    """
    # 获取客户端信息
    ip_address = http_request.client.host if http_request.client else None
    user_agent = http_request.headers.get("user-agent")
    session_id = http_request.headers.get("x-session-id")
    
    Tracker.track_event(
        db=db,
        event_name=request.event_name,
        user_id=current_user.id if current_user else None,
        event_type=request.event_type,
        page_path=request.page_path,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        properties=request.properties
    )
    
    return {"code": 200, "message": "事件记录成功"}


@router.post("/track/performance")
async def track_performance_endpoint(
    request: TrackPerformanceRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    接收性能数据上报
    
    用于监控前端性能或后端异步任务性能
    """
    Tracker.track_performance(
        db=db,
        operation=request.operation,
        duration_ms=request.duration_ms,
        user_id=current_user.id if current_user else None,
        status=request.status,
        metadata=request.metadata
    )
    
    return {"code": 200, "message": "性能数据记录成功"}


@router.get("/dashboard")
async def get_dashboard(
    days: int = 7,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取数据看板（仅管理员）
    
    - days: 统计天数，默认7天
    """
    # 检查是否为管理员（这里简化处理，实际应该检查用户角色）
    if current_user.username != "admin":
        return {"code": 403, "message": "无权访问"}
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 1. 用户增长统计
    new_users = db.query(func.count(User.id)).filter(
        User.created_at >= start_date
    ).scalar()
    
    # 2. 活跃用户数（有事件记录的用户）
    active_users = db.query(func.count(func.distinct(EventLog.user_id))).filter(
        EventLog.created_at >= start_date
    ).scalar()
    
    # 3. 核心事件统计
    event_stats = db.query(
        EventLog.event_name,
        func.count(EventLog.id).label("count")
    ).filter(
        EventLog.created_at >= start_date
    ).group_by(EventLog.event_name).all()
    
    # 4. 性能统计
    perf_stats = db.query(
        PerformanceLog.operation,
        func.avg(PerformanceLog.duration_ms).label("avg_duration"),
        func.count(PerformanceLog.id).label("count")
    ).filter(
        PerformanceLog.created_at >= start_date
    ).group_by(PerformanceLog.operation).all()
    
    # 5. 业务指标汇总
    today = datetime.now().strftime("%Y-%m-%d")
    business_stats = db.query(
        BusinessMetric.metric_type,
        func.sum(BusinessMetric.metric_value).label("total")
    ).filter(
        BusinessMetric.metric_date >= start_date.strftime("%Y-%m-%d")
    ).group_by(BusinessMetric.metric_type).all()
    
    return {
        "code": 200,
        "data": {
            "period": f"{start_date.date()} 至 {datetime.now().date()}",
            "user_stats": {
                "new_users": new_users,
                "active_users": active_users
            },
            "event_stats": [{"event": e.event_name, "count": e.count} for e in event_stats],
            "performance_stats": [
                {
                    "operation": p.operation,
                    "avg_duration_ms": round(p.avg_duration, 2),
                    "count": p.count
                } for p in perf_stats
            ],
            "business_stats": [{"type": b.metric_type, "total": int(b.total)} for b in business_stats]
        }
    }


@router.get("/metrics/daily")
async def get_daily_metrics(
    metric_type: str,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取每日指标趋势
    
    - metric_type: 指标类型（chat_count/upload_count/review_count等）
    - days: 查询天数
    """
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    metrics = db.query(BusinessMetric).filter(
        BusinessMetric.user_id == current_user.id,
        BusinessMetric.metric_type == metric_type,
        BusinessMetric.metric_date >= start_date
    ).order_by(BusinessMetric.metric_date).all()
    
    return {
        "code": 200,
        "data": {
            "metric_type": metric_type,
            "daily_data": [
                {"date": m.metric_date, "value": m.metric_value}
                for m in metrics
            ]
        }
    }


@router.get("/usage/limit")
async def check_usage_limit(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    检查用户使用额度（用于前端展示和限流）
    
    返回今日各项使用指标
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 查询各项指标
    chat_count = Tracker.get_user_daily_metric(db, current_user.id, "chat_count", today)
    upload_count = Tracker.get_user_daily_metric(db, current_user.id, "upload_count", today)
    review_count = Tracker.get_user_daily_metric(db, current_user.id, "review_count", today)
    chart_count = Tracker.get_user_daily_metric(db, current_user.id, "chart_count", today)
    
    # 免费版限制（可根据实际情况调整）
    limits = {
        "chat_count": {"used": chat_count, "limit": 50, "unit": "次"},
        "upload_count": {"used": upload_count, "limit": 10, "unit": "篇"},
        "review_count": {"used": review_count, "limit": 3, "unit": "次"},
        "chart_count": {"used": chart_count, "limit": 10, "unit": "张"}
    }
    
    return {
        "code": 200,
        "data": {
            "date": today,
            "limits": limits,
            "is_limit_exceeded": any(
                v["used"] >= v["limit"] for v in limits.values()
            )
        }
    }
