from fastapi import APIRouter

from app.api import heartbeat, login, order_tracking

api_router = APIRouter()
api_router.include_router(heartbeat.router, tags=["health"])
api_router.include_router(login.router, tags=["login"])
api_router.include_router(order_tracking.router, tags=["order_tracking"])
