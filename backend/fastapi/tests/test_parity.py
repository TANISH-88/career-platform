"""
test_parity.py - Pytest wrapper for ml-training/check_parity.py.

Fails (does NOT skip) when ml-training/artifacts/pipeline.pkl is absent.
pipeline.pkl is committed to Git so it must always be present in CI.

Expects REPO_ROOT to be discoverable from this file's location:
    tests/ -> fastapi/ -> backend/ -> <repo_root>
"""

import pathlib
import sys

import pytest

TESTS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml-training" / "artifacts"
PIPELINE_PKL = ARTIFACTS_DIR / "pipeline.pkl"


def test_serving_parity():
    """Pipeline.pkl and separate pkl files must produce bit-identical probabilities.

    This test FAILS (not skips) when pipeline.pkl is absent.
    pipeline.pkl is committed to the repository and must always be present.
    If it is missing, that is a repository integrity error, not a skip condition.
    """
    if not PIPELINE_PKL.exists():
        pytest.fail(
            f"pipeline.pkl not found at {PIPELINE_PKL}. "
            "This file must be committed to Git for the parity gate to run in CI. "
            "Run 'git status ml-training/artifacts/' to diagnose."
        )

    sys.path.insert(0, str(REPO_ROOT / "ml-training"))
    from check_parity import check_parity

    ok = check_parity(ARTIFACTS_DIR)
    assert ok, (
        "Serving parity gate failed: pipeline.pkl and serving pkl files "
        "disagree. Run check_parity.py for details."
    )
