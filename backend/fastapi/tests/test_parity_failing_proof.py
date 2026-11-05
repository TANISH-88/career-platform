"""
test_parity_failing_proof.py

Proves that the parity gate detects a real parity-breaking change.

This test deliberately passes a wrong (identity/constant) model to check_parity
and asserts that it returns False (failing proof). It then passes the real model
and asserts that it returns True (green proof).

This is not a simplified duplicate implementation — it uses the real check_parity
function that exercises FeatureMapper and PredictorService (the shipping code).
"""

import pathlib
import shutil
import sys
import tempfile

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

TESTS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml-training" / "artifacts"
PIPELINE_PKL = ARTIFACTS_DIR / "pipeline.pkl"

sys.path.insert(0, str(REPO_ROOT / "ml-training"))


def test_parity_gate_passes_with_correct_model():
    """Real artifacts must produce parity OK (baseline sanity check)."""
    if not PIPELINE_PKL.exists():
        pytest.fail(
            f"pipeline.pkl not found at {PIPELINE_PKL}. "
            "This file must be committed to Git."
        )
    from check_parity import check_parity
    assert check_parity(ARTIFACTS_DIR) is True, (
        "Parity gate failed with correct artifacts — baseline is broken."
    )


def test_parity_gate_fails_with_wrong_model():
    """Parity gate must return False when frf.pkl is replaced with a wrong model.

    This is the failing proof: if someone promotes an incompatible frf.pkl,
    check_parity catches it and returns False.
    """
    if not PIPELINE_PKL.exists():
        pytest.fail(
            f"pipeline.pkl not found at {PIPELINE_PKL}. "
            "This file must be committed to Git."
        )
    from check_parity import check_parity

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        # Copy real artifacts into temp dir
        for fname in ("pipeline.pkl", "scaler.pkl", "pca.pkl"):
            shutil.copy(ARTIFACTS_DIR / fname, tmp_dir / fname)

        # Build a deliberately wrong RF that always predicts class 0
        # It has the same interface but produces completely different outputs.
        wrong_rf = RandomForestClassifier(n_estimators=1, random_state=0, max_depth=1)
        # Fit on 2-sample trivial data with 12 features (10 personality + 2 PCA)
        wrong_rf.fit(np.zeros((2, 12)), [0, 1])
        joblib.dump(wrong_rf, tmp_dir / "frf.pkl")

        # Parity must fail: the wrong RF disagrees with the pipeline
        result = check_parity(tmp_dir)
        assert result is False, (
            "Parity gate did NOT catch a deliberately wrong frf.pkl — "
            "the failing proof is broken."
        )

