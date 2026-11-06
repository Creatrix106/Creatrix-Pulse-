"""Make arbitrary analytics output JSON-safe (framework free, so it is unit-testable).

Starlette's JSONResponse uses json.dumps(allow_nan=False): a single NaN/inf, numpy scalar
or Timestamp anywhere in a payload turns the whole response into a 500. Sanitising at the
boundary removes that whole class of bug.
"""
import datetime as _dt
import math
from pathlib import Path
from typing import Any

try:  # numpy is always present (pandas dependency) but keep this module importable without it
    import numpy as _np
except ImportError:  # pragma: no cover
    _np = None


def sanitize(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, bool)):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    # pandas missing-value singletons (NaT / NA) without importing pandas
    if type(obj).__name__ in ("NaTType", "NAType"):
        return None
    if _np is not None and isinstance(obj, _np.generic):
        return sanitize(obj.item())
    if isinstance(obj, dict):
        return {str(k): sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [sanitize(v) for v in obj]
    if _np is not None and isinstance(obj, _np.ndarray):
        return [sanitize(v) for v in obj.tolist()]
    if isinstance(obj, (_dt.datetime, _dt.date)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    return str(obj)
