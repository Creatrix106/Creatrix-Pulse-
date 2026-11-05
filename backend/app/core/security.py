import os
import hmac
import hashlib
import base64
import json
import time
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False
)

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def _b64_url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
# Password Hashing hoah rhi bdi bhayankar wrna sb gya

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    kdf_b64 = base64.b64encode(kdf).decode("ascii")
    return f"pbkdf2:sha256:100000${salt_b64}${kdf_b64}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3:
            return False
        meta, salt_b64, kdf_b64 = parts
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_kdf = base64.b64decode(kdf_b64.encode("ascii"))
        actual_kdf = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected_kdf, actual_kdf)
    except Exception:
        return False

# JWT Tokens 🗿

def create_access_token(data: Dict[str, Any], expires_delta_seconds: Optional[int] = None) -> str:
    payload = data.copy()
    now = int(time.time())
    if expires_delta_seconds is not None:
        expire = now + expires_delta_seconds
    else:
        expire = now + (settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    payload.update({
        "exp": expire,
        "iat": now,
        "type": "access"
    })
    
    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    header_bytes = _b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_bytes = _b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_bytes}.{payload_bytes}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(signature)
    return f"{header_bytes}.{payload_bytes}.{sig_b64}"

def create_refresh_token(data: Dict[str, Any]) -> str:
    payload = data.copy()
    now = int(time.time())
    expire = now + (settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60)
    payload.update({
        "exp": expire,
        "iat": now,
        "type": "refresh"
    })
    header = {"alg": settings.ALGORITHM, "typ": "JWT"}
    header_bytes = _b64_url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_bytes = _b64_url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_bytes}.{payload_bytes}".encode("utf-8")
    signature = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = _b64_url_encode(signature)
    return f"{header_bytes}.{payload_bytes}.{sig_b64}"

def decode_token(token: str) -> Dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Malformed token."}
        )
    header_bytes, payload_bytes, sig_b64 = parts
    signing_input = f"{header_bytes}.{payload_bytes}".encode("utf-8")
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        actual_sig = _b64_url_decode(sig_b64)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Invalid token encoding."}
        )
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_signature", "message": "Token signature mismatch."}
        )
    try:
        payload = json.loads(_b64_url_decode(payload_bytes).decode("utf-8"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Could not parse token claims."}
        )
    if payload.get("exp", 0) < time.time():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "token_expired", "message": "Token has expired."}
        )
    return payload
