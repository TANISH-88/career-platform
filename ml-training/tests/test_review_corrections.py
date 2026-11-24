import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_split import load_frozen_split, PERSONALITY, persona_id
from development_data import load_development_addendum
from robust_gate import SEEDS, robust_gate
from train_candidate_ci import REFERENCE, read_reference


def make_manifest(tmp_path, row):
    data = tmp_path / "new.csv"
    row.to_csv(data, index=False)
    manifest = tmp_path / "addendum.json"
    manifest.write_text(json.dumps({"version": 1, "files": [{"path": data.name,
        "sha256": hashlib.sha256(data.read_bytes()).hexdigest(), "source": "synthetic test only"}]}))
    return manifest


def test_reference_tamper(tmp_path):
    assert len(read_reference()["row_ids"]) == 740
    altered = tmp_path / "reference.json"
    altered.write_bytes(REFERENCE.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="reference SHA256"):
        read_reference(altered)


def test_development_addendum(tmp_path):
    dev, hold = load_frozen_split()
    row = dev.iloc[[0]].copy()
    row["row_id"] = 10179
    for col in PERSONALITY:
        row[col] = 0.123456
    row["persona_id"] = persona_id(row[PERSONALITY].iloc[0])
    assert row.persona_id.iloc[0] not in set(hold.persona_id)
    manifest = make_manifest(tmp_path, row)
    augmented, info = load_development_addendum(dev, hold, manifest)
    assert len(augmented) == len(dev) + 1
    assert info["added_rows"] == 1
    assert set(augmented.persona_id).isdisjoint(hold.persona_id)
    (tmp_path / "new.csv").write_text("tampered")
    with pytest.raises(ValueError, match="SHA256"):
        load_development_addendum(dev, hold, manifest)


def test_holdout_and_duplicates_rejected(tmp_path):
    dev, hold = load_frozen_split()
    row = hold.iloc[[0]].copy()
    row["row_id"] = 10179
    with pytest.raises(ValueError, match="holdout persona"):
        load_development_addendum(dev, hold, make_manifest(tmp_path, row))
    row = dev.iloc[[0]].copy()
    row["row_id"] = 10179
    with pytest.raises(ValueError, match="Duplicate"):
        load_development_addendum(dev, hold, make_manifest(tmp_path, row))


def test_matched_seed_guard():
    y = np.tile(np.arange(16), 44)
    groups = np.repeat(np.arange(44), 16)
    old = y.copy()
    old[::2] = (old[::2] + 1) % 16
    new = old.copy()
    new[::4] = y[::4]
    baseline = np.tile(old, (len(SEEDS), 1))
    isolated = baseline.copy()
    isolated[0] = new
    report = robust_gate(y, old, new, groups, baseline, isolated, True)
    assert report["single_seed_eligible"]
    assert not report["promotion_eligible"]
    stable = np.tile(new, (len(SEEDS), 1))
    assert robust_gate(y, old, new, groups, baseline, stable, True)["promotion_eligible"]
    assert not robust_gate(y, old, new, groups, baseline, stable, False)["promotion_eligible"]
