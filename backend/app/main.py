from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    general_exception_handler,
)
from app.db.database import db
from app.db.seed import seed_all

from app.api.v1.auth import router as auth_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.insights import router as insights_router
from app.api.v1.reports import router as reports_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-performance backend API for Creatrix Pulse Analytics application.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

@app.on_event("startup")
async def on_startup():
    await db.init_db()
    # Check if demo datasets exist; if not, seed
    datasets = await db.list_datasets()
    if not datasets:
        await seed_all()

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected"
    }

# 1. Mount API v1 Routes
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(datasets_router, prefix=settings.API_V1_PREFIX)
app.include_router(analytics_router, prefix=settings.API_V1_PREFIX)
app.include_router(insights_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)

# 2. Mount API Routes with /api prefix (for default NEXT_PUBLIC_API_BASE_URL="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(insights_router, prefix="/api")
app.include_router(reports_router, prefix="/api")

# 3. Mount Direct Root Routes (for NEXT_PUBLIC_API_BASE_URL="http://localhost:8000")
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(analytics_router)
app.include_router(insights_router)
app.include_router(reports_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
