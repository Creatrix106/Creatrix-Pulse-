import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.insights import router as insights_router
from app.api.v1.reports import router as reports_router
from app.config import DEFAULT_SECRET_KEY, settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    dataset_not_found_handler,
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.db.database import db
from app.db.seed import seed_all
from app.services.errors import DatasetNotFoundError

logger = logging.getLogger("creatrix.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    await seed_all()  # no-op after the first run (see app/db/seed.py)

    if settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        logger.warning("SECRET_KEY is the built-in default. Set a long random SECRET_KEY before deploying.")
    if settings.ALLOW_ANONYMOUS_DEMO:
        logger.warning(
            "ALLOW_ANONYMOUS_DEMO is ON: requests without a session are served as the demo admin. "
            "Set ALLOW_ANONYMOUS_DEMO=false before deploying."
        )
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="High-performance backend API for Creatrix Pulse Analytics application.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# The frontend sends cookies (credentials: "include"), so the browser requires an EXPLICIT
# Access-Control-Allow-Origin. A "*" origin makes every credentialed request fail in the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list(),
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# All errors reach the frontend as { code, message, details } (see src/services/api-client.ts).
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # incl. unknown route 404 / 405
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(DatasetNotFoundError, dataset_not_found_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.get("/health", tags=["Health"])
async def health_check():
    database_ok = await db.ping()
    return {
        "status": "ok" if database_ok else "degraded",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected" if database_ok else "unavailable",
    }


ROUTERS = [auth_router, datasets_router, analytics_router, insights_router, reports_router]

# Same routes under three prefixes so any NEXT_PUBLIC_API_BASE_URL works:
#   http://localhost:8000/api/v1   (recommended)   http://localhost:8000/api   http://localhost:8000
# Only the versioned copy is listed in /docs (the others would duplicate every operation id).
for _router in ROUTERS:
    app.include_router(_router, prefix=settings.API_V1_PREFIX)
for _router in ROUTERS:
    app.include_router(_router, prefix="/api", include_in_schema=False)
for _router in ROUTERS:
    app.include_router(_router, include_in_schema=False)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
