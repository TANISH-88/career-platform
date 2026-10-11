import logging
import os
import joblib
import numpy as np
import pandas as pd

from app.config.constants import (
    TECHNICAL_FEATURES,
    PERSONALITY_FEATURES,
    UI_MIN,
    UI_MAX,
    TECH_MAX,
    PERSONALITY_MAX,
)

logger = logging.getLogger(__name__)


class FeatureMapper:
    def __init__(self, models_dir: str = "models/") -> None:
        scaler_path = os.path.join(models_dir, "scaler.pkl")
        pca_path = os.path.join(models_dir, "pca.pkl")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"scaler.pkl not found at: {scaler_path}")
        if not os.path.exists(pca_path):
            raise FileNotFoundError(f"pca.pkl not found at: {pca_path}")
        self.scaler = joblib.load(scaler_path)
        self.pca = joblib.load(pca_path)

    def transform_training_units(self, values: list[float]) -> np.ndarray:
        """
        Original transform behavior: expects raw values directly in training scale
        (technical in [0, 6], personality in [0, 1]).
        Preserved for parity checks, CSV validation, and low-level testing.
        """
        if len(values) != 14:
            raise ValueError(f"Expected exactly 14 values, got {len(values)}")
        all_features = TECHNICAL_FEATURES + PERSONALITY_FEATURES
        df = pd.DataFrame([values], columns=all_features)
        scaled_technical = self.scaler.transform(df[TECHNICAL_FEATURES])
        pca_components = self.pca.transform(scaled_technical)
        personality_array = df[PERSONALITY_FEATURES].values
        result = np.concatenate([personality_array, pca_components], axis=1)
        return result

    def transform(self, values: list[float]) -> np.ndarray:
        """
        Serving-boundary transform: expects UI-scale inputs in [UI_MIN, UI_MAX] (1–10).
        Clamps values outside [UI_MIN, UI_MAX] with a warning log, converts to training
        units via linear scaling:
          technical:   (v - UI_MIN) / (UI_MAX - UI_MIN) * TECH_MAX
          personality: (v - UI_MIN) / (UI_MAX - UI_MIN) * PERSONALITY_MAX
        then applies standard scaler and PCA.
        """
        if len(values) != 14:
            raise ValueError(f"Expected exactly 14 values, got {len(values)}")

        clamped_count = sum(1 for v in values if v < UI_MIN or v > UI_MAX)
        if clamped_count > 0:
            logger.warning(
                f"FeatureMapper: {clamped_count} of 14 input values were outside "
                f"[{UI_MIN}, {UI_MAX}] and were clamped."
            )

        clamped = [min(max(float(v), UI_MIN), UI_MAX) for v in values]
        ui_span = UI_MAX - UI_MIN

        # First 4 values are technical, next 10 are personality
        training_units = []
        for v in clamped[:4]:
            training_units.append((v - UI_MIN) / ui_span * TECH_MAX)
        for v in clamped[4:]:
            training_units.append((v - UI_MIN) / ui_span * PERSONALITY_MAX)

        return self.transform_training_units(training_units)
