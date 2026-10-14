"""
KCapTrack — Main FastAPI Application Entrypoint.

Vision-powered calorie and macronutrient tracking platform.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import engine, Base

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown events."""
    # Ensure uploads directory exists
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(parents=True, exist_ok=True)

    # Initialize tables asynchronously on startup if using SQLite or dev mode
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed food database on startup if seed file exists
    data_path = settings.BASE_DIR / "data" / "food_seed.json"
    if data_path.exists():
        from app.db.session import async_session
        from app.db.seed import seed_food_items_async
        async with async_session() as session:
            await seed_food_items_async(session, data_path)

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "**KCapTrack**: Computer vision-powered calorie and macro tracker. "
        "Upload meal photos to detect food items with YOLOv8, estimate portions, "
        "and track daily nutritional intake against personalized Mifflin-St Jeor biometric targets."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static Uploads & UI Mount ─────────────────────────────────────────────────
upload_path = Path(settings.UPLOAD_DIR)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

static_path = Path("static")
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(api_router)


# ── Health & Web UI ───────────────────────────────────────────────────────────
@app.get("/", tags=["UI"])
async def root():
    """Serve the KCapTrack interactive Web Dashboard."""
    index_file = Path("static/index.html")
    if index_file.exists():
        from fastapi.responses import FileResponse
        return FileResponse(index_file)
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/api", tags=["System"])
async def api_info():
    """API metadata and endpoints directory."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "auth_register": "/api/v1/users/register",
            "auth_login": "/api/v1/users/login",
            "user_profile": "/api/v1/users/profile",
            "meal_scan": "/api/v1/meals/scan",
            "meal_logs": "/api/v1/meals/logs",
            "dashboard_summary": "/api/v1/dashboard/summary",
        },
    }


@app.get("/health", tags=["System"])
async def health_check():
    """System health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "yolo_model": settings.YOLO_WEIGHTS_PATH,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
