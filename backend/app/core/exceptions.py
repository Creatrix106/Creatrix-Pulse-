import logging
from typing import Any, Optional

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.services.errors import DatasetNotFoundError

logger = logging.getLogger("creatrix.errors")


class AppException(StarletteHTTPException):
    def __init__(self, status_code: int, code: str, message: str, details: Optional[Any] = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found.", code: str = "not_found", details: Optional[Any] = None):
        super().__init__(status.HTTP_404_NOT_FOUND, code, message, details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required.", code: str = "unauthorized", details: Optional[Any] = None):
        super().__init__(status.HTTP_401_UNAUTHORIZED, code, message, details)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access forbidden.", code: str = "forbidden", details: Optional[Any] = None):
        super().__init__(status.HTTP_403_FORBIDDEN, code, message, details)


class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request.", code: str = "bad_request", details: Optional[Any] = None):
        super().__init__(status.HTTP_400_BAD_REQUEST, code, message, details)


def _error_body(code: str, message: str, details: Any = None) -> dict:
    """The frontend reads `code`, `message`, `details` from the TOP LEVEL of the body."""
    return {
        "success": False,
        "code": code,
        "message": message,
        "details": details,
        "error": {"code": code, "message": message, "details": details},
    }


def _cors_headers(request: Request) -> dict:
    """Errors raised outside the CORS middleware (500s) would otherwise reach the browser
    without CORS headers, which the frontend reports as a generic 'network error'."""
    origin = request.headers.get("origin")
    if origin and settings.is_origin_allowed(origin):
        return {
            "access-control-allow-origin": origin,
            "access-control-allow-credentials": "true",
            "vary": "Origin",
        }
    return {}


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message, exc.details))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles FastAPI HTTPException *and* Starlette's own 404/405 (unknown route, bad method)."""
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "http_error")
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details")
    else:
        code = "not_found" if exc.status_code == 404 else "http_error"
        message = str(exc.detail)
        details = None
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message, details),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path")]
    field = ".".join(loc)
    msg = first.get("msg", "Invalid request.")
    message = f"Invalid value for '{field}': {msg}" if field else f"Invalid request: {msg}"
    try:
        details = jsonable_encoder(errors)
    except Exception:  # non-serialisable ctx objects
        details = [{"loc": list(e.get("loc", ())), "msg": str(e.get("msg", ""))} for e in errors]
    return JSONResponse(status_code=422, content=_error_body("validation_error", message, details))


async def dataset_not_found_handler(request: Request, exc: DatasetNotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=_error_body("dataset_not_found", "This dataset does not exist or was deleted."),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    details = f"{type(exc).__name__}: {exc}" if settings.DEBUG else None
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_server_error", "An unexpected server error occurred.", details),
        headers=_cors_headers(request),
    )
