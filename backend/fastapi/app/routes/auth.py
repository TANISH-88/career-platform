from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config.settings import (
    get_refresh_token_expire_days,
    is_cookie_secure,
    use_samesite_none_cookie,
)
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    GoogleLinkRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import (
    EmailAlreadyExistsError,
    GoogleAccountConflictError,
    InvalidCredentialsError,
    InvalidTokenError,
    authenticate_google_user,
    authenticate_user,
    get_current_user,
    issue_token_pair,
    link_google_to_password_account,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.rate_limiter import rate_limit_auth, rate_limit_login_email

auth_router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/"


def _cookie_policy() -> tuple[bool, str]:
    samesite = "none" if use_samesite_none_cookie() else "lax"
    secure = is_cookie_secure()
    return secure, samesite


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    secure, samesite = _cookie_policy()
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=REFRESH_COOKIE_PATH,
        max_age=get_refresh_token_expire_days() * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    secure, samesite = _cookie_policy()
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path=REFRESH_COOKIE_PATH,
    )


def require_csrf_header(
    x_requested_with: str | None = Header(default=None, alias="X-Requested-With"),
) -> None:
    if not x_requested_with or not x_requested_with.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-Requested-With header",
        )


@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit_auth)],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_user(db, email=payload.email, password=payload.password)
    except EmailAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    rate_limit_login_email(request, payload.email)
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token, refresh_token = issue_token_pair(db, user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@auth_router.post(
    "/google",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    try:
        user = authenticate_google_user(db, payload.id_token)
    except GoogleAccountConflictError as exc:
        # An existing password account matched by email — ownership proof required.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (InvalidCredentialsError, InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token, refresh_token = issue_token_pair(db, user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@auth_router.post(
    "/google/link",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit_auth)],
)
def google_link(
    payload: GoogleLinkRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    """Link a Google identity to an existing email/password account.

    The caller must supply their current password to prove they own the account.
    On success the account's password_hash is cleared and all existing refresh
    tokens are revoked; a fresh token pair is issued.
    """
    try:
        user = link_google_to_password_account(db, payload.id_token, payload.password)
    except (InvalidCredentialsError, InvalidTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    access_token, refresh_token = issue_token_pair(db, user.id)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@auth_router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(require_csrf_header)],
)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    try:
        access_token, new_refresh_token = rotate_refresh_token(db, refresh_token)
    except InvalidTokenError as exc:
        _clear_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    _set_refresh_cookie(response, new_refresh_token)
    return TokenResponse(access_token=access_token)


@auth_router.post(
    "/logout",
    dependencies=[Depends(require_csrf_header)],
)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    revoke_refresh_token(db, refresh_token)
    _clear_refresh_cookie(response)
    return {"detail": "Logged out"}


@auth_router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
