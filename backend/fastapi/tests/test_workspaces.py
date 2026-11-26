import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config.constants import MAX_RESUME_BYTES, MAX_RESUME_VERSIONS_PER_WORKSPACE
from app.db.base import Base
from app.db.engine import create_db_engine
from app.db.models import Prediction, ResumeVersion, SkillProfile
from app.db.session import create_session_factory
from app.main import app
from app.schemas.resume import ParsedResumeResponse
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
        app.state.login_email_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        app.state.resume_rate_limiter = InMemoryRateLimiter(max_requests=50, window_seconds=60)
        yield test_client, session_factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _register_and_login(
    client: TestClient, email: str, password: str = "strongpassword123"
) -> dict[str, str]:
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
    assert client.post(f"/workspaces/{ws_id}/archive", headers=headers_b).status_code == 404
    assert client.post(f"/workspaces/{ws_id}/unarchive", headers=headers_b).status_code == 404
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

    del_resp = client.delete(f"/workspaces/{ws_id}", headers=headers)
    assert del_resp.status_code == 204
    assert client.get(f"/workspaces/{ws_id}", headers=headers).status_code == 404

    with session_factory() as db:
        assert db.scalars(select(SkillProfile)).all() == []
        assert db.scalars(select(Prediction)).all() == []


def test_workspace_archive_unarchive_and_last_active(workspace_client):
    client, _ = workspace_client
    headers = _register_and_login(client, "archive@example.com")

    # Initially no active workspaces -> 404
    assert client.get("/workspaces/last-active", headers=headers).status_code == 404

    ws1 = client.post("/workspaces", json={"name": "First"}, headers=headers).json()
    time.sleep(0.01)
    ws2 = client.post("/workspaces", json={"name": "Second"}, headers=headers).json()

    # ws2 was created more recently -> last-active is ws2
    last_resp = client.get("/workspaces/last-active", headers=headers)
    assert last_resp.status_code == 200
    assert last_resp.json()["id"] == ws2["id"]

    # Opening ws1 updates its last_opened_at -> last-active becomes ws1
    time.sleep(0.01)
    open_ws1 = client.get(f"/workspaces/{ws1['id']}", headers=headers)
    assert open_ws1.status_code == 200
    assert open_ws1.json()["last_opened_at"] >= ws1["last_opened_at"]
    assert client.get("/workspaces/last-active", headers=headers).json()["id"] == ws1["id"]

    # Archiving ws1 excludes it from default list and shifts last-active to ws2
    arch_ws1 = client.post(f"/workspaces/{ws1['id']}/archive", headers=headers)
    assert arch_ws1.status_code == 200
    assert arch_ws1.json()["archived_at"] is not None

    active_list = client.get("/workspaces", headers=headers).json()
    assert [w["id"] for w in active_list] == [ws2["id"]]

    full_list = client.get("/workspaces?include_archived=true", headers=headers).json()
    assert {w["id"] for w in full_list} == {ws1["id"], ws2["id"]}
    assert client.get("/workspaces/last-active", headers=headers).json()["id"] == ws2["id"]

    # Archiving ws2 too -> last-active returns 404
    assert client.post(f"/workspaces/{ws2['id']}/archive", headers=headers).status_code == 200
    assert client.get("/workspaces/last-active", headers=headers).status_code == 404

    # Unarchiving ws1 restores it to active list and last-active
    unarch_ws1 = client.post(f"/workspaces/{ws1['id']}/unarchive", headers=headers)
    assert unarch_ws1.status_code == 200
    assert unarch_ws1.json()["archived_at"] is None
    assert client.get("/workspaces/last-active", headers=headers).json()["id"] == ws1["id"]


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
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.setenv("MLFLOW_ENABLED", "false")

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass


def test_fail_closed_startup_unset_environment_with_non_sqlite_raises(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@db.example.com:5432/app")
    monkeypatch.setenv("JWT_SECRET", "some-secret")
    monkeypatch.setenv("MLFLOW_ENABLED", "false")

    with pytest.raises(RuntimeError, match="ENVIRONMENT"):
        with TestClient(app):
            pass


class _StubResumeParser:
    def __init__(self, extracted_text: str = "Alice Private SSN 999-11-2222 Python Engineer"):
        self.extracted_text = extracted_text
        self.calls = 0

    def extract_text(self, file_bytes: bytes, filename: str) -> str:
        return self.extracted_text

    def extract_skills(self, text: str) -> ParsedResumeResponse:
        self.calls += 1
        return ParsedResumeResponse(
            computer_architecture=7.0,
            programming_skills=8.0,
            project_management=6.0,
            communication_skills=7.0,
            openness=6.5,
            conscientiousness=7.0,
            extraversion=5.5,
            agreeableness=6.0,
            emotional_range=5.0,
            conversation=6.0,
            openness_change=6.5,
            hedonism=4.5,
            self_enhancement=6.0,
            self_transcendence=6.5,
        )


def test_resume_version_create_list_delete_and_privacy(workspace_client):
    client, session_factory = workspace_client
    stub = _StubResumeParser()
    client.app.state.resume_parser = stub
    headers = _register_and_login(client, "cp21owner@example.com")

    ws_id = client.post("/workspaces", json={"name": "CP21 Track"}, headers=headers).json()["id"]

    # 1) Missing consent -> 422 before calling Gemini parser
    no_consent = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("alice_private_cv.pdf", b"%PDF-1.4 Alice Private SSN", "application/pdf")},
        data={"consent": "false"},
        headers=headers,
    )
    assert no_consent.status_code == 422
    assert stub.calls == 0

    # 2) Valid upload with consent -> 201 + derived scores + ML prediction
    v1_resp = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("alice_private_cv.pdf", b"%PDF-1.4 Alice Private SSN", "application/pdf")},
        data={"consent": "true"},
        headers=headers,
    )
    assert v1_resp.status_code == 201
    v1 = v1_resp.json()
    assert v1["version_number"] == 1
    assert v1["parsed_skills"] == SAMPLE_UI_VALUES
    assert v1["predicted_role"]
    assert len(v1["top_k"]) == 3
    assert v1["model_version"] == "frf_v1"
    assert v1["parser_model"]
    assert stub.calls == 1

    # Upload second version (DOCX)
    v2_resp = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={
            "file": (
                "alice_v2.docx",
                b"PK\x03\x04 docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"consent": "true"},
        headers=headers,
    )
    assert v2_resp.status_code == 201
    v2 = v2_resp.json()
    assert v2["version_number"] == 2

    # Verify list ordering (newest first)
    listed = client.get(f"/workspaces/{ws_id}/resume-versions", headers=headers)
    assert listed.status_code == 200
    assert [item["version_number"] for item in listed.json()] == [2, 1]

    # Verify strict privacy invariant: NO raw file bytes, filename, or personal text in DB
    with session_factory() as db:
        rows = db.scalars(select(ResumeVersion)).all()
        assert len(rows) == 2
        column_names = set(ResumeVersion.__table__.columns.keys())
        assert not ({"raw_text", "resume_text", "file_bytes", "filename"} & column_names)
        serialized = repr([(r.parsed_skills, r.predicted_role, r.top_k, r.model_version, r.parser_model) for r in rows])
        assert "Alice" not in serialized
        assert "999-11-2222" not in serialized
        assert "alice_private_cv.pdf" not in serialized

    # Delete v1 individually
    assert client.delete(f"/workspaces/{ws_id}/resume-versions/{v1['id']}", headers=headers).status_code == 204
    after_del = client.get(f"/workspaces/{ws_id}/resume-versions", headers=headers).json()
    assert [item["version_number"] for item in after_del] == [2]

    # Uploading again increments monotonically to v3
    v3 = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("cv3.pdf", b"%PDF-1.4", "application/pdf")},
        data={"consent": "true"},
        headers=headers,
    ).json()
    assert v3["version_number"] == 3

    # Delete all resume versions in workspace
    assert client.delete(f"/workspaces/{ws_id}/resume-versions", headers=headers).status_code == 204
    assert client.get(f"/workspaces/{ws_id}/resume-versions", headers=headers).json() == []
    # Workspace itself remains intact
    assert client.get(f"/workspaces/{ws_id}", headers=headers).status_code == 200


def test_resume_version_isolation_and_cascade(workspace_client):
    client, session_factory = workspace_client
    client.app.state.resume_parser = _StubResumeParser()
    headers_a = _register_and_login(client, "rv_a@example.com")
    headers_b = _register_and_login(client, "rv_b@example.com")

    ws_a = client.post("/workspaces", json={"name": "User A"}, headers=headers_a).json()["id"]
    ws_b = client.post("/workspaces", json={"name": "User B"}, headers=headers_b).json()["id"]

    ver_a = client.post(
        f"/workspaces/{ws_a}/resume-versions",
        files={"file": ("a.pdf", b"%PDF", "application/pdf")},
        data={"consent": "true"},
        headers=headers_a,
    ).json()

    # User B cannot access/upload/delete User A's resume versions (all 404)
    assert (
        client.post(
            f"/workspaces/{ws_a}/resume-versions",
            files={"file": ("b.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert client.get(f"/workspaces/{ws_a}/resume-versions", headers=headers_b).status_code == 404
    assert client.delete(f"/workspaces/{ws_a}/resume-versions/{ver_a['id']}", headers=headers_b).status_code == 404
    assert client.delete(f"/workspaces/{ws_a}/resume-versions", headers=headers_b).status_code == 404
    # User B also cannot delete User A's version_id through User B's own workspace
    assert client.delete(f"/workspaces/{ws_b}/resume-versions/{ver_a['id']}", headers=headers_b).status_code == 404

    # Deleting User A's workspace cascades to resume_versions
    assert client.delete(f"/workspaces/{ws_a}", headers=headers_a).status_code == 204
    with session_factory() as db:
        assert db.scalars(select(ResumeVersion)).all() == []


def test_resume_version_upload_limits_and_rate_limiting(workspace_client):
    client, _ = workspace_client
    stub = _StubResumeParser()
    client.app.state.resume_parser = stub
    headers = _register_and_login(client, "limits@example.com")
    ws_id = client.post("/workspaces", json={"name": "Limits"}, headers=headers).json()["id"]

    # 1) Size limit -> 413
    oversized = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("big.pdf", b"x" * (MAX_RESUME_BYTES + 1), "application/pdf")},
        data={"consent": "true"},
        headers=headers,
    )
    assert oversized.status_code == 413

    # 2) Unsupported media type -> 415
    bad_type = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        data={"consent": "true"},
        headers=headers,
    )
    assert bad_type.status_code == 415

    # 3) Per-workspace version limit (MAX_RESUME_VERSIONS_PER_WORKSPACE) -> 409 Conflict
    for idx in range(MAX_RESUME_VERSIONS_PER_WORKSPACE):
        r = client.post(
            f"/workspaces/{ws_id}/resume-versions",
            files={"file": (f"v{idx}.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers,
        )
        assert r.status_code == 201

    calls_before_cap = stub.calls
    over_cap = client.post(
        f"/workspaces/{ws_id}/resume-versions",
        files={"file": ("v11.pdf", b"%PDF", "application/pdf")},
        data={"consent": "true"},
        headers=headers,
    )
    assert over_cap.status_code == 409
    assert stub.calls == calls_before_cap

    # 4) Rate limiting on both /workspaces/{id}/resume-versions and /parse-resume -> 429
    client.app.state.resume_rate_limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert (
        client.post(
            "/parse-resume",
            files={"file": ("r1.pdf", b"%PDF", "application/pdf")},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/parse-resume",
            files={"file": ("r2.pdf", b"%PDF", "application/pdf")},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/parse-resume",
            files={"file": ("r3.pdf", b"%PDF", "application/pdf")},
        ).status_code
        == 429
    )

    client.app.state.resume_rate_limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    # Delete 1 version first so capacity is open again
    first_id = client.get(f"/workspaces/{ws_id}/resume-versions", headers=headers).json()[0]["id"]
    assert client.delete(f"/workspaces/{ws_id}/resume-versions/{first_id}", headers=headers).status_code == 204
    assert (
        client.post(
            f"/workspaces/{ws_id}/resume-versions",
            files={"file": ("ok.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers,
        ).status_code
        == 201
    )
    # Next call hits 429
    assert (
        client.post(
            f"/workspaces/{ws_id}/resume-versions",
            files={"file": ("rl.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers,
        ).status_code
        == 429
    )


def test_concurrent_resume_version_limit_enforced(workspace_client):
    """Concurrent uploads near capacity must never exceed MAX_RESUME_VERSIONS_PER_WORKSPACE."""
    from concurrent.futures import ThreadPoolExecutor

    client, session_factory = workspace_client

    class _SlowStubParser(_StubResumeParser):
        def extract_skills(self, text: str) -> ParsedResumeResponse:
            time.sleep(0.05)
            return super().extract_skills(text)

    client.app.state.resume_parser = _SlowStubParser()
    headers = _register_and_login(client, "concurrent_rv@example.com")
    ws_id = client.post("/workspaces", json={"name": "Concurrent"}, headers=headers).json()["id"]

    # Fill to MAX - 1 sequentially
    for idx in range(MAX_RESUME_VERSIONS_PER_WORKSPACE - 1):
        r = client.post(
            f"/workspaces/{ws_id}/resume-versions",
            files={"file": (f"v{idx}.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers,
        )
        assert r.status_code == 201

    # Fire 6 concurrent uploads simultaneously; all 6 pass pre-LLM capacity check,
    # but atomic lock + re-check must allow only 1 to commit and reject 5 with 409.
    def _upload(i: int) -> int:
        resp = client.post(
            f"/workspaces/{ws_id}/resume-versions",
            files={"file": (f"race_{i}.pdf", b"%PDF", "application/pdf")},
            data={"consent": "true"},
            headers=headers,
        )
        return resp.status_code

    with ThreadPoolExecutor(max_workers=6) as pool:
        statuses = list(pool.map(_upload, range(6)))

    assert statuses.count(201) == 1
    assert statuses.count(409) == 5

    with session_factory() as db:
        rows = db.scalars(
            select(ResumeVersion)
            .where(ResumeVersion.workspace_id == ws_id)
            .order_by(ResumeVersion.version_number.asc())
        ).all()
        assert len(rows) == MAX_RESUME_VERSIONS_PER_WORKSPACE
        assert [row.version_number for row in rows] == list(
            range(1, MAX_RESUME_VERSIONS_PER_WORKSPACE + 1)
        )
