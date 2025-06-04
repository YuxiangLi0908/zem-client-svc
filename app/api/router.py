from fastapi import APIRouter

from app.api import heartbeat, login

api_router = APIRouter()
api_router.include_router(heartbeat.router, tags=["health"])
api_router.include_router(login.router, tags=["login"])
