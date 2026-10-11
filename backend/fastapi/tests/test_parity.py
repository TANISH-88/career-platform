"""
test_parity.py - Pytest wrapper for ml-training/check_parity.py.

Skips automatically when ml-training/artifacts/pipeline.pkl is absent
(pipeline.pkl is DVC-tracked and not committed to git).

Expects REPO_ROOT to be discoverable from this file's location:
    tests/ -> fastapi/ -> backend/ -> <repo_root>
"""

import pathlib
import pytest

TESTS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent.parent
ARTIFACTS_DIR = REPO_ROOT / "ml-training" / "artifacts"
PIPELINE_PKL = ARTIFACTS_DIR / "pipeline.pkl"


@pytest.mark.skipif(
    not PIPELINE_PKL.exists(),
    reason="pipeline.pkl not found (DVC-tracked; run `dvc pull` to enable this test)",
)
def test_serving_parity():
    """Pipeline.pkl and separate pkl files must produce bit-identical probabilities."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "ml-training"))
    from check_parity import check_parity

    ok = check_parity(ARTIFACTS_DIR)
    assert ok, (
        "Serving parity gate failed: pipeline.pkl and serving pkl files "
        "disagree. Run check_parity.py for details."
    )
