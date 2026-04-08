"""
数据埋点核心模块
提供用户行为追踪、性能监控和业务指标统计功能
"""
from datetime import datetime
from typing import Optional, Dict, Any
import json

from sqlalchemy.orm import Session

from app.models.database import EventLog, PerformanceLog, BusinessMetric


class Tracker:
    """埋点追踪器"""
    
    @staticmethod
    def track_event(
        db: Session,
        event_name: str,
        user_id: Optional[int] = None,
        event_type: str = "click",
        page_path: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None
    ):
        """记录用户行为事件"""
        event = EventLog(
            user_id=user_id,
            event_name=event_name,
            event_type=event_type,
            page_path=page_path,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            properties=json.dumps(properties, ensure_ascii=False) if properties else None
        )
        db.add(event)
        db.commit()
    
    @staticmethod
    def track_performance(
        db: Session,
        operation: str,
        duration_ms: int,
        user_id: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        resource_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """记录性能数据"""
        perf = PerformanceLog(
            user_id=user_id,
            operation=operation,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            resource_size=resource_size,
            meta_data=json.dumps(metadata, ensure_ascii=False) if metadata else None
        )
        db.add(perf)
        db.commit()
    
    @staticmethod
    def increment_metric(
        db: Session,
        user_id: int,
        metric_type: str,
        increment: int = 1,
        date: Optional[str] = None
    ):
        """增加业务指标计数"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        # 查找或创建记录
        metric = db.query(BusinessMetric).filter(
            BusinessMetric.user_id == user_id,
            BusinessMetric.metric_date == date,
            BusinessMetric.metric_type == metric_type
        ).first()
        
        if metric:
            metric.metric_value += increment
        else:
            metric = BusinessMetric(
                user_id=user_id,
                metric_date=date,
                metric_type=metric_type,
                metric_value=increment
            )
            db.add(metric)
        
        db.commit()
    
    @staticmethod
    def get_user_daily_metric(
        db: Session,
        user_id: int,
        metric_type: str,
        date: Optional[str] = None
    ) -> int:
        """获取用户当日指标值"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        metric = db.query(BusinessMetric).filter(
            BusinessMetric.user_id == user_id,
            BusinessMetric.metric_date == date,
            BusinessMetric.metric_type == metric_type
        ).first()
        
        return metric.metric_value if metric else 0


# 便捷函数
def track_event(db: Session, event_name: str, **kwargs):
    """快捷记录事件"""
    Tracker.track_event(db, event_name, **kwargs)


def track_performance(db: Session, operation: str, duration_ms: int, **kwargs):
    """快捷记录性能"""
    Tracker.track_performance(db, operation, duration_ms, **kwargs)


def increment_user_metric(db: Session, user_id: int, metric_type: str, increment: int = 1):
    """快捷增加用户指标"""
    Tracker.increment_metric(db, user_id, metric_type, increment)
