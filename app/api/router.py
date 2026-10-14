"""
KCapTrack — Main API Router.

Combines all modular sub-routers under the `/api/v1` prefix:
  • /api/v1/users       (Registration, login, biometric profile CRUD)
  • /api/v1/meals       (YOLO meal image scanning & historical logs)
  • /api/v1/dashboard   (Daily nutrition progress vs. biometric targets)
"""

from fastapi import APIRouter

from app.api.endpoints import dashboard, meals, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(users.router)
api_router.include_router(meals.router)
api_router.include_router(dashboard.router)
