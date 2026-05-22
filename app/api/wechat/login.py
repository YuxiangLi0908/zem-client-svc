"""
微信小程序登录接口模块

【关键业务规则】
1. 登录验证顺序：
   - 第一步：查询 User 表（warehouse_customer，客户用户），用 Django 密码算法
   - 第二步：如果第一步没找到，用 zem-client-svc 原有的登录逻辑再查一次 User 表

2. Token 生成：
   - 生成 JWT token，包含用户名、显示名称、用户类型
   - 用户类型用于后续权限判断
"""
import jwt
import logging
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from app.data_models.db.user import User
from app.data_models.login import LoginRequest, UserAuth
from app.services.config import app_config
from app.services.db_session import db_session
from app.services.user_auth import authenticate_user

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
# 全局复用密码验证上下文
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """密码验证（兼容空密码/异常格式）"""
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        logger.error(f"Password verify error: {str(e)}")
        return False


def _query_user_sync(db: Session, model: Type[Any], attr: str, value: str):
    """同步查询用户"""
    try:
        column = getattr(model, attr)
        return db.query(model).filter(column == value).first()
    except AttributeError as e:
        logger.error(f"Model field error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Model {model.__name__} has no field: {attr}",
        )
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        )


@router.post("/login", response_model=UserAuth, name="wechat_login")
async def login(
    request: LoginRequest,
    db: Session = Depends(db_session.get_db)
) -> UserAuth:
    """
    微信小程序用户登录接口
    第一步：查 User 表（Django 密码算法）
    第二步：如果没找到，用 zem-client-svc 原有的登录逻辑再查一次
    """
    # 1. 基础参数校验
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )
    username = request.username.strip()
    password = request.password

    # 2. 第一步：查询 User 表（客户用户），用 Django 密码算法
    try:
        user = await run_in_threadpool(_query_user_sync, db, User, "username", username)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"User query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )

    if user:
        # 验证客户密码
        if _verify_password(password, user.password):
            # 生成 Token
            display_name = user.full_name or user.zem_name
            token = jwt.encode(
                {
                    "user_name": user.username or user.zem_name,
                    "display_name": display_name,
                    "user_type": "customer",
                },
                app_config.SECRET_KEY,
                algorithm=app_config.JWT_ALGO,
            )
            return UserAuth(
                user=display_name,
                access_token=token,
                user_type="customer",
            )

    # 3. 第二步：用 zem-client-svc 原有的登录逻辑再查一次 User 表
    try:
        # 调用 zem-client-svc 原有的认证函数
        user = await run_in_threadpool(authenticate_user, db, request)
    except HTTPException as e:
        # 如果原有的认证也失败了，继续下一步
        pass
    except Exception as e:
        logger.error(f"Zem client auth error: {str(e)}")
        # 继续下一步
    else:
        if user:
            # zem-client-svc 原有的认证成功
            display_name = user.full_name or user.zem_name
            token = jwt.encode(
                {
                    "user_name": user.username or user.zem_name,
                    "display_name": display_name,
                    "user_type": "customer",
                },
                app_config.SECRET_KEY,
                algorithm=app_config.JWT_ALGO,
            )
            return UserAuth(
                user=display_name,
                access_token=token,
                user_type="customer",
            )

    # 4. 都无该用户
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found / 用户不存在",
    )
