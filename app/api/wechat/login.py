"""
微信小程序登录接口模块

【关键业务规则】
1. 登录验证顺序：
   - 第一步：查询 auth_user 表（Django 内置员工用户表），用 Django 密码算法
   - 第二步：如果第一步没找到，查询 warehouse_customer 表（客户用户），用 Django 密码算法

2. Token 生成：
   - 生成 JWT token，包含用户名、显示名称、用户类型
   - 用户类型用于后续权限判断（staff 可查看所有柜号，customer 只能查看自己的）
"""
import jwt
import logging
from typing import Any, Type

from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi.concurrency import run_in_threadpool

from app.data_models.db.user import Customer, AuthUser
from app.data_models.login import LoginRequest, UserAuth
from app.services.config import app_config
from app.services.db_session import db_session

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"], deprecated="auto")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError) as e:
        logger.error(f"Password verify error: {str(e)}")
        return False


def _query_user_sync(db: Session, model: Type[Any], attr: str, value: str):
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
    第一步：查 auth_user 表（Django 员工用户）
    第二步：查 warehouse_customer 表（客户用户）
    """
    if not request.username or not request.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required",
        )
    username = request.username.strip()
    password = request.password

    # 第一步：查询 AuthUser 表（Django 内置员工用户表）
    try:
        auth_user = await run_in_threadpool(_query_user_sync, db, AuthUser, "username", username)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"AuthUser query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )

    if auth_user:
        if not getattr(auth_user, "is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is disabled / 账户已禁用",
            )
        if _verify_password(password, auth_user.password):
            display_name = f"{auth_user.first_name} {auth_user.last_name}".strip() or auth_user.username
            token = jwt.encode(
                {
                    "user_name": auth_user.username,
                    "display_name": display_name,
                    "user_type": "staff",
                },
                app_config.SECRET_KEY,
                algorithm=app_config.JWT_ALGO,
            )
            return UserAuth(
                user=display_name,
                access_token=token,
                user_type="staff",
            )

    # 第二步：查询 Customer 表（客户用户）
    try:
        customer = await run_in_threadpool(_query_user_sync, db, Customer, "username", username)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Customer query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable",
        )

    if customer:
        if _verify_password(password, customer.password):
            display_name = customer.full_name or customer.zem_name
            token = jwt.encode(
                {
                    "user_name": customer.username or customer.zem_name,
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

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found / 用户不存在",
    )
