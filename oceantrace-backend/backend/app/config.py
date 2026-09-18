"""
Central configuration, loaded from environment variables.
Never hardcode secrets here — see .env.example for required variables.
"""
import os
from functools import lru_cache


class Settings:
    APP_NAME: str = "OceanTrace AI"
    ENV: str = os.getenv("ENV", "development")

    # --- Security -----------------------------------------------------
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    SESSION_IDLE_TIMEOUT_MINUTES: int = int(os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "30"))

    # --- Database -------------------------------------------------------
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./oceantrace.db")

    # --- CORS -------------------------------------------------------------
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")

    # --- Uploads ------------------------------------------------------------
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./data/uploads")
    MAX_UPLOAD_MB: int = int(os.getenv("MAX_UPLOAD_MB", "25"))
    ALLOWED_IMAGE_EXT: set = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

    # --- Rate limiting ------------------------------------------------------
    AUTH_RATE_LIMIT: str = os.getenv("AUTH_RATE_LIMIT", "10/minute")

    def validate(self):
        if self.ENV == "production" and not self.JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET must be set via environment variable in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if not self.JWT_SECRET:
            # Development-only fallback so the demo boots without extra setup.
            # This is NEVER acceptable in production — see validate() above.
            self.JWT_SECRET = "dev-only-insecure-secret-change-me"


@lru_cache
def get_settings() -> "Settings":
    s = Settings()
    s.validate()
    return s
