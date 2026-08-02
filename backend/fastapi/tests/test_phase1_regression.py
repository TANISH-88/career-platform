from importlib import reload

import pytest
from starlette.testclient import TestClient

from app.config.constants import ROLE_MAPPING, TECHNICAL_FEATURES, PERSONALITY_FEATURES
from app.main import app
from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService

VALID_PAYLOAD = {
    "values": [5.0, 7.0, 6.0, 8.0, 0.6, 0.7, 0.5, 0.8, 0.4, 0.6, 0.7, 0.3, 0.5, 0.6]
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def feature_mapper(models_dir):
    return FeatureMapper(models_dir=models_dir)


@pytest.fixture(scope="session")
def predictor_service(models_dir):
    return PredictorService(models_dir=models_dir)


def test_phase1_feature_mapper_smoke(models_dir):
    mapper = FeatureMapper(models_dir=models_dir)
    assert mapper is not None


def test_phase1_feature_mapper_output_shape(feature_mapper, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    for _, row in sample_rows.iterrows():
        values = row[feature_cols].tolist()
        result = feature_mapper.transform(values)
        assert result.shape == (1, 12), f"Expected shape (1, 12), got {result.shape}"


def test_phase1_feature_mapper_rejects_too_few_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([0.5] * 13)


def test_phase1_feature_mapper_rejects_too_many_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([0.5] * 15)


def test_phase1_predictor_service_smoke(models_dir):
    service = PredictorService(models_dir=models_dir)
    assert service is not None


def test_phase1_predicted_role_is_valid(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    assert result.predicted_role in ROLE_MAPPING.values(), (
        f"predicted_role '{result.predicted_role}' not in ROLE_MAPPING"
    )


def test_phase1_top_3_roles_count(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    assert len(result.top_3_roles) == 3


def test_phase1_top_3_roles_probabilities_in_range(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    for entry in result.top_3_roles:
        assert 0.0 <= entry.probability <= 1.0, (
            f"probability {entry.probability} out of range [0.0, 1.0]"
        )


def test_phase1_predictor_service_bad_models_dir():
    with pytest.raises(FileNotFoundError):
        PredictorService(models_dir="/nonexistent/path")


def test_phase1_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Backend running"}


def test_phase1_predict_valid_input_returns_200(client):
    response = client.post("/predict", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "predicted_role" in body
    assert "top_3_roles" in body
    assert len(body["top_3_roles"]) == 3


def test_phase1_predict_wrong_length_returns_422(client):
    response = client.post("/predict", json={"values": [1.0, 2.0, 3.0]})
    assert response.status_code == 422


def test_startup_fails_without_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    import app.main as app_main

    reloaded = reload(app_main)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        with TestClient(reloaded.app):
            pass
