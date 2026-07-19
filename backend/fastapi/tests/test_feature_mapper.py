import pytest
from app.services.feature_mapper import FeatureMapper
from app.config.constants import TECHNICAL_FEATURES, PERSONALITY_FEATURES


def test_feature_mapper_smoke(models_dir):
    mapper = FeatureMapper(models_dir=models_dir)
    assert mapper is not None


def test_feature_mapper_output_shape(feature_mapper, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    for _, row in sample_rows.iterrows():
        values = row[feature_cols].tolist()
        result = feature_mapper.transform(values)
        assert result.shape == (1, 12), f"Expected shape (1, 12), got {result.shape}"


def test_feature_mapper_rejects_too_few_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([0.5] * 13)


def test_feature_mapper_rejects_too_many_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([0.5] * 15)
