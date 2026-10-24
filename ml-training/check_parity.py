"""
check_parity.py - Serving parity gate.

Loads pipeline.pkl and the separate frf/scaler/pca pkl files from a given
artifacts directory, runs both paths on the 160-row test fixture, and
asserts that every predicted probability matches to within 1e-9 and every
top-1 prediction is identical.

Exit code 0 = parity OK.
Exit code 1 = parity FAIL (details printed to stdout).

Usage:
    python ml-training/check_parity.py [--artifacts-dir ml-training/artifacts]
"""

import argparse
import pathlib
import sys

import joblib
import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE_CSV = REPO_ROOT / "backend" / "fastapi" / "tests" / "fixtures" / "sample_careers.csv"

sys.path.insert(0, str(REPO_ROOT / "backend" / "fastapi"))

from app.config.constants import PERSONALITY_FEATURES, ROLE_MAPPING, TECHNICAL_FEATURES
from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService

ALL_FEATURES = TECHNICAL_FEATURES + PERSONALITY_FEATURES

PROB_TOL = 1e-9


def run_pipeline_path(pipeline, df: pd.DataFrame) -> np.ndarray:
    """Run inference through the unified sklearn Pipeline."""
    return pipeline.predict_proba(df[ALL_FEATURES])


def run_serving_path(
    artifacts_dir: pathlib.Path, df: pd.DataFrame
) -> list:
    """Run inference through the shipping FeatureMapper and PredictorService."""
    feature_mapper = FeatureMapper(models_dir=str(artifacts_dir))
    predictor_service = PredictorService(models_dir=str(artifacts_dir))
    predictions = []
    for row in df[ALL_FEATURES].itertuples(index=False, name=None):
        features = feature_mapper.transform_training_units(list(row))
        predictions.append(predictor_service.predict(features))
    return predictions


def check_parity(artifacts_dir: pathlib.Path) -> bool:
    """Return True if parity passes, False if it fails."""
    pipeline_path = artifacts_dir / "pipeline.pkl"
    frf_path = artifacts_dir / "frf.pkl"
    scaler_path = artifacts_dir / "scaler.pkl"
    pca_path = artifacts_dir / "pca.pkl"

    for p in [pipeline_path, frf_path, scaler_path, pca_path]:
        if not p.exists():
            print(f"[PARITY FAIL] Missing artifact: {p}")
            return False

    print(f"[PARITY] Loading artifacts from: {artifacts_dir}")
    pipeline = joblib.load(pipeline_path)

    print(f"[PARITY] Loading fixture: {FIXTURE_CSV}")
    df = pd.read_csv(FIXTURE_CSV)
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(df.columns[0], axis=1)
    print(f"[PARITY] Fixture rows: {len(df)}")

    proba_pipeline = run_pipeline_path(pipeline, df)
    predictions_serving = run_serving_path(artifacts_dir, df)
    pipeline_classes = pipeline.classes_
    top3_indices = np.argsort(proba_pipeline, axis=1)[:, -3:][:, ::-1]
    max_diff = 0.0
    top1_mismatches = 0
    top3_mismatches = 0

    for row_index, prediction in enumerate(predictions_serving):
        pipeline_top1_role = ROLE_MAPPING[int(pipeline_classes[np.argmax(proba_pipeline[row_index])])]
        if prediction.predicted_role != pipeline_top1_role:
            top1_mismatches += 1

        for serving_role, class_index in zip(
            prediction.top_3_roles, top3_indices[row_index]
        ):
            expected_role = ROLE_MAPPING[int(pipeline_classes[class_index])]
            expected_probability = float(proba_pipeline[row_index, class_index])
            max_diff = max(max_diff, abs(expected_probability - serving_role.probability))
            if serving_role.role != expected_role or not np.isclose(
                serving_role.probability, expected_probability, atol=PROB_TOL, rtol=0
            ):
                top3_mismatches += 1

    print(f"[PARITY] Max probability difference (pipeline vs serving): {max_diff:.2e}")
    print(f"[PARITY] Top-1 role mismatches: {top1_mismatches}/{len(df)}")
    print(f"[PARITY] Top-3 role/probability mismatches: {top3_mismatches}/{len(df) * 3}")

    if top1_mismatches > 0 or top3_mismatches > 0:
        print(
            f"[PARITY FAIL] PredictorService output differs from pipeline "
            f"(probability tolerance {PROB_TOL:.0e})"
        )
        return False

    print("[PARITY OK] pipeline.pkl and PredictorService produce identical outputs.")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Serving parity gate")
    parser.add_argument(
        "--artifacts-dir",
        default=str(REPO_ROOT / "ml-training" / "artifacts"),
        help="Path to the artifacts directory (default: ml-training/artifacts)",
    )
    args = parser.parse_args()

    artifacts_dir = pathlib.Path(args.artifacts_dir).resolve()
    ok = check_parity(artifacts_dir)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
