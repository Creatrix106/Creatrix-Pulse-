from typing import Any, Dict, Mapping, Optional

from fastapi.responses import JSONResponse

from app.core.jsonsafe import sanitize


def json_response(
    content: Any,
    status_code: int = 200,
    headers: Optional[Mapping[str, str]] = None,
) -> JSONResponse:
    """JSONResponse that can never fail on NaN / numpy / datetime values."""
    return JSONResponse(content=sanitize(content), status_code=status_code, headers=dict(headers or {}))


def make_envelope(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None, "meta": meta}
