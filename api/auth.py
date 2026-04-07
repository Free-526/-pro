"""
用户认证API路由
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import get_db, User
from app.models.schemas import ResponseModel, UserCreate, UserLogin, TokenResponse, UserResponse
from app.core.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    get_current_user,
    create_default_admin
)
from app.core.analytics import Tracker

router = APIRouter()


@router.post("/register", response_model=ResponseModel)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    用户注册
    
    - **username**: 用户名（3-50字符）
    - **email**: 邮箱地址
    - **password**: 密码（至少6位）
    """
    # 检查用户名是否已存在
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已被注册"
        )
    
    # 检查邮箱是否已存在
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        is_active=1
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 记录注册事件
    Tracker.track_event(
        db=db,
        user_id=new_user.id,
        event_name="user_register",
        event_type="auth",
        properties={"username": new_user.username, "email": new_user.email}
    )
    
    # 增加用户注册计数
    Tracker.increment_metric(db, new_user.id, "user_count")
    
    return ResponseModel(
        code=200,
        message="注册成功",
        data={
            "id": new_user.id,
            "username": new_user.username,
            "email": new_user.email
        }
    )


@router.post("/login", response_model=ResponseModel)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    
    返回 JWT Token，用于后续请求的认证
    """
    # 查找用户
    user = db.query(User).filter(User.username == login_data.username).first()
    
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 更新最后登录时间
    user.last_login = datetime.now()
    db.commit()
    
    # 记录登录事件
    Tracker.track_event(
        db=db,
        user_id=user.id,
        event_name="user_login",
        event_type="auth",
        properties={"username": user.username}
    )
    
    # 创建 JWT Token
    access_token = create_access_token(data={"user_id": user.id, "username": user.username})
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "created_at": user.created_at
            }
        }
    )


@router.get("/me", response_model=ResponseModel)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    需要在请求头中携带 Bearer Token
    """
    return ResponseModel(
        code=200,
        data={
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "created_at": current_user.created_at,
            "last_login": current_user.last_login
        }
    )


@router.post("/logout", response_model=ResponseModel)
async def logout():
    """
    用户登出
    客户端需要清除保存的 Token
    """
    return ResponseModel(code=200, message="登出成功")


@router.post("/init-admin")
async def init_admin(db: Session = Depends(get_db)):
    """
    初始化默认管理员账号
    仅在数据库为空时可用
    """
    # 检查是否已有用户
    user_count = db.query(User).count()
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员账号已存在"
        )
    
    create_default_admin(db)
    
    return ResponseModel(
        code=200,
        message="默认管理员账号已创建",
        data={"username": "admin", "password": "admin123"}
    )
