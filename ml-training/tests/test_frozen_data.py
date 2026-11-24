"""Non-skipping M3 tests against committed data."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import pytest
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml-training"))
sys.path.insert(0, str(ROOT / "backend/fastapi"))
from data_split import CLEAN, MANIFEST, FEATURES, TECH, PERSONALITY, persona_id, load_frozen_split
from app.config.constants import ROLE_MAPPING


def test_cleaned_source_and_quarantine():
    clean = pd.read_csv(CLEAN)
    raw = pd.read_csv(ROOT / "data/CareerMap- Mapping Tech Roles With Personality & Skills.csv")
    raw["Role"] = raw.Role.replace({"Software tester": "Software Tester"})
    raw = raw.drop_duplicates(FEATURES + ["Role"])
    quarantine = pd.read_csv(ROOT / "data/quarantine/extra_rows.csv")
    assert len(clean) == 3116
    assert len(quarantine) == 1000
    assert not ((quarantine[TECH] % 1 == 0).all(axis=1)).any()
    assert (clean[TECH] % 1 == 0).all().all()
    assert not clean.duplicated(FEATURES + ["Role"]).any()
    assert clean.row_id.is_unique
    assert not clean.isna().any().any()
    assert clean.persona_id.nunique() == 218
    assert clean.Role.nunique() == 16
    assert clean.persona_id.tolist() == [persona_id(v) for v in clean[PERSONALITY].itertuples(index=False, name=None)]
    # Compare numeric feature values at the precision present in the raw source.
    def rows(frame):
        return Counter(tuple(round(float(v), 12) for v in row[:-1]) + (row[-1],)
                       for row in frame[FEATURES + ["Role"]].itertuples(index=False, name=None))
    assert rows(clean) == rows(raw)


def test_role_mapping_matches_label_encoder():
    labels = LabelEncoder().fit(pd.read_csv(CLEAN).Role).classes_.tolist()
    assert list(ROLE_MAPPING) == list(range(16))
    assert list(ROLE_MAPPING.values()) == labels


def test_frozen_split():
    manifest = json.loads(MANIFEST.read_text())
    assert hashlib.sha256(CLEAN.read_bytes()).hexdigest() == manifest["cleaned_sha256"]
    dev, hold = load_frozen_split()
    a, b = set(dev.persona_id), set(hold.persona_id)
    assert not a & b
    assert a | b == set(pd.read_csv(CLEAN).persona_id)
    assert (len(a), len(b)) == (174, 44)
    assert b == set(manifest["holdout_persona_ids"])
    for role, counts in manifest["role_persona_counts"].items():
        assert dev.loc[dev.Role == role, "persona_id"].nunique() == counts["development"] >= 1
        assert hold.loc[hold.Role == role, "persona_id"].nunique() == counts["holdout"] >= 1


def test_tampered_data_rejected(tmp_path):
    altered = tmp_path / "altered.csv"
    altered.write_bytes(CLEAN.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        load_frozen_split(altered)
