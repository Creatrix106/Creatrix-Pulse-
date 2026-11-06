"""Small helpers that behave the same on Pydantic v1 and v2."""
from typing import Any, Dict


def model_to_dict(model: Any, **kwargs: Any) -> Dict[str, Any]:
    """`model_dump()` on Pydantic v2, `dict()` on v1 (avoids v2 deprecation warnings)."""
    if hasattr(model, "model_dump"):
        return model.model_dump(**kwargs)
    return model.dict(**kwargs)
