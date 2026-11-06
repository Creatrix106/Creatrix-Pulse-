import json
import re
from pathlib import Path
from typing import List, Optional

# Works with both Pydantic v2 (pydantic-settings, what requirements.txt installs)
# and legacy Pydantic v1 (where BaseSettings still lives in `pydantic`).
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _PYDANTIC_V2 = True
except ImportError:  # pragma: no cover - only on pydantic v1 installs
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = None  # type: ignore
    _PYDANTIC_V2 = False

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_SECRET_KEY = "creatrix-pulse-jwt-super-secret-key-32-chars-min-prod"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Creatrix Pulse API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # ---- Security ----
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # The frontend has no login guard yet, so by default requests without a session
    # are served as the seeded demo admin. SET THIS TO false BEFORE DEPLOYING.
    ALLOW_ANONYMOUS_DEMO: bool = True
    # Logging in with an unknown e-mail must NOT silently create an account.
    AUTO_CREATE_USER_ON_LOGIN: bool = False

    # Session cookie. Use COOKIE_SECURE=true and COOKIE_SAMESITE=none when the
    # frontend and API live on different sites (HTTPS required for that).
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # ---- Database ----
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'creatrix_pulse.db'}"

    # ---- Storage ----
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = BASE_DIR / "data" / "uploads"
    PARQUET_DIR: Path = BASE_DIR / "data" / "parquet"
    REPORTS_DIR: Path = BASE_DIR / "data" / "reports"

    # ---- CORS ----
    # Comma-separated list or JSON array. NEVER include "*": browsers reject a wildcard
    # origin on credentialed requests (the frontend sends cookies), so login would fail.
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # Any localhost port is accepted in development (Next.js moves to 3001 if 3000 is busy).
    CORS_ORIGIN_REGEX: Optional[str] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

    # ---- Processing ----
    MAX_FILE_SIZE_MB: int = 50
    PREVIEW_ROW_COUNT: int = 8
    MAX_EXPLORER_ROWS: int = 50_000
    # Share of rows allowed to have an unreadable date before the upload is rejected.
    MAX_BAD_DATE_SHARE: float = 0.05
    # Ambiguous dates such as 05/03/2026: day-first (India/UK) when True, month-first (US) when False.
    # Unambiguous values in the file (e.g. 13/03/2026) always override this.
    DATE_DAYFIRST_DEFAULT: bool = True

    if _PYDANTIC_V2:
        model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")
    else:  # pragma: no cover

        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"

    # ---- helpers ----
    def cors_origins_list(self) -> List[str]:
        raw = (self.CORS_ORIGINS or "").strip()
        if raw.startswith("["):
            try:
                items = [str(o) for o in json.loads(raw)]
            except ValueError:
                items = []
        else:
            items = [o.strip() for o in raw.split(",")]
        return [o.rstrip("/") for o in items if o and o != "*"]

    def is_origin_allowed(self, origin: Optional[str]) -> bool:
        if not origin:
            return False
        if origin.rstrip("/") in self.cors_origins_list():
            return True
        return bool(self.CORS_ORIGIN_REGEX and re.fullmatch(self.CORS_ORIGIN_REGEX, origin))


settings = Settings()

# Ensure directories exist
for _d in (settings.DATA_DIR, settings.UPLOAD_DIR, settings.PARQUET_DIR, settings.REPORTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
