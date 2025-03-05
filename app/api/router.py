from fastapi import APIRouter

from app.api.routes import heartbeat

api_router = APIRouter()
api_router.include_router(heartbeat.router, tags=["health"])
