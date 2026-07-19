import pytest
from starlette.testclient import TestClient
from app.main import app

VALID_PAYLOAD = {
    "values": [5.0, 7.0, 6.0, 8.0, 0.6, 0.7, 0.5, 0.8, 0.4, 0.6, 0.7, 0.3, 0.5, 0.6]
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_predict_valid_input_returns_200(client):
    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "predicted_role" in body
    assert "top_3_roles" in body
    assert len(body["top_3_roles"]) == 3


def test_predict_wrong_length_returns_422(client):
    response = client.post("/predict", json={"values": [1.0, 2.0, 3.0]})
    assert response.status_code == 422


def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Backend running"}
