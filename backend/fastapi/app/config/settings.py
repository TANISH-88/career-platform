import logging
import os
import secrets

logger = logging.getLogger(__name__)

_ephemeral_dev_jwt_secret: str | None = None


def get_raw_environment() -> str:
    return os.environ.get("ENVIRONMENT", "").strip().lower()


def get_environment() -> str:
    return get_raw_environment() or "development"


def is_production() -> bool:
    return get_environment() == "production"


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", "sqlite:///./app.db").strip()


def _is_sqlite_url(url: str) -> bool:
    return url.lower().startswith("sqlite")


def _check_fail_closed_environment() -> None:
    if not get_raw_environment() and not _is_sqlite_url(get_database_url()):
        raise RuntimeError(
            "ENVIRONMENT must be set when DATABASE_URL is not SQLite (fail-closed startup guard)."
        )


def get_jwt_secret() -> str:
    global _ephemeral_dev_jwt_secret

    _check_fail_closed_environment()
    secret = os.environ.get("JWT_SECRET", "").strip()
    if secret:
        return secret

    if is_production():
        raise RuntimeError("JWT_SECRET environment variable must be set in production.")

    if _ephemeral_dev_jwt_secret is None:
        _ephemeral_dev_jwt_secret = secrets.token_urlsafe(32)
        logger.warning(
            "JWT_SECRET is not set; generated an ephemeral per-process secret for non-production use."
        )
    return _ephemeral_dev_jwt_secret


def reset_ephemeral_jwt_secret() -> None:
    """Reset the cached per-process dev secret (for tests)."""
    global _ephemeral_dev_jwt_secret
    _ephemeral_dev_jwt_secret = None


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


def get_google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def use_samesite_none_cookie() -> bool:
    return os.environ.get("COOKIE_SAMESITE_NONE", "false").strip().lower() in ("true", "1", "yes")


def is_cookie_secure() -> bool:
    if is_production() or use_samesite_none_cookie():
        return True
    return os.environ.get("COOKIE_SECURE", "false").strip().lower() in ("true", "1", "yes")


def validate_startup_settings() -> None:
    """Validate critical configuration at application startup."""
    _check_fail_closed_environment()
    get_jwt_secret()
