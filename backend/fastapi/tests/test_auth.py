from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.engine import create_db_engine
from app.db.session import create_session_factory
from app.main import app
from app.services.auth_service import create_access_token
from app.services.rate_limiter import InMemoryRateLimiter


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("MLFLOW_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-key")
    monkeypatch.setenv("ENVIRONMENT", "test")

    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = create_session_factory(engine)

    with TestClient(app) as test_client:
        app.state.db_engine.dispose()
        app.state.db_engine = engine
        app.state.db_session_factory = session_factory
        app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60)
        yield test_client

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_register_happy_path(client: TestClient):
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


def test_register_duplicate_email_returns_409(client: TestClient):
    payload = {"email": "dup@example.com", "password": "strongpassword123"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_wrong_password_returns_401(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "correctpassword123"},
    )
    resp = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_login_me_refresh_and_logout(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "carol@example.com", "password": "strongpassword123"},
    )
    login_resp = client.post(
        "/auth/login",
        json={"email": "carol@example.com", "password": "strongpassword123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    assert token
    assert "refresh_token" in login_resp.cookies

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "carol@example.com"

    refresh_resp = client.post("/auth/refresh")
    assert refresh_resp.status_code == 200
    assert refresh_resp.json()["access_token"]

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 200


def test_expired_token_returns_401(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "expired@example.com", "password": "strongpassword123"},
    )
    user_id = reg.json()["id"]
    expired_token = create_access_token(user_id, expires_delta=timedelta(seconds=-10))

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401


def test_tampered_token_returns_401(client: TestClient):
    reg = client.post(
        "/auth/register",
        json={"email": "tamper@example.com", "password": "strongpassword123"},
    )
    user_id = reg.json()["id"]
    valid_token = create_access_token(user_id)
    tampered = valid_token[:-4] + "XXXX"

    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401


def test_auth_rate_limit_returns_429(client: TestClient):
    app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    payload = {"email": "rate@example.com", "password": "wrongpassword"}
    assert client.post("/auth/login", json=payload).status_code == 401
    assert client.post("/auth/login", json=payload).status_code == 401
    assert client.post("/auth/login", json=payload).status_code == 429
