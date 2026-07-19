import pytest
from app.services.predictor import PredictorService
from app.config.constants import ROLE_MAPPING, TECHNICAL_FEATURES, PERSONALITY_FEATURES


def test_predictor_service_smoke(models_dir):
    service = PredictorService(models_dir=models_dir)
    assert service is not None


def test_predicted_role_is_valid(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    assert result.predicted_role in ROLE_MAPPING.values(), (
        f"predicted_role '{result.predicted_role}' not in ROLE_MAPPING"
    )


def test_top_3_roles_count(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    assert len(result.top_3_roles) == 3


def test_top_3_roles_probabilities_in_range(feature_mapper, predictor_service, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    row = sample_rows.iloc[0]
    features = feature_mapper.transform(row[feature_cols].tolist())
    result = predictor_service.predict(features)
    for entry in result.top_3_roles:
        assert 0.0 <= entry.probability <= 1.0, (
            f"probability {entry.probability} out of range [0.0, 1.0]"
        )


def test_predictor_service_bad_models_dir():
    with pytest.raises(FileNotFoundError):
        PredictorService(models_dir="/nonexistent/path")
