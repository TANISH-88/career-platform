import logging
import pytest
import numpy as np

from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService
from app.config.constants import (
    TECHNICAL_FEATURES,
    PERSONALITY_FEATURES,
)


def test_feature_mapper_smoke(models_dir):
    mapper = FeatureMapper(models_dir=models_dir)
    assert mapper is not None


def test_feature_mapper_output_shape(feature_mapper, sample_rows):
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    for _, row in sample_rows.iterrows():
        values = row[feature_cols].tolist()
        # Direct training units transform produces shape (1, 12)
        result_direct = feature_mapper.transform_training_units(values)
        assert result_direct.shape == (1, 12), f"Expected shape (1, 12), got {result_direct.shape}"

        # UI-scale transform also produces shape (1, 12)
        ui_values = [v * 9.0 / 6.0 + 1.0 for v in values[:4]] + [v * 9.0 + 1.0 for v in values[4:]]
        result_ui = feature_mapper.transform(ui_values)
        assert result_ui.shape == (1, 12), f"Expected shape (1, 12), got {result_ui.shape}"


def test_feature_mapper_rejects_too_few_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([5.0] * 13)


def test_feature_mapper_rejects_too_many_values(feature_mapper):
    with pytest.raises(ValueError, match="Expected exactly 14 values"):
        feature_mapper.transform([5.0] * 15)


def test_boundary_mapping_ui_to_training_scale(feature_mapper):
    """
    4a. UI 1 maps to 0 and UI 10 maps to scale max for both technical [0, 6]
    and personality [0, 1] groups.
    """
    # UI_MIN (all 1.0) maps to technical min (0.0) and personality min (0.0)
    min_ui = [1.0] * 14
    min_train = [0.0] * 14
    res_min_from_ui = feature_mapper.transform(min_ui)
    res_min_direct = feature_mapper.transform_training_units(min_train)
    np.testing.assert_allclose(res_min_from_ui, res_min_direct, atol=1e-9)

    # UI_MAX (all 10.0) maps to TECH_MAX (6.0) and PERSONALITY_MAX (1.0)
    max_ui = [10.0] * 14
    max_train = [6.0] * 4 + [1.0] * 10
    res_max_from_ui = feature_mapper.transform(max_ui)
    res_max_direct = feature_mapper.transform_training_units(max_train)
    np.testing.assert_allclose(res_max_from_ui, res_max_direct, atol=1e-9)


def test_round_trip_conversion_over_fixture(feature_mapper, sample_rows):
    """
    4b. to_ui then transform equals transform_training_units within 1e-9 over
    the 160 fixture rows.
    """
    feature_cols = TECHNICAL_FEATURES + PERSONALITY_FEATURES
    for _, row in sample_rows.iterrows():
        raw = row[feature_cols].tolist()
        # Convert training units to UI units:
        # tech in [0, 6] -> v * 9/6 + 1
        # pers in [0, 1] -> v * 9 + 1
        ui_vals = [raw[i] * 9.0 / 6.0 + 1.0 for i in range(4)] + [
            raw[i] * 9.0 + 1.0 for i in range(4, 14)
        ]
        res_ui = feature_mapper.transform(ui_vals)
        res_direct = feature_mapper.transform_training_units(raw)
        np.testing.assert_allclose(res_ui, res_direct, atol=1e-9)


def test_personality_sensitivity(feature_mapper, predictor_service):
    """
    4c. For fixed technical inputs, changing personality from all 1 to all 10
    must change the probability vector for at least one technical combination.
    """
    tech_candidates = [
        [1.0, 1.0, 1.0, 1.0],
        [5.0, 5.0, 5.0, 5.0],
        [8.0, 9.0, 7.0, 8.0],
    ]
    detected_change = False
    for tech in tech_candidates:
        p_low = tech + [1.0] * 10
        p_high = tech + [10.0] * 10
        X_low = feature_mapper.transform(p_low)
        X_high = feature_mapper.transform(p_high)
        proba_low = predictor_service.frf_model.predict_proba(X_low)[0]
        proba_high = predictor_service.frf_model.predict_proba(X_high)[0]
        if not np.allclose(proba_low, proba_high, atol=1e-4):
            detected_change = True
            break
    assert detected_change, "Changing personality from 1 to 10 failed to affect model probabilities"


@pytest.mark.allow_clamping
def test_clamp_out_of_bounds_inputs(feature_mapper, caplog):
    """
    4d. Inputs outside [1, 10] are clamped to [1, 10] and log a WARNING.
    """
    with caplog.at_level(logging.WARNING):
        # Frontend sends 0 for empty inputs, or user enters > 10
        oob_input = [0.0] * 4 + [15.0] * 10
        clamped_input = [1.0] * 4 + [10.0] * 10

        res_oob = feature_mapper.transform(oob_input)
        res_clamped = feature_mapper.transform(clamped_input)

        np.testing.assert_allclose(res_oob, res_clamped, atol=1e-9)
        assert any("clamped" in record.message for record in caplog.records)

