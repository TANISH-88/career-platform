"""Read-only data audit for the curated and raw career datasets."""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml-training"))
from train import ALL_FEATURES, PERSONALITY_FEATURES, TECHNICAL_FEATURES, TARGET_COL

CURATED_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"
RAW_PATH = REPO_ROOT / "data" / "CareerMap- Mapping Tech Roles With Personality & Skills.csv"


def load(path: pathlib.Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.columns[0].startswith("Unnamed"):
        frame = frame.drop(columns=frame.columns[0])
    return frame


def key(frame: pd.DataFrame) -> pd.DataFrame:
    return frame[ALL_FEATURES + [TARGET_COL]].copy()


def main() -> None:
    curated = load(CURATED_PATH)
    raw = load(RAW_PATH)
    technical_non_whole = (curated[TECHNICAL_FEATURES] % 1 != 0).any(axis=1)
    fractional = curated[technical_non_whole]
    remaining = curated[~technical_non_whole]
    raw_keys = set(map(tuple, key(raw).itertuples(index=False, name=None)))
    curated_keys = list(map(tuple, key(curated).itertuples(index=False, name=None)))
    extra = curated[[row not in raw_keys for row in curated_keys]]

    print(f"CURATED_ROWS={len(curated)}")
    print(f"RAW_ROWS={len(raw)}")
    print(f"ROWS_WITH_NONWHOLE_TECHNICAL={len(fractional)}")
    print("NONWHOLE_TECHNICAL_STATS")
    for column in TECHNICAL_FEATURES:
        print(
            f"{column}: min={fractional[column].min():.12g} "
            f"max={fractional[column].max():.12g} mean={fractional[column].mean():.12g} "
            f"| remaining min={remaining[column].min():.12g} "
            f"max={remaining[column].max():.12g} mean={remaining[column].mean():.12g}"
        )
    print("RAW_EXTRA_TECHNICAL_STATS")
    for column in TECHNICAL_FEATURES:
        print(
            f"{column}: raw min={raw[column].min():.12g} max={raw[column].max():.12g} "
            f"mean={raw[column].mean():.12g} | extra min={extra[column].min():.12g} "
            f"max={extra[column].max():.12g} mean={extra[column].mean():.12g}"
        )
    print("NONWHOLE_ROLE_COUNTS")
    print(fractional[TARGET_COL].value_counts().sort_index().to_string())
    print("NONWHOLE_PERSONALITY_RANGE")
    print(
        f"min={fractional[PERSONALITY_FEATURES].min().min():.12g} "
        f"max={fractional[PERSONALITY_FEATURES].max().max():.12g} "
        f"| remaining min={remaining[PERSONALITY_FEATURES].min().min():.12g} "
        f"max={remaining[PERSONALITY_FEATURES].max().max():.12g}"
    )
    raw_personality = set(map(tuple, raw[PERSONALITY_FEATURES].itertuples(index=False, name=None)))
    personality_matches = [
        tuple(row) in raw_personality
        for row in fractional[PERSONALITY_FEATURES].itertuples(index=False, name=None)
    ]
    print(
        "NONWHOLE_PERSONALITY_VECTORS_IN_RAW="
        f"{sum(personality_matches)}/{len(personality_matches)}"
    )
    print("RAW_EXTRA_PERSONALITY_RANGE")
    for column in PERSONALITY_FEATURES:
        print(
            f"{column}: raw min={raw[column].min():.12g} max={raw[column].max():.12g} "
            f"| extra min={extra[column].min():.12g} max={extra[column].max():.12g}"
        )
    print(f"CURATED_ROWS_NOT_IN_RAW={sum(row not in raw_keys for row in curated_keys)}")

    vectors = raw[PERSONALITY_FEATURES].apply(tuple, axis=1)
    vector_counts = vectors.value_counts()
    role_counts_per_vector = raw.assign(_vector=vectors).groupby("_vector")[TARGET_COL].nunique()
    print(f"RAW_DISTINCT_PERSONALITY_VECTORS={vector_counts.size}")
    print(
        "RAW_ROWS_PER_VECTOR="
        f"min={vector_counts.min()} median={vector_counts.median():g} max={vector_counts.max()}"
    )
    print(
        "RAW_VECTORS_WITH_MULTIPLE_ROLES="
        f"{int((role_counts_per_vector > 1).sum())}"
    )

    duplicate_counts = key(raw).value_counts()
    print(f"RAW_EXACT_DUPLICATE_ROWS={int((duplicate_counts > 1).sum())}")
    print(f"RAW_EXACT_DUPLICATE_EXTRA_OCCURRENCES={int((duplicate_counts - 1).clip(lower=0).sum())}")


if __name__ == "__main__":
    main()
