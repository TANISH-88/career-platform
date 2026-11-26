"""M3 training: frozen-persona evaluation, explicit registry bootstrap, no deployment.

Legacy load_data and preprocessing helpers are retained for historical audits.
Run from any working directory:
  python ml-training/train.py bootstrap --output ml-training/m3-output
  python ml-training/train.py candidate --output ml-training/m3-output
"""
import json
import os
import pathlib
import hashlib

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
TEST_SIZE: float = 0.20
DATA_PATH: str = "data/CareerMapping1.csv"  # legacy audit source
ARTIFACTS_DIR: str = "ml-training/m3-output"
METRICS_PATH: str = "ml-training/metrics.json"
EXPERIMENT_NAME: str = "career-prediction"


TECHNICAL_FEATURES: list[str] = [
    "Computer Architecture",
    "Programming Skills",
    "Project Management",
    "Communication skills",
]
PERSONALITY_FEATURES: list[str] = [
    "Openness",
    "Conscientousness",
    "Extraversion",
    "Agreeableness",
    "Emotional_Range",
    "Conversation",
    "Openness to Change",
    "Hedonism",
    "Self-enhancement",
    "Self-transcendence",
]
ALL_FEATURES: list[str] = TECHNICAL_FEATURES + PERSONALITY_FEATURES
TARGET_COL: str = "Role"


def _load_params(repo_root: pathlib.Path) -> dict:
    """Load hyperparameters from ml-training/params.yaml (DVC params file)."""
    params_path = repo_root / "ml-training" / "params.yaml"
    if params_path.exists():
        with open(params_path) as fh:
            raw = yaml.safe_load(fh)
        rf_params = raw.get("rf_params", {})
        return {
            "RANDOM_SEED": raw.get("random_seed", RANDOM_SEED),
            "TEST_SIZE": raw.get("test_size", TEST_SIZE),
            "RF_PARAMS": {
                "bootstrap": rf_params.get("bootstrap", True),
                "max_depth": rf_params.get("max_depth", 10),
                "max_features": rf_params.get("max_features", "sqrt"),
                "min_samples_leaf": rf_params.get("min_samples_leaf", 7),
                "min_samples_split": rf_params.get("min_samples_split", 7),
                "n_estimators": rf_params.get("n_estimators", 200),
                "random_state": raw.get("random_seed", RANDOM_SEED),
            },
        }
    # Fallback defaults when params.yaml is absent
    return {
        "RANDOM_SEED": RANDOM_SEED,
        "TEST_SIZE": TEST_SIZE,
        "RF_PARAMS": {
            "bootstrap": True,
            "max_depth": 10,
            "max_features": "sqrt",
            "min_samples_leaf": 7,
            "min_samples_split": 7,
            "n_estimators": 200,
            "random_state": RANDOM_SEED,
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def compute_md5(path: str) -> str:
    """Return the MD5 hex-digest of a file (used for DVC-style data versioning)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_data(path: str, exclude_extra_rows: bool = True) -> pd.DataFrame:
    """Load career mapping CSV, excluding unknown-origin extra rows by default.

    The dataset (CareerMapping1.csv, 10,179 rows) contains 1,000 rows appended
    at indices 9,179–10,178 whose origin is unknown.  These rows have fractional
    technical feature values (continuous in [0, 1]) whereas the 9,179 raw rows
    have integer technical values in [0, 6].  Because their origin cannot be
    established they are excluded from default training and evaluation.

    Pass ``exclude_extra_rows=False`` only when explicitly investigating the
    extra rows.  The raw dataset file is never modified.
    """
    df = pd.read_csv(path)
    # Drop the unnamed index column that the notebook also drops
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(df.columns[0], axis=1)
    if exclude_extra_rows:
        # Identify extra rows: technical features are fractional (not whole numbers)
        # Raw rows always have integer-valued technical features (0–6).
        def _all_integer(row: pd.Series) -> bool:
            return all(float(v) == int(float(v)) for v in row)
        mask_raw = df[TECHNICAL_FEATURES].apply(_all_integer, axis=1)
        n_excluded = int((~mask_raw).sum())
        if n_excluded > 0:
            print(
                f"[data] Excluded {n_excluded} unknown-origin extra rows "
                f"(fractional technical features; origin unknown, excluded). "
                f"Remaining: {mask_raw.sum()} rows."
            )
        df = df[mask_raw].reset_index(drop=True)
    return df


def validate_data(df: pd.DataFrame) -> None:
    missing = df.isnull().sum()
    if missing.sum() != 0:
        raise ValueError(f"Missing values found:\n{missing[missing > 0]}")
    for col in ALL_FEATURES + [TARGET_COL]:
        if col not in df.columns:
            raise KeyError(f"Required column '{col}' not found in dataset")


def build_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X, y) where X keeps all 14 raw features; label-encode y."""
    X = df[ALL_FEATURES].copy()
    le = LabelEncoder()
    y = pd.Series(le.fit_transform(df[TARGET_COL]), name=TARGET_COL)
    return X, y


def fit_preprocessor(
    X_train: pd.DataFrame,
) -> tuple[StandardScaler, PCA]:
    """Fit scaler+PCA on training split only (no leakage)."""
    scaler = StandardScaler()
    pca = PCA(n_components=2, random_state=RANDOM_SEED)

    scaled_tech = scaler.fit_transform(X_train[TECHNICAL_FEATURES])
    pca.fit(scaled_tech)
    return scaler, pca


def apply_preprocessor(
    X: pd.DataFrame, scaler: StandardScaler, pca: PCA
) -> np.ndarray:
    """Apply pre-fitted scaler+PCA and concatenate with personality features."""
    scaled_tech = scaler.transform(X[TECHNICAL_FEATURES])
    pca_components = pca.transform(scaled_tech)
    personality = X[PERSONALITY_FEATURES].values
    return np.concatenate([personality, pca_components], axis=1)



import argparse
from data_split import load_frozen_split, CLEAN, MANIFEST
from promotion_gate import promotion_gate
from check_parity import check_parity

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CHAMPION_PARAMS = dict(bootstrap=True, max_depth=10, max_features="sqrt",
                       min_samples_leaf=7, min_samples_split=7,
                       n_estimators=200, random_state=42)
CHAMPION_NAME = "career-rf-m3-champion"
LEGACY_NAME = "career-rf-legacy"


def build_pipeline(rf_params):
    tech = Pipeline([("scaler", StandardScaler()),
                     ("pca", PCA(n_components=2, random_state=42))])
    pre = ColumnTransformer([("personality", "passthrough", PERSONALITY_FEATURES),
                             ("tech", tech, TECHNICAL_FEATURES)])
    return Pipeline([("preprocessor", pre),
                     ("classifier", RandomForestClassifier(**rf_params))])


def fit_development(dev, rf_params):
    validate_data(dev)
    encoder = LabelEncoder().fit(dev.Role)
    from app.config.constants import ROLE_MAPPING
    if list(encoder.classes_) != list(ROLE_MAPPING.values()):
        raise ValueError("Development label order mismatch")
    model = build_pipeline(rf_params)
    model.fit(dev[ALL_FEATURES], encoder.transform(dev.Role))
    return model, encoder


def evaluate(model, encoder, frame):
    y = encoder.transform(frame.Role)
    pred = model.predict(frame[ALL_FEATURES])
    return {"accuracy": float(accuracy_score(y, pred)),
            "macro_f1": float(f1_score(y, pred, labels=np.arange(len(encoder.classes_)),
                                       average="macro", zero_division=0)),
            "rows": len(frame), "personas": int(frame.persona_id.nunique()),
            "per_role": classification_report(y, pred, labels=np.arange(len(encoder.classes_)),
                                             target_names=encoder.classes_, output_dict=True,
                                             zero_division=0)}


def save_artifacts(model, destination):
    destination.mkdir(parents=True, exist_ok=True)
    tech = model.named_steps["preprocessor"].named_transformers_["tech"]
    for name, obj in (("pipeline", model), ("frf", model.named_steps["classifier"]),
                      ("scaler", tech.named_steps["scaler"]), ("pca", tech.named_steps["pca"])):
        joblib.dump(obj, destination / (name + ".pkl"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def frozen_identity():
    return {"cleaned_sha256": digest(CLEAN), "manifest_sha256": digest(MANIFEST)}


def register_once(model, name, tags, metrics=None, tracking_uri=None):
    import mlflow
    import mlflow.sklearn
    from mlflow.tracking import MlflowClient

    mlflow.set_tracking_uri(tracking_uri or os.environ.get(
        "MLFLOW_TRACKING_URI", f"sqlite:///{REPO_ROOT.as_posix()}/mlflow.db"))
    mlflow.set_experiment(EXPERIMENT_NAME)
    client = MlflowClient()
    versions = client.search_model_versions(f"name = '{name}'")
    if versions:
        # Never silently adopt a model with a different training-data identity.
        matching = [v for v in versions if all(v.tags.get(k) == str(val)
                                               for k, val in tags.items())]
        if len(matching) != 1 or len(versions) != 1:
            raise RuntimeError(f"Registry {name} already contains unexpected versions")
        return {"name": name, "version": str(matching[0].version),
                "run_id": matching[0].run_id}
    with mlflow.start_run(run_name=name) as run:
        mlflow.set_tags(tags)
        if metrics:
            mlflow.log_metrics({k: v for k, v in metrics.items()
                                if k in ("accuracy", "macro_f1")})
        mlflow.sklearn.log_model(model, artifact_path="pipeline")
        version = mlflow.register_model(f"runs:/{run.info.run_id}/pipeline", name,
                                        await_registration_for=120)
        for k, v in tags.items():
            client.set_model_version_tag(name, version.version, k, str(v))
        return {"name": name, "version": str(version.version), "run_id": run.info.run_id}


def bootstrap(output, register=False):
    dev, hold = load_frozen_split()
    directory = output / "champion"
    if directory.exists():
        raise FileExistsError("Champion already exists; use a fresh output directory")
    champion, encoder = fit_development(dev, CHAMPION_PARAMS)
    save_artifacts(champion, directory)
    if not check_parity(directory):
        raise RuntimeError("Champion serving parity failed")
    report = {"identity": frozen_identity(), "recipe": CHAMPION_PARAMS,
              "class_order": encoder.classes_.tolist(), "dev": evaluate(champion, encoder, dev),
              "holdout": evaluate(champion, encoder, hold),
              "pipeline_sha256": digest(directory / "pipeline.pkl"), "parity_passed": True}
    if register:
        report["champion_registry"] = register_once(
            champion, CHAMPION_NAME, {**report["identity"],
                "recipe": json.dumps(CHAMPION_PARAMS, sort_keys=True),
                "training_scope": "development personas only",
                "pipeline_sha256": report["pipeline_sha256"]}, report["holdout"])
        legacy_path = REPO_ROOT / "ml-training/artifacts/pipeline.pkl"
        report["legacy_registry"] = register_once(
            joblib.load(legacy_path), LEGACY_NAME,
            {"source_pipeline_sha256": digest(legacy_path),
             "training_scope": "historical random row split from full original source including holdout personas",
             "comparison": "not comparable; no unseen-persona score"})
    write_json(directory / "report.json", report)
    print(json.dumps({"champion_holdout_accuracy": report["holdout"]["accuracy"],
                      "champion_holdout_macro_f1": report["holdout"]["macro_f1"],
                      "registry": report.get("champion_registry")}, indent=2))
    return report


def train_candidate(output):
    """Use the pinned-reference and robust gate shared with CI."""
    from train_candidate_ci import run
    return run(output / "candidate")


def train():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", default="candidate", choices=["bootstrap", "candidate"])
    parser.add_argument("--output", type=pathlib.Path,
                        default=REPO_ROOT / "ml-training/m3-output")
    parser.add_argument("--register", action="store_true",
                        help="Explicitly register bootstrap models in MLflow; never deploy")
    args = parser.parse_args()
    if args.register and args.mode != "bootstrap":
        parser.error("--register is only valid for bootstrap")
    if args.mode == "bootstrap":
        bootstrap(args.output.resolve(), register=args.register)
    else:
        train_candidate(args.output.resolve())


if __name__ == "__main__":
    train()
