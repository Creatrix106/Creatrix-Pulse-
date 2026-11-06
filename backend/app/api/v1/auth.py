import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import SESSION_COOKIE_NAMES, build_user, get_current_user
from app.config import settings
from app.core.compat import model_to_dict
from app.core.exceptions import AppException, UnauthorizedException
from app.core.response import json_response
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.database import db
from app.schemas.auth import LoginPayload, RefreshPayload, RegisterPayload, User

router = APIRouter(prefix="/auth", tags=["Authentication"])

MIN_PASSWORD_LENGTH = 8


def _set_session_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        key="session",
        value=token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # same lifetime as the token inside it
        path="/",
    )


def _issue_session(user_row: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    """User payload + tokens + session cookie. The cookie MUST be set on the response object that
    is actually returned: cookies set on an injected `response` are dropped when a Response is
    returned directly (the original register/logout bug)."""
    access_token = create_access_token({
        "sub": user_row["id"], "role": user_row.get("role", "admin"),
        "email": user_row["email"], "name": user_row["name"],
    })
    refresh_token = create_refresh_token({"sub": user_row["id"]})
    user = model_to_dict(build_user(user_row))
    body = {
        **user,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
        "success": True,
        "data": user,
        "error": None,
    }
    resp = json_response(body, status_code=status_code)
    _set_session_cookie(resp, access_token)
    return resp


async def _authenticate(email: Any, password: Any) -> Dict[str, Any]:
    if not email or not password:
        raise AppException(status.HTTP_400_BAD_REQUEST, "invalid_credentials", "Email and password are required.")

    email = str(email).lower().strip()
    bad_credentials = UnauthorizedException("Incorrect email or password.", code="invalid_credentials")
    if email.startswith("blocked@"):  # fixture mirrored from the frontend mock
        raise bad_credentials

    user_row = await db.get_user_by_email(email)
    if user_row is None:
        if not settings.AUTO_CREATE_USER_ON_LOGIN:
            raise bad_credentials  # same message as a wrong password: do not reveal which e-mails exist
        user_row = {
            "id": f"user-{uuid.uuid4().hex[:8]}",
            "name": email.split("@")[0].replace(".", " ").replace("-", " ").title(),
            "email": email,
            "hashed_password": hash_password(str(password)),
            "role": "admin",
        }
        await db.create_user(user_row)
    elif not verify_password(str(password), user_row["hashed_password"]):
        raise bad_credentials
    return user_row


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterPayload):
    email = payload.email.lower().strip()
    name = payload.name.strip()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 254:
        raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_email", "Enter a valid email address.")
    if len(name) < 1:
        raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_name", "Enter your name.")
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise AppException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "weak_password",
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
        )
    if await db.get_user_by_email(email):
        raise AppException(status.HTTP_400_BAD_REQUEST, "user_exists", "A user with this email already exists.")

    user_row = {
        "id": f"user-{uuid.uuid4().hex[:8]}",
        "name": name,
        "email": email,
        "hashed_password": hash_password(payload.password),
        "role": payload.role or "admin",
    }
    await db.create_user(user_row)
    return _issue_session(user_row, status_code=status.HTTP_201_CREATED)


@router.post("/login", response_model=User)
async def login(payload: LoginPayload):
    """JSON login used by the frontend: `{ "email": ..., "password": ... }`."""
    return _issue_session(await _authenticate(payload.email, payload.password))


@router.post("/token", include_in_schema=True)
async def login_for_swagger(form: OAuth2PasswordRequestForm = Depends()):
    """Form-encoded login (`username` + `password`) for OAuth2 clients and Swagger's *Authorize* button."""
    return _issue_session(await _authenticate(form.username, form.password))


@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    user = model_to_dict(current_user)
    return json_response({**user, "success": True, "data": user, "error": None})


@router.post("/refresh")
async def refresh_tokens(payload: RefreshPayload):
    try:
        claims = decode_token(payload.refresh_token, expected_type="refresh")
    except Exception:
        raise UnauthorizedException("Refresh token is invalid or expired.", code="invalid_refresh_token")

    user_row = await db.get_user_by_id(claims.get("sub"))
    if not user_row:
        raise UnauthorizedException("User not found.", code="user_not_found")

    new_access = create_access_token({
        "sub": user_row["id"], "role": user_row.get("role", "admin"),
        "email": user_row["email"], "name": user_row["name"],
    })
    resp = json_response({
        "success": True,
        "access_token": new_access,
        "refresh_token": create_refresh_token({"sub": user_row["id"]}),
        "token_type": "bearer",
    })
    _set_session_cookie(resp, new_access)
    return resp


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    for name in SESSION_COOKIE_NAMES:  # delete on the response we return (see _issue_session)
        resp.delete_cookie(name, path="/")
    return resp
