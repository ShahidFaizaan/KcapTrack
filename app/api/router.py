from fastapi import APIRouter

from app.api.endpoints import dashboard, meals, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users.router)
api_router.include_router(meals.router)
api_router.include_router(dashboard.router)
