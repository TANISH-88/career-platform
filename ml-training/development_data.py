"""Validated development-only additions; never change the frozen holdout."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from data_split import ROOT, FEATURES, TECH, PERSONALITY, persona_id

ADDENDUM = ROOT / "data/development/addendum_v1.json"


def load_development_addendum(dev, hold, manifest_path=ADDENDUM):
    path = Path(manifest_path)
    raw = path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Invalid development addendum manifest")
    frames = [dev]
    ids = set(dev.row_id) | set(hold.row_id)
    hold_ids = set(hold.persona_id)
    seen = set()
    for entry in manifest["files"]:
        name = entry["path"]
        if (not isinstance(name, str) or Path(name).name != name or
                not name.endswith(".csv") or name in seen or
                not isinstance(entry.get("source"), str) or not entry["source"].strip()):
            raise ValueError("Invalid addendum path or provenance")
        seen.add(name)
        csv_path = path.parent / name
        if csv_path.is_symlink() or hashlib.sha256(csv_path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Development addendum SHA256 mismatch")
        data = pd.read_csv(csv_path)
        if set(data.columns) != set(dev.columns) or len(data.columns) != len(dev.columns) or data.empty or data.isna().any().any():
            raise ValueError("Invalid development addendum schema")
        if not pd.api.types.is_integer_dtype(data.row_id) or (data.row_id <= 10178).any() or not data.row_id.is_unique or set(data.row_id) & ids:
            raise ValueError("Invalid or repeated addendum row_id")
        tech = data[TECH].to_numpy(dtype=float)
        personality = data[PERSONALITY].to_numpy(dtype=float)
        if not (np.isfinite(tech).all() and np.isfinite(personality).all() and
                ((tech >= 0) & (tech <= 6) & (tech % 1 == 0)).all() and
                ((personality >= 0) & (personality <= 1)).all()):
            raise ValueError("Invalid addendum feature range")
        if not set(data.Role) <= set(dev.Role):
            raise ValueError("Unknown addendum role")
        expected = [persona_id(v) for v in data[PERSONALITY].itertuples(index=False, name=None)]
        if data.persona_id.tolist() != expected or set(expected) & hold_ids:
            raise ValueError("Invalid persona ID or holdout persona in addendum")
        ids.update(data.row_id)
        frames.append(data)
    combined = pd.concat(frames, ignore_index=True)
    if combined.duplicated(FEATURES + ["Role"]).any():
        raise ValueError("Duplicate development observation")
    return combined, {"version": 1, "manifest_sha256": hashlib.sha256(raw).hexdigest(),
                      "added_rows": len(combined) - len(dev), "files": manifest["files"]}
