import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.config.settings import (
    get_access_token_expire_minutes,
    get_google_client_id,
    get_jwt_algorithm,
    get_jwt_secret,
    get_refresh_token_expire_days,
)
from app.db.models import RefreshToken, User
from app.db.session import get_db

_password_hasher = PasswordHasher()
_bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(Exception):
    """Base authentication/authorization error."""


class EmailAlreadyExistsError(AuthError):
    """Raised when registering an email that already exists."""


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""


class InvalidTokenError(AuthError):
    """Raised when a JWT or Google ID token is missing, expired, malformed, or reused."""


class GoogleAccountConflictError(AuthError):
    """Raised when a Google sign-in matches an existing password account that is not yet linked.

    The caller must present the account password to prove ownership before linking.
    See POST /auth/google/link.
    """


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def _hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=get_access_token_expire_minutes())
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + delta,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())


def _encode_refresh_jwt(user_id: str, jti: str, now: datetime, expires_at: datetime) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=get_jwt_algorithm())


def issue_token_pair(
    db: Session,
    user_id: str,
    refresh_expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    delta = refresh_expires_delta or timedelta(days=get_refresh_token_expire_days())
    expires_at = now + delta
    jti = str(uuid.uuid4())

    token_row = RefreshToken(
        user_id=user_id,
        jti_hash=_hash_jti(jti),
        expires_at=expires_at,
    )
    db.add(token_row)
    db.commit()

    access_token = create_access_token(user_id)
    refresh_token = _encode_refresh_jwt(user_id=user_id, jti=jti, now=now, expires_at=expires_at)
    return access_token, refresh_token


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError("Invalid token type")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise InvalidTokenError("Invalid token subject")
    return payload


def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    """Rotate a refresh token atomically at the database level.

    Concurrency & atomicity guarantees:
      1. Lock acquisition before read/write:
         - On SQLite, if not already in a transaction, ``BEGIN IMMEDIATE`` acquires
           a RESERVED write lock before the ``SELECT`` so two concurrent threads on
           separate connections serialize cleanly instead of hitting a SHARED->RESERVED
           upgrade deadlock.
         - On PostgreSQL (and other row-locking backends), ``SELECT ... FOR UPDATE``
           acquires an exclusive row lock on the refresh token row until commit.
      2. Conditional atomic UPDATE (defense-in-depth):
         ``UPDATE refresh_tokens SET revoked_at = :now WHERE jti_hash = :h AND revoked_at IS NULL``
         checks ``result.rowcount``. If 0 rows matched (already revoked or lost a race),
         all active tokens for that user are revoked and ``InvalidTokenError`` is raised.
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        raise InvalidTokenError("Refresh token missing jti")

    jti_hash = _hash_jti(jti)

    # Acquire a write lock upfront on SQLite so concurrent writers serialize cleanly.
    bind = db.get_bind()
    if bind is not None and bind.dialect.name == "sqlite" and not db.in_transaction():
        db.execute(text("BEGIN IMMEDIATE"))

    token_row = db.scalar(
        select(RefreshToken).where(RefreshToken.jti_hash == jti_hash).with_for_update()
    )
    if token_row is None:
        raise InvalidTokenError("Unknown refresh token")

    now = datetime.now(timezone.utc)

    if token_row.revoked_at is not None:
        # Compromised/reused or concurrently rotated token: revoke all active tokens for user.
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise InvalidTokenError("Refresh token has been revoked")

    # Check expiry before attempting atomic revocation so we return the right error.
    if _as_utc(token_row.expires_at) <= now:
        raise InvalidTokenError("Refresh token expired")

    # Atomic conditional revocation: only succeeds if the row is still active.
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.jti_hash == jti_hash,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.flush()

    if result.rowcount == 0:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == token_row.user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise InvalidTokenError("Refresh token has been revoked")

    user = get_active_user(db, token_row.user_id)
    if user is None:
        db.commit()
        raise InvalidTokenError("User not found or inactive")

    new_jti = str(uuid.uuid4())
    new_expires_at = now + timedelta(days=get_refresh_token_expire_days())
    new_row = RefreshToken(
        user_id=user.id,
        jti_hash=_hash_jti(new_jti),
        expires_at=new_expires_at,
    )
    db.add(new_row)
    db.flush()

    db.execute(
        update(RefreshToken)
        .where(RefreshToken.jti_hash == jti_hash)
        .values(replaced_by=new_row.id)
    )
    db.commit()

    access_token = create_access_token(user.id)
    new_refresh_jwt = _encode_refresh_jwt(
        user_id=user.id, jti=new_jti, now=now, expires_at=new_expires_at
    )
    return access_token, new_refresh_jwt


def revoke_refresh_token(db: Session, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    try:
        payload = jwt.decode(
            refresh_token,
            get_jwt_secret(),
            algorithms=[get_jwt_algorithm()],
            options={"verify_exp": False},
        )
    except jwt.PyJWTError:
        return

    if payload.get("type") != "refresh":
        return
    jti = payload.get("jti")
    if not isinstance(jti, str) or not jti:
        return

    token_row = db.scalar(select(RefreshToken).where(RefreshToken.jti_hash == _hash_jti(jti)))
    if token_row is not None and token_row.revoked_at is None:
        token_row.revoked_at = datetime.now(timezone.utc)
        db.commit()


def register_user(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    existing = db.scalar(select(User).where(User.email == normalized_email))
    if existing is not None:
        raise EmailAlreadyExistsError("An account with this email already exists")

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalized_email))
    if (
        user is None
        or not user.is_active
        or not user.password_hash
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError("Invalid email or password")
    return user


def verify_google_id_token(token: str) -> dict:
    client_id = get_google_client_id()
    if not client_id:
        raise InvalidTokenError("Google login is not configured")
    try:
        claims = google_id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise InvalidTokenError("Invalid Google ID token") from exc
    return claims


def authenticate_google_user(db: Session, id_token_str: str) -> User:
    """Verify Google ID token and return (or create) the matching user.

    If the Google email matches an existing account that still has a password_hash,
    we do NOT automatically link — the user must prove ownership first by calling
    ``link_google_to_password_account``.  This prevents an attacker who controls a
    Google account from hijacking a password-based account that shares the same email.
    """
    claims = verify_google_id_token(id_token_str)
    if claims.get("email_verified") is not True:
        raise InvalidCredentialsError("Google email is not verified")

    google_sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(google_sub, str) or not google_sub or not isinstance(email, str) or not email:
        raise InvalidTokenError("Google token missing required user claims")

    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if user is None:
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is not None:
            if user.google_sub is not None and user.google_sub != google_sub:
                raise InvalidCredentialsError("Account is linked to a different Google account")
            if user.password_hash is not None:
                # Existing password account found — require proof of ownership.
                raise GoogleAccountConflictError(
                    "An account with this email already exists. "
                    "Sign in with your password, then link Google from account settings."
                )
            # Existing Google-only account (password_hash already NULL): attach sub.
            user.google_sub = google_sub
            db.commit()
            db.refresh(user)
        else:
            user = User(
                email=normalized_email,
                password_hash=None,
                google_sub=google_sub,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    # user found by google_sub — no changes needed.

    if not user.is_active:
        raise InvalidCredentialsError("User account is inactive")
    return user


def link_google_to_password_account(db: Session, id_token_str: str, password: str) -> User:
    """Link a Google identity to an existing email/password account.

    The caller must supply the current account password to prove they own it.
    On success:
      - ``users.google_sub`` is set.
      - ``users.password_hash`` is set to NULL (Google becomes the sole credential).
      - All existing ``refresh_tokens`` for the user are revoked.

    Returns the updated ``User``.
    """
    claims = verify_google_id_token(id_token_str)
    if claims.get("email_verified") is not True:
        raise InvalidCredentialsError("Google email is not verified")

    google_sub = claims.get("sub")
    email = claims.get("email")
    if not isinstance(google_sub, str) or not google_sub or not isinstance(email, str) or not email:
        raise InvalidTokenError("Google token missing required user claims")

    normalized_email = email.strip().lower()

    # Check the google_sub is not already bound to a different account.
    existing_by_sub = db.scalar(select(User).where(User.google_sub == google_sub))
    if existing_by_sub is not None and existing_by_sub.email != normalized_email:
        raise InvalidCredentialsError("This Google account is already linked to another email")

    user = db.scalar(select(User).where(User.email == normalized_email))
    if user is None:
        raise InvalidCredentialsError("No account found for this email")
    if not user.is_active:
        raise InvalidCredentialsError("User account is inactive")
    if user.google_sub is not None and user.google_sub != google_sub:
        raise InvalidCredentialsError("Account is linked to a different Google account")
    if not user.password_hash:
        raise InvalidCredentialsError("Account does not have a password; use Google Sign-In directly")

    # Verify the supplied password proves account ownership.
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("Invalid password")

    now = datetime.now(timezone.utc)
    user.google_sub = google_sub
    user.password_hash = None
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    db.commit()
    db.refresh(user)
    return user


def get_active_user(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = get_active_user(db, payload["sub"])
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
