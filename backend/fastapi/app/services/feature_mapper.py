import os
import joblib
import numpy as np
import pandas as pd

from app.config.constants import TECHNICAL_FEATURES, PERSONALITY_FEATURES


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

    def transform(self, values: list[float]) -> np.ndarray:
        if len(values) != 14:
            raise ValueError(f"Expected exactly 14 values, got {len(values)}")
        all_features = TECHNICAL_FEATURES + PERSONALITY_FEATURES
        df = pd.DataFrame([values], columns=all_features)
        scaled_technical = self.scaler.transform(df[TECHNICAL_FEATURES])
        pca_components = self.pca.transform(scaled_technical)
        personality_array = df[PERSONALITY_FEATURES].values
        result = np.concatenate([personality_array, pca_components], axis=1)
        return result
