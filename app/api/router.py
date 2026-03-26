from fastapi import APIRouter

from app.api import heartbeat, login, order_tracking,order_tracking_date

api_router = APIRouter()
api_router.include_router(heartbeat.router, tags=["health"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(order_tracking.router, tags=["order_tracking"])
api_router.include_router(order_tracking_date.router, tags=["order_tracking_date"])