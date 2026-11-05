from typing import Any, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse

class AppException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Any] = None
    ):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details

class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found.", code: str = "not_found", details: Optional[Any] = None):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, code=code, message=message, details=details)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required.", code: str = "unauthorized", details: Optional[Any] = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, code=code, message=message, details=details)

class ForbiddenException(AppException):
    def __init__(self, message: str = "Access forbidden.", code: str = "forbidden", details: Optional[Any] = None):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, code=code, message=message, details=details)

class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request.", code: str = "bad_request", details: Optional[Any] = None):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, code=code, message=message, details=details)

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    content = {
        "success": False,
        "code": exc.code,
        "message": exc.message,
        "details": exc.details,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "details": exc.details
        }
    }
    return JSONResponse(status_code=exc.status_code, content=content)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "http_error")
        message = exc.detail.get("message", "An error occurred.")
        details = exc.detail.get("details")
    else:
        code = "http_error"
        message = str(exc.detail)
        details = None
        
    content = {
        "success": False,
        "code": code,
        "message": message,
        "details": details,
        "error": {
            "code": code,
            "message": message,
            "details": details
        }
    }
    return JSONResponse(status_code=exc.status_code, content=content)

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    content = {
        "success": False,
        "code": "internal_server_error",
        "message": "An unexpected server error occurred.",
        "details": str(exc),
        "error": {
            "code": "internal_server_error",
            "message": str(exc)
        }
    }
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content)
