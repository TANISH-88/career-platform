"""Frozen M3 data contract. Never regenerate the holdout during training."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data/cleaned/careers_clean.csv"
MANIFEST = ROOT / "data/cleaned/holdout_v1.json"
TECH = ["Computer Architecture", "Programming Skills", "Project Management", "Communication skills"]
PERSONALITY = ["Openness", "Conscientousness", "Extraversion", "Agreeableness",
               "Emotional_Range", "Conversation", "Openness to Change", "Hedonism",
               "Self-enhancement", "Self-transcendence"]
FEATURES = TECH + PERSONALITY


def persona_id(values):
    return hashlib.sha1("|".join(f"{float(v):.6f}" for v in values).encode()).hexdigest()


def load_frozen_split(clean_path=CLEAN, manifest_path=MANIFEST):
    """Reject changed data; return disjoint development and holdout frames."""
    clean_path = Path(clean_path)
    manifest = json.loads(Path(manifest_path).read_text())
    if hashlib.sha256(clean_path.read_bytes()).hexdigest() != manifest["cleaned_sha256"]:
        raise ValueError("Cleaned dataset SHA256 does not match frozen holdout")
    params = yaml.safe_load((ROOT / "ml-training/params.yaml").read_text())
    if (manifest["seed"] != params["holdout_seed"] or
            manifest["holdout_persona_fraction"] != params["holdout_persona_fraction"]):
        raise ValueError("Frozen holdout parameters mismatch")
    df = pd.read_csv(clean_path)
    ids = set(df.persona_id)
    hold = set(manifest["holdout_persona_ids"])
    if not hold < ids or len(hold) != manifest["holdout_personas"]:
        raise ValueError("Invalid holdout persona IDs")
    dev = df.loc[~df.persona_id.isin(hold)].copy()
    test = df.loc[df.persona_id.isin(hold)].copy()
    if (len(df), len(ids), len(dev), len(test), dev.persona_id.nunique()) != (
            manifest["total_rows"], manifest["total_personas"], manifest["development_rows"],
            manifest["holdout_rows"], manifest["development_personas"]):
        raise ValueError("Frozen holdout counts mismatch")
    if set(dev.Role) != set(df.Role) or set(test.Role) != set(df.Role):
        raise ValueError("Missing role in frozen split")
    return dev, test
