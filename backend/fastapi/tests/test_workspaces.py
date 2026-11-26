import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.base import Base
from app.db.engine import create_db_engine
from app.db.models import Prediction, SkillProfile
from app.db.session import create_session_factory
from app.main import app
from app.services.rate_limiter import InMemoryRateLimiter

SAMPLE_UI_VALUES = [7.0, 8.0, 6.0, 7.0, 6.5, 7.0, 5.5, 6.0, 5.0, 6.0, 6.5, 4.5, 6.0, 6.5]


@pytest.fixture()
def workspace_client(monkeypatch):
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
        app.state.auth_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        yield test_client, session_factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_and_login(client: TestClient, email: str, password: str = "strongpassword123") -> dict[str, str]:
    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_workspace_isolation_returns_404_for_other_user(workspace_client):
    client, _ = workspace_client
    headers_a = _register_and_login(client, "usera@example.com")
    headers_b = _register_and_login(client, "userb@example.com")

    created = client.post("/workspaces", json={"name": "User A Workspace"}, headers=headers_a)
    assert created.status_code == 201
    ws_id = created.json()["id"]

    assert client.get(f"/workspaces/{ws_id}", headers=headers_b).status_code == 404
    assert client.get(f"/workspaces/{ws_id}/history", headers=headers_b).status_code == 404
    assert (
        client.post(
            f"/workspaces/{ws_id}/predict",
            json={"values": SAMPLE_UI_VALUES},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert client.delete(f"/workspaces/{ws_id}", headers=headers_b).status_code == 404


def test_workspace_predict_history_and_delete_cascade(workspace_client):
    client, session_factory = workspace_client
    headers = _register_and_login(client, "owner@example.com")

    created = client.post("/workspaces", json={"name": "Backend Track"}, headers=headers)
    assert created.status_code == 201
    ws_id = created.json()["id"]

    listed = client.get("/workspaces", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == ws_id

    pred_resp = client.post(
        f"/workspaces/{ws_id}/predict",
        json={"values": SAMPLE_UI_VALUES},
        headers=headers,
    )
    assert pred_resp.status_code == 200
    pred_data = pred_resp.json()
    assert "predicted_role" in pred_data
    assert len(pred_data["top_3_roles"]) == 3
    assert pred_data["model_version"] == "frf_v1"

    history_resp = client.get(f"/workspaces/{ws_id}/history", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["values"] == SAMPLE_UI_VALUES
    assert history[0]["predicted_role"] == pred_data["predicted_role"]
    assert history[0]["top_k"] == pred_data["top_3_roles"]

    # Delete workspace and verify cascade in DB
    del_resp = client.delete(f"/workspaces/{ws_id}", headers=headers)
    assert del_resp.status_code == 204
    assert client.get(f"/workspaces/{ws_id}", headers=headers).status_code == 404

    with session_factory() as db:
        assert db.scalars(select(SkillProfile)).all() == []
        assert db.scalars(select(Prediction)).all() == []


def test_anonymous_predict_remains_unchanged(workspace_client):
    client, session_factory = workspace_client
    resp = client.post("/predict", json={"values": SAMPLE_UI_VALUES})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"predicted_role", "top_3_roles"}
    assert len(data["top_3_roles"]) == 3

    with session_factory() as db:
        assert db.scalars(select(SkillProfile)).all() == []
        assert db.scalars(select(Prediction)).all() == []


def test_production_startup_without_jwt_secret_raises(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("MLFLOW_ENABLED", "false")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass
