from typing import Any, Optional, Dict, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[Any] = None
    meta: Optional[Dict[str, Any]] = None

def make_envelope(data: Any, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": meta
    }

def format_response(data: Any, meta: Optional[Dict[str, Any]] = None, envelope: bool = False) -> Any:
    """
    If envelope=True, returns standardized envelope.
    If envelope=False:
      - If data is a dict, embeds 'success': True, 'error': None alongside top-level keys
        so that both direct frontend consumption (res.id, res.name) and envelope-checking
        clients (res.success, res.data) are natively satisfied!
      - If data is a list, returns data directly so array methods (.map, .length) in frontend work.
    """
    if envelope:
        return make_envelope(data, meta)
    
    if isinstance(data, dict):
        res = dict(data)
        if "success" not in res:
            res["success"] = True
        if "error" not in res:
            res["error"] = None
        if meta and "meta" not in res:
            res["meta"] = meta
        if "data" not in res:
            res["data"] = data
        return res
        
    return data
