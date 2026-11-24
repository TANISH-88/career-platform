"""Candidate-only CI; evaluate against a checked-in immutable champion reference."""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import yaml
from sklearn.metrics import accuracy_score, f1_score

from data_split import load_frozen_split
from train import (REPO_ROOT, ALL_FEATURES, CHAMPION_PARAMS, _load_params,
                   fit_development, evaluate, frozen_identity, save_artifacts,
                   digest, write_json)
from check_parity import check_parity
from promotion_gate import promotion_gate

REFERENCE = REPO_ROOT / "ml-training/champion-reference.json"


def run(output):
    dev, hold = load_frozen_split()
    ref = json.loads(REFERENCE.read_text())
    if (ref["identity"] != frozen_identity()
            or ref["recipe"] != CHAMPION_PARAMS
            or ref["row_ids"] != hold.row_id.tolist()
            or ref["source_commit"] != "55572273068bdad19d719149df877d7b00fd01d1"):
        raise ValueError("Champion reference identity mismatch; review required")
    params = _load_params(REPO_ROOT)["RF_PARAMS"]
    model, encoder = fit_development(dev, params)
    if ref["class_order"] != encoder.classes_.tolist():
        raise ValueError("Champion label order mismatch")
    y = encoder.transform(hold.Role)
    old = np.asarray(ref["predictions"])
    if old.shape != y.shape or not np.isin(old, np.arange(len(encoder.classes_))).all():
        raise ValueError("Invalid frozen predictions")
    if (not np.isclose(accuracy_score(y, old), ref["holdout_accuracy"], atol=1e-12, rtol=0)
            or not np.isclose(f1_score(y, old, labels=np.arange(len(encoder.classes_)),
                                       average="macro", zero_division=0),
                              ref["holdout_macro_f1"], atol=1e-12, rtol=0)):
        raise ValueError("Frozen champion score mismatch")
    if output.exists():
        raise FileExistsError("Use a fresh candidate output directory")
    save_artifacts(model, output)
    parity = check_parity(output)
    new = model.predict(hold[ALL_FEATURES])
    gate = promotion_gate(y, old, new, hold.persona_id, parity,
                          min_gain=yaml.safe_load((REPO_ROOT / "ml-training/params.yaml").read_text())["min_gain"])
    report = {"source_commit": os.environ.get("GITHUB_SHA"), "identity": frozen_identity(),
              "reference_sha256": digest(REFERENCE), "champion_source_commit": ref["source_commit"],
              "candidate_recipe": params, "candidate_pipeline_sha256": digest(output / "pipeline.pkl"),
              "champion_holdout_macro_f1": ref["holdout_macro_f1"],
              "candidate_holdout": evaluate(model, encoder, hold),
              "candidate_dev": evaluate(model, encoder, dev), "gate": gate,
              "deployed": False, "registered": False}
    write_json(output / "report.json", report)
    print(json.dumps(gate, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.output)
    except Exception as exc:
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a") as f:
                f.write("## Candidate training failed\n\n" + type(exc).__name__ + ": " + str(exc) + "\n")
        raise
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        gate = report["gate"]
        with open(summary, "a") as f:
            f.write("## M3 candidate report\n\n")
            for key in ("champion_accuracy", "candidate_accuracy", "observed_gain",
                        "ci_90_lower", "ci_90_upper", "parity_passed", "promotion_eligible"):
                f.write(f"- {key}: {gate[key]}\n")
            f.write("\nNo model registered, promoted or deployed.\n")


if __name__ == "__main__":
    main()
