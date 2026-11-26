from datetime import timedelta
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config.settings import get_jwt_secret, reset_ephemeral_jwt_secret
from app.db.base import Base
from app.db.engine import create_db_engine
from app.db.models import RefreshToken, User
from app.db.session import create_session_factory
from app.main import app
from app.services.auth_service import create_access_token, issue_token_pair
from app.services.rate_limiter import InMemoryRateLimiter

CSRF_HEADERS = {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture()
def auth_client(monkeypatch):
    monkeypatch.setenv("MLFLOW_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-key")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client-id.apps.googleusercontent.com")
    monkeypatch.delenv("COOKIE_SAMESITE_NONE", raising=False)

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)

    with TestClient(app) as test_client:
        app.state.db_engine.dispose()
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        app.state.login_email_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        yield test_client, session_factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_register_happy_path(auth_client):
    client, _ = auth_client
    resp = client.post(
        "/auth/register",
        json={"email": "Alice@Example.com", "password": "strongpassword123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert "id" in data
    assert "password_hash" not in data
    assert "password" not in data


def test_register_duplicate_email_returns_409(auth_client):
    client, _ = auth_client
    payload = {"email": "dup@example.com", "password": "strongpassword123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_wrong_password_returns_401(auth_client):
    client, _ = auth_client
    client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "correctpassword123"},
    )
    resp = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_cookie_samesite_lax_default_and_none_fallback(auth_client, monkeypatch):
    client, _ = auth_client
    client.post(
        "/auth/register",
        json={"email": "cookie@example.com", "password": "strongpassword123"},
    )
    login_lax = client.post(
        "/auth/login",
        json={"email": "cookie@example.com", "password": "strongpassword123"},
    )
    assert login_lax.status_code == 200
    set_cookie_lax = login_lax.headers.get("set-cookie", "").lower()
    assert "httponly" in set_cookie_lax
    assert "samesite=lax" in set_cookie_lax

    monkeypatch.setenv("COOKIE_SAMESITE_NONE", "true")
    login_none = client.post(
        "/auth/login",
        json={"email": "cookie@example.com", "password": "strongpassword123"},
    )
    assert login_none.status_code == 200
    set_cookie_none = login_none.headers.get("set-cookie", "").lower()
    assert "samesite=none" in set_cookie_none
    assert "secure" in set_cookie_none


def test_refresh_rotation_works_and_old_token_rejected(auth_client):
    client, session_factory = auth_client
    client.post(
        "/auth/register",
        json={"email": "rotate@example.com", "password": "strongpassword123"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "rotate@example.com", "password": "strongpassword123"},
    )
    assert login_resp.status_code == 200
    old_refresh = login_resp.cookies.get("refresh_token")
    assert old_refresh

    refresh_resp = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert refresh_resp.status_code == 200
    new_access = refresh_resp.json()["access_token"]
    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_access
    assert new_refresh
    assert new_refresh != old_refresh

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {new_access}"})
    assert me_resp.status_code == 200

    with session_factory() as db:
        rows = db.scalars(select(RefreshToken).order_by(RefreshToken.created_at.asc())).all()
        assert len(rows) == 2
        assert rows[0].revoked_at is not None
        assert rows[0].replaced_by == rows[1].id
        assert rows[1].revoked_at is None

    # Replay the old refresh token explicitly -> must be rejected (401)
    client.cookies.set("refresh_token", old_refresh)
    replay_resp = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert replay_resp.status_code == 401


def test_refresh_reuse_revokes_all_user_tokens(auth_client):
    client, session_factory = auth_client
    client.post(
        "/auth/register",
        json={"email": "reuse@example.com", "password": "strongpassword123"},
    )
    login_1 = client.post(
        "/auth/login",
        json={"email": "reuse@example.com", "password": "strongpassword123"},
    )
    token_1 = login_1.cookies.get("refresh_token")

    login_2 = client.post(
        "/auth/login",
        json={"email": "reuse@example.com", "password": "strongpassword123"},
    )
    token_2 = login_2.cookies.get("refresh_token")
    assert token_1 and token_2 and token_1 != token_2

    # Rotate token_1 legitimately -> produces token_1b
    client.cookies.set("refresh_token", token_1)
    rot_resp = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert rot_resp.status_code == 200
    token_1b = rot_resp.cookies.get("refresh_token")
    assert token_1b

    # Attacker replays already-rotated token_1 -> triggers global revocation for user
    client.cookies.set("refresh_token", token_1)
    reuse_resp = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert reuse_resp.status_code == 401

    # Both token_1b and token_2 must now be revoked in DB and rejected
    with session_factory() as db:
        rows = db.scalars(select(RefreshToken)).all()
        assert len(rows) == 3
        assert all(row.revoked_at is not None for row in rows)

    client.cookies.set("refresh_token", token_1b)
    assert client.post("/auth/refresh", headers=CSRF_HEADERS).status_code == 401

    client.cookies.set("refresh_token", token_2)
    assert client.post("/auth/refresh", headers=CSRF_HEADERS).status_code == 401


def test_logout_revokes_refresh_token(auth_client):
    client, session_factory = auth_client
    client.post(
        "/auth/register",
        json={"email": "logout@example.com", "password": "strongpassword123"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "logout@example.com", "password": "strongpassword123"},
    )
    saved_refresh = login_resp.cookies.get("refresh_token")
    assert saved_refresh

    logout_resp = client.post("/auth/logout", headers=CSRF_HEADERS)
    assert logout_resp.status_code == 200

    with session_factory() as db:
        row = db.scalar(select(RefreshToken))
        assert row is not None
        assert row.revoked_at is not None

    client.cookies.set("refresh_token", saved_refresh)
    assert client.post("/auth/refresh", headers=CSRF_HEADERS).status_code == 401


def test_expired_refresh_token_rejected(auth_client):
    client, session_factory = auth_client
    reg = client.post(
        "/auth/register",
        json={"email": "exprefresh@example.com", "password": "strongpassword123"},
    )
    user_id = reg.json()["id"]

    with session_factory() as db:
        _, expired_refresh = issue_token_pair(
            db, user_id, refresh_expires_delta=timedelta(seconds=-10)
        )

    client.cookies.set("refresh_token", expired_refresh)
    resp = client.post("/auth/refresh", headers=CSRF_HEADERS)
    assert resp.status_code == 401


def test_refresh_and_logout_require_csrf_header(auth_client):
    client, _ = auth_client
    assert client.post("/auth/refresh").status_code == 403
    assert client.post("/auth/logout").status_code == 403


def test_expired_access_token_returns_401(auth_client):
    client, _ = auth_client
    reg = client.post(
        "/auth/register",
        json={"email": "expired@example.com", "password": "strongpassword123"},
    )
    user_id = reg.json()["id"]
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-10))
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_tampered_access_token_returns_401(auth_client):
    client, _ = auth_client
    reg = client.post(
        "/auth/register",
        json={"email": "tamper@example.com", "password": "strongpassword123"},
    )
    user_id = reg.json()["id"]
    valid_token = create_access_token(user_id)
    tampered = valid_token[:-4] + "XXXX"
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_rate_limit_login_per_ip_and_per_email(auth_client):
    client, _ = auth_client

    # 1) Per-IP limit across distinct emails
    app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    app.state.login_email_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
    assert client.post("/auth/login", json={"email": "a@example.com", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"email": "b@example.com", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"email": "c@example.com", "password": "x"}).status_code == 429

    # 2) Per-email limit even when IP limit allows more traffic
    app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
    app.state.login_email_rate_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert client.post("/auth/login", json={"email": "victim@example.com", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"email": "Victim@Example.com", "password": "x"}).status_code == 401
    assert client.post("/auth/login", json={"email": "victim@example.com", "password": "x"}).status_code == 429


def test_google_login_creates_links_and_rejects_unverified(auth_client, monkeypatch):
    client, session_factory = auth_client

    def fake_verify(token, _request, audience):
        assert audience == "test-google-client-id.apps.googleusercontent.com"
        if token == "new-user-token":
            return {
                "sub": "google-sub-123",
                "email": "GoogleUser@Example.com",
                "email_verified": True,
                "aud": audience,
            }
        if token == "unverified-token":
            return {
                "sub": "google-sub-999",
                "email": "unverified@example.com",
                "email_verified": False,
                "aud": audience,
            }
        if token == "wrong-aud-token":
            raise ValueError(f"Token has wrong audience, expected {audience}")
        raise ValueError("Invalid token")

    monkeypatch.setattr("app.services.auth_service.google_id_token.verify_oauth2_token", fake_verify)

    # 1) New Google user created with nullable password_hash and google_sub
    resp_new = client.post("/auth/google", json={"id_token": "new-user-token"})
    assert resp_new.status_code == 200
    assert resp_new.json()["access_token"]
    assert "refresh_token" in resp_new.cookies

    with session_factory() as db:
        g_user = db.scalar(select(User).where(User.email == "googleuser@example.com"))
        assert g_user is not None
        assert g_user.google_sub == "google-sub-123"
        assert g_user.password_hash is None

    # Google-only account cannot log in via password
    pw_attempt = client.post(
        "/auth/login",
        json={"email": "googleuser@example.com", "password": "anypassword"},
    )
    assert pw_attempt.status_code == 401

    # 2) Unverified email refused
    resp_unverified = client.post("/auth/google", json={"id_token": "unverified-token"})
    assert resp_unverified.status_code == 401


def test_google_login_rejects_wrong_audience(auth_client, monkeypatch):
    client, _ = auth_client

    def fake_verify(token, _request, audience):
        token_aud = "other-client-id.apps.googleusercontent.com"
        if token_aud != audience:
            raise ValueError("Wrong audience")
        return {"sub": "s", "email": "a@example.com", "email_verified": True}

    monkeypatch.setattr("app.services.auth_service.google_id_token.verify_oauth2_token", fake_verify)
    resp = client.post("/auth/google", json={"id_token": "token-for-other-client"})
    assert resp.status_code == 401


def test_google_login_requires_ownership_proof_for_existing_password_account(
    auth_client, monkeypatch
):
    """POST /auth/google returns 409 when the email matches an existing password account.

    The user must call POST /auth/google/link with their password to prove ownership.
    That endpoint clears password_hash, revokes existing tokens, and issues a fresh pair.
    """
    client, session_factory = auth_client

    def fake_verify(token, _request, audience):
        assert audience == "test-google-client-id.apps.googleusercontent.com"
        return {
            "sub": "google-sub-456",
            "email": "existing@example.com",
            "email_verified": True,
            "aud": audience,
        }

    monkeypatch.setattr("app.services.auth_service.google_id_token.verify_oauth2_token", fake_verify)

    # Register and sign in with password first.
    assert (
        client.post(
            "/auth/register",
            json={"email": "existing@example.com", "password": "strongpassword123"},
        ).status_code
        == 201
    )
    pw_login = client.post(
        "/auth/login",
        json={"email": "existing@example.com", "password": "strongpassword123"},
    )
    assert pw_login.status_code == 200
    pw_refresh = pw_login.cookies.get("refresh_token")
    assert pw_refresh

    # /auth/google must NOT auto-link — it must return 409 and explain what to do.
    google_resp = client.post("/auth/google", json={"id_token": "link-existing-token"})
    assert google_resp.status_code == 409
    assert "password" in google_resp.json()["detail"].lower()

    # Account must be unchanged: google_sub still NULL, password_hash still set.
    with session_factory() as db:
        u = db.scalar(select(User).where(User.email == "existing@example.com"))
        assert u is not None
        assert u.google_sub is None
        assert u.password_hash is not None

    # Old refresh token must still work (account not disturbed).
    client.cookies.set("refresh_token", pw_refresh)
    assert client.post("/auth/refresh", headers=CSRF_HEADERS).status_code == 200

    # /auth/google/link with wrong password → 401.
    link_bad = client.post(
        "/auth/google/link",
        json={"id_token": "link-existing-token", "password": "WRONG_password"},
    )
    assert link_bad.status_code == 401

    # /auth/google/link with correct password → 200; password cleared, tokens revoked.
    link_resp = client.post(
        "/auth/google/link",
        json={"id_token": "link-existing-token", "password": "strongpassword123"},
    )
    assert link_resp.status_code == 200
    link_refresh = link_resp.cookies.get("refresh_token")
    assert link_refresh

    with session_factory() as db:
        linked = db.scalar(select(User).where(User.email == "existing@example.com"))
        assert linked is not None
        assert linked.google_sub == "google-sub-456"
        assert linked.password_hash is None

        tokens = db.scalars(
            select(RefreshToken).where(RefreshToken.user_id == linked.id)
        ).all()
        # 3 rows: pw_login, the refreshed one from above, and the link token.
        # All old ones must be revoked; only the link-issued token is active.
        active = [t for t in tokens if t.revoked_at is None]
        assert len(active) == 1

    # Password login must now fail — password_hash is gone.
    assert (
        client.post(
            "/auth/login",
            json={"email": "existing@example.com", "password": "strongpassword123"},
        ).status_code
        == 401
    )

    # /auth/google now succeeds (google_sub already set, no password_hash conflict).
    google_now = client.post("/auth/google", json={"id_token": "link-existing-token"})
    assert google_now.status_code == 200


def test_concurrent_refresh_rotation_only_one_succeeds(monkeypatch, tmp_path):
    """Regression test: two threads with independent DB connections racing to rotate
    the same refresh token.

    Uses a file-backed SQLite DB (separate connections per session, rather than
    in-memory StaticPool) so both threads genuinely execute concurrent DB transactions.
    Only one request should receive 200; the other must get 401 and at most one
    replacement refresh token row may be created.
    """
    monkeypatch.setenv("MLFLOW_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-key")
    monkeypatch.setenv("ENVIRONMENT", "test")

    db_file = tmp_path / "concurrent_refresh.db"
    engine = create_db_engine(f"sqlite:///{db_file}")
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)

    with TestClient(app) as client:
        app.state.db_engine.dispose()
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        app.state.login_email_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)

        assert (
            client.post(
                "/auth/register",
                json={"email": "concurrent@example.com", "password": "strongpassword123"},
            ).status_code
            == 201
        )
        login_resp = client.post(
            "/auth/login",
            json={"email": "concurrent@example.com", "password": "strongpassword123"},
        )
        assert login_resp.status_code == 200
        shared_refresh = login_resp.cookies.get("refresh_token")
        assert shared_refresh

        results: list[int] = []
        results_lock = threading.Lock()
        barrier = threading.Barrier(2)

        def do_refresh():
            tc = TestClient(app)
            tc.cookies.set("refresh_token", shared_refresh)
            barrier.wait()
            resp = tc.post("/auth/refresh", headers=CSRF_HEADERS)
            with results_lock:
                results.append(resp.status_code)

        t1 = threading.Thread(target=do_refresh)
        t2 = threading.Thread(target=do_refresh)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert sorted(results) == [200, 401], (
            f"Expected exactly one 200 and one 401, got {results}"
        )

        # Only one new token row should have been created (2 total: original + 1 rotated),
        # and both should now be revoked (winner rotated original -> new; loser detected reuse).
        with session_factory() as db:
            rows = db.scalars(select(RefreshToken).order_by(RefreshToken.created_at.asc())).all()
            assert len(rows) == 2
            assert rows[0].replaced_by == rows[1].id
            assert all(r.revoked_at is not None for r in rows)

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_non_prod_without_jwt_secret_uses_ephemeral_random_secret(monkeypatch, caplog):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./app.db")
    monkeypatch.delenv("JWT_SECRET", raising=False)

    reset_ephemeral_jwt_secret()
    secret_1 = get_jwt_secret()
    assert secret_1
    assert "dev-only-insecure" not in secret_1
    assert "ephemeral" in caplog.text.lower()

    reset_ephemeral_jwt_secret()
    secret_2 = get_jwt_secret()
    assert secret_1 != secret_2
