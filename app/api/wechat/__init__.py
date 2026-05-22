
"""
微信小程序API模块
"""
from fastapi import APIRouter
from app.api.wechat import order_tracking, table_query

router = APIRouter(prefix="/wechat", tags=["wechat"])

router.include_router(order_tracking.router)
router.include_router(table_query.router)

__all__ = ["router"]

