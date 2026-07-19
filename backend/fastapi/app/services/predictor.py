import os
import joblib
import numpy as np

from app.config.constants import ROLE_MAPPING
from app.schemas.prediction import PredictionResult, TopRole


class PredictorService:
    def __init__(self, models_dir: str = "models/") -> None:
        model_path = os.path.join(models_dir, "frf.pkl")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"frf.pkl not found at: {model_path}")
        self.frf_model = joblib.load(model_path)

    def predict(self, features: np.ndarray) -> PredictionResult:
        predicted_index = int(self.frf_model.predict(features)[0])
        predicted_role = ROLE_MAPPING[predicted_index]
        proba = self.frf_model.predict_proba(features)
        top3_indices = np.argsort(proba[0])[-3:][::-1]
        top_3_roles = [
            TopRole(role=ROLE_MAPPING[int(idx)], probability=float(proba[0][idx]))
            for idx in top3_indices
        ]
        return PredictionResult(predicted_role=predicted_role, top_3_roles=top_3_roles)
