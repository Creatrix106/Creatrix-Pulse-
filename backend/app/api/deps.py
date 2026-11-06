from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, Request, status

from app.config import settings
from app.core.security import decode_token, oauth2_scheme
from app.db.database import db
from app.schemas.auth import User

DEMO_ADMIN_EMAIL = "admin@creatrix.io"
DEFAULT_WORKSPACE = "Creatrix Retail Org"
SESSION_COOKIE_NAMES = ("session", "access_token", "token")


def build_user(row: Dict[str, Any]) -> User:
    return User(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        role=row.get("role") or "admin",
        created_at=row.get("created_at"),
        active_workspace=DEFAULT_WORKSPACE,
    )


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": code, "message": message})


async def _anonymous_user() -> User:
    """Served only while ALLOW_ANONYMOUS_DEMO is on (the frontend has no login guard yet)."""
    demo = await db.get_user_by_email(DEMO_ADMIN_EMAIL)
    if demo:
        return build_user(demo)
    return User(id="user-demo", name="Demo Admin", email=DEMO_ADMIN_EMAIL, role="admin",
                active_workspace=DEFAULT_WORKSPACE)


async def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
) -> User:
    token, from_header = bearer_token, bool(bearer_token)
    if not token:
        for name in SESSION_COOKIE_NAMES:
            if request.cookies.get(name):
                token = request.cookies[name]
                break

    if not token:
        if settings.ALLOW_ANONYMOUS_DEMO:
            return await _anonymous_user()
        raise _unauthorized("not_authenticated", "Authentication required.")

    # An explicit Authorization header that is bad is always an error. A stale *cookie*
    # (expired, or from a reset database) is treated as "signed out" in demo mode, otherwise the
    # browser would keep sending it and every API call would fail until the user logs in again.
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub") or payload.get("id")
        user_row = await db.get_user_by_id(user_id) if user_id else None
        if not user_row:
            raise _unauthorized("user_not_found", "The account for this session no longer exists.")
        return build_user(user_row)
    except HTTPException:
        if not from_header and settings.ALLOW_ANONYMOUS_DEMO:
            return await _anonymous_user()
        raise


def require_role(*allowed_roles: str):
    async def _role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": f"Operation requires one of: {allowed_roles}"},
            )
        return user
    return _role_checker
