import logging
import os

logger = logging.getLogger(__name__)

_DEV_FALLBACK_JWT_SECRET = "dev-only-insecure-jwt-secret-change-me"


def get_environment() -> str:
    return os.environ.get("ENVIRONMENT", "development").strip().lower()


def is_production() -> bool:
    return get_environment() == "production"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///./app.db").strip()


def get_jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    if secret:
        return secret
    if is_production():
        raise RuntimeError("JWT_SECRET environment variable must be set in production.")
    logger.warning("JWT_SECRET is not set; using insecure development fallback secret.")
    return _DEV_FALLBACK_JWT_SECRET


def get_jwt_algorithm() -> str:
    return os.environ.get("JWT_ALGORITHM", "HS256").strip()


def get_access_token_expire_minutes() -> int:
    return int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))


def get_refresh_token_expire_days() -> int:
    return int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def get_cors_allowed_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


def validate_startup_settings() -> None:
    """Validate critical configuration at application startup."""
    get_jwt_secret()
