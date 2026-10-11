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

TECHNICAL_FEATURES = [
    "Computer Architecture",
    "Programming Skills",
    "Project Management",
    "Communication skills",
]
PERSONALITY_FEATURES = [
    "Openness",
    "Conscientousness",
    "Extraversion",
    "Agreeableness",
    "Emotional_Range",
    "Conversation",
    "Openness to Change",
    "Hedonism",
    "Self-enhancement",
    "Self-transcendence",
]
ALL_FEATURES = TECHNICAL_FEATURES + PERSONALITY_FEATURES

PROB_TOL = 1e-9


def run_pipeline_path(pipeline, df: pd.DataFrame) -> np.ndarray:
    """Run inference through the unified sklearn Pipeline."""
    return pipeline.predict_proba(df[ALL_FEATURES])


def run_serving_path(scaler, pca, frf, df: pd.DataFrame) -> np.ndarray:
    """Run inference through the separate scaler+pca+frf pkl files (serving path)."""
    tech_scaled = scaler.transform(df[TECHNICAL_FEATURES])
    tech_pca = pca.transform(tech_scaled)
    personality = df[PERSONALITY_FEATURES].values
    X = np.concatenate([personality, tech_pca], axis=1)
    return frf.predict_proba(X)


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
    frf = joblib.load(frf_path)
    scaler = joblib.load(scaler_path)
    pca = joblib.load(pca_path)

    print(f"[PARITY] Loading fixture: {FIXTURE_CSV}")
    df = pd.read_csv(FIXTURE_CSV)
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(df.columns[0], axis=1)
    print(f"[PARITY] Fixture rows: {len(df)}")

    proba_pipeline = run_pipeline_path(pipeline, df)
    proba_serving = run_serving_path(scaler, pca, frf, df)

    max_diff = float(np.max(np.abs(proba_pipeline - proba_serving)))
    top1_pipeline = np.argmax(proba_pipeline, axis=1)
    top1_serving = np.argmax(proba_serving, axis=1)
    top1_mismatches = int(np.sum(top1_pipeline != top1_serving))

    print(f"[PARITY] Max probability difference (pipeline vs serving): {max_diff:.2e}")
    print(f"[PARITY] Top-1 mismatches: {top1_mismatches}/{len(df)}")

    if max_diff > PROB_TOL:
        print(
            f"[PARITY FAIL] Max probability diff {max_diff:.2e} exceeds tolerance {PROB_TOL:.0e}"
        )
        return False
    if top1_mismatches > 0:
        print(f"[PARITY FAIL] {top1_mismatches} top-1 prediction(s) differ between pipeline and serving paths")
        return False

    print("[PARITY OK] pipeline.pkl and separate pkl files produce identical outputs.")
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
