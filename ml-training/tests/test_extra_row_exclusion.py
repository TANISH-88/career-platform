"""
test_extra_row_exclusion.py

Proves that unknown-origin extra rows (indices 9,179–10,178 in CareerMapping1.csv)
are excluded from the default training dataset loaded by train.load_data().

The 1,000 extra rows have fractional technical feature values in [0, 1] while
the 9,179 raw rows always have integer technical values in [0, 6].
Origin: unknown, excluded — see MODEL_CARD.md § Data Quality.
"""

import pathlib
import sys

import pandas as pd
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"
sys.path.insert(0, str(REPO_ROOT / "ml-training"))

import train  # noqa: E402


TECHNICAL_FEATURES = train.TECHNICAL_FEATURES


def _has_fractional_technical(df: pd.DataFrame) -> bool:
    """Return True if any row has non-integer technical feature values."""
    for col in TECHNICAL_FEATURES:
        if not (df[col].apply(lambda v: float(v) == int(float(v))).all()):
            return True
    return False


@pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason="CareerMapping1.csv not present in this checkout",
)
def test_default_load_excludes_extra_rows():
    """load_data() with exclude_extra_rows=True (default) must return only the 9,179 raw rows."""
    df = train.load_data(str(DATA_PATH), exclude_extra_rows=True)
    assert len(df) == 9_179, (
        f"Expected 9,179 raw rows after exclusion, got {len(df)}. "
        "Unknown-origin extra rows may have leaked into training data."
    )
    # No fractional technical values should remain
    assert not _has_fractional_technical(df), (
        "Extra rows with fractional technical features remain after exclusion. "
        "origin unknown, excluded — but filtering did not work."
    )


@pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason="CareerMapping1.csv not present in this checkout",
)
def test_full_load_includes_extra_rows():
    """load_data() with exclude_extra_rows=False must return all 10,179 rows."""
    df = train.load_data(str(DATA_PATH), exclude_extra_rows=False)
    assert len(df) == 10_179, (
        f"Expected 10,179 rows when exclusion is disabled, got {len(df)}."
    )
    # Fractional technical values should be present in the full dataset
    assert _has_fractional_technical(df), (
        "Extra rows not found even with exclude_extra_rows=False — "
        "dataset structure may have changed."
    )


@pytest.mark.skipif(
    not DATA_PATH.exists(),
    reason="CareerMapping1.csv not present in this checkout",
)
def test_extra_rows_have_fractional_technical():
    """Extra rows (indices 9179–10178) must all have fractional technical features."""
    df_full = train.load_data(str(DATA_PATH), exclude_extra_rows=False)
    df_raw = train.load_data(str(DATA_PATH), exclude_extra_rows=True)
    # The extra rows are the ones present in the full but not the raw dataset
    # We detect them by the same criterion used in filtering
    def is_integer_row(row):
        return all(float(v) == int(float(v)) for v in row[TECHNICAL_FEATURES])
    is_integer = df_full.apply(is_integer_row, axis=1)
    extra_rows = df_full[~is_integer]
    assert len(extra_rows) == 1_000, (
        f"Expected 1,000 extra rows with fractional technical features, found {len(extra_rows)}."
    )
    # None of these rows should appear in the filtered raw dataset
    assert len(df_raw) == 9_179

