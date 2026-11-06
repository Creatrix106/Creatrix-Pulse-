import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.config import settings

# `auto_error=False`: deps.get_current_user decides what an unauthenticated request means.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/token",
    auto_error=False,
)

PBKDF2_ITERATIONS = 100_000


def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    kdf_b64 = base64.b64encode(kdf).decode("ascii")
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt_b64}${kdf_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        meta, salt_b64, kdf_b64 = hashed_password.split("$")
        iterations = int(meta.rsplit(":", 1)[-1])  # honour the count stored with the hash
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_kdf = base64.b64decode(kdf_b64.encode("ascii"))
        actual_kdf = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(expected_kdf, actual_kdf)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT (HS256)
# ---------------------------------------------------------------------------

def _sign(payload: Dict[str, Any]) -> str:
    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    header_b64 = _b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64_url_encode(signature)}"


def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    now = int(time.time())
    ttl = expires_delta_seconds if expires_delta_seconds is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    return _sign({**data, "exp": now + ttl, "iat": now, "type": "access"})


def create_refresh_token(data: Dict[str, Any]) -> str:
    now = int(time.time())
    return _sign({**data, "exp": now + settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60, "iat": now, "type": "refresh"})


def _unauthorized(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"code": code, "message": message})


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """Verify signature + expiry. When `expected_type` is given the token's `type` claim must
    match, so a long-lived refresh token can never be used as an access token (or vice versa)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise _unauthorized("invalid_token", "Malformed token.")
    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64_url_decode(sig_b64)
    except Exception:
        raise _unauthorized("invalid_token", "Invalid token encoding.")
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise _unauthorized("invalid_signature", "Token signature mismatch.")
    try:
        payload = json.loads(_b64_url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise _unauthorized("invalid_token", "Could not parse token claims.")
    if payload.get("exp", 0) < time.time():
        raise _unauthorized("token_expired", "Token has expired.")
    if expected_type is not None and payload.get("type") != expected_type:
        raise _unauthorized("invalid_token_type", f"Expected a {expected_type} token.")
    return payload
