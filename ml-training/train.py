"""
train.py - Production training script for Career Role Prediction RF model.

Usage:
    python ml-training/train.py

Outputs:
    - models/frf.pkl          : trained RandomForestClassifier
    - models/scaler.pkl       : fitted StandardScaler
    - models/pca.pkl          : fitted PCA (n_components=2)
    - mlruns/                 : MLflow experiment artifacts & metrics

All randomness is controlled by RANDOM_SEED = 42.
The train/test split is fixed at 80/20 stratified.
"""

import json
import os
import pathlib
import hashlib

import joblib
import mlflow
import mlflow.sklearn
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
DATA_PATH: str = "data/CareerMapping1.csv"
ARTIFACTS_DIR: str = "ml-training/artifacts"
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


def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Drop the unnamed index column that the notebook also drops
    if df.columns[0].startswith("Unnamed"):
        df = df.drop(df.columns[0], axis=1)
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


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def train() -> None:
    import sklearn
    sklearn_version = sklearn.__version__

    # Resolve paths relative to repo root (script may be called from any cwd)
    repo_root = pathlib.Path(__file__).resolve().parent.parent
    data_path = repo_root / DATA_PATH
    artifacts_dir = repo_root / ARTIFACTS_DIR
    metrics_path = repo_root / METRICS_PATH

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # -- Load params from params.yaml (DVC-tracked) ------------------------
    p = _load_params(repo_root)
    random_seed: int = p["RANDOM_SEED"]
    test_size: float = p["TEST_SIZE"]
    rf_params: dict = p["RF_PARAMS"]

    # -- Shared MLflow tracking URI (env var or sqlite:///mlflow.db) -------
    default_tracking_uri = f"sqlite:///{repo_root.as_posix()}/mlflow.db"
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", default_tracking_uri)
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="rf_train_v1"):

        # -- Log fixed hyper-params & run config ---------------------------
        mlflow.log_params(
            {
                "random_seed": random_seed,
                "test_size": test_size,
                "data_path": str(data_path),
                "sklearn_version": sklearn_version,
                **rf_params,
            }
        )

        # -- Data loading & validation -------------------------------------
        print(f"[1/6] Loading data from {data_path} ...")
        df = load_data(str(data_path))
        validate_data(df)
        data_md5 = compute_md5(str(data_path))
        mlflow.set_tag("data_md5", data_md5)
        mlflow.set_tag("data_rows", str(len(df)))
        print(f"       {len(df)} rows | md5={data_md5}")

        # -- Fixed train/test split (stratified) ---------------------------
        print("[2/6] Splitting data (80/20 stratified, seed=42) ...")
        X, y = build_features(df)
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=random_seed,
            stratify=y,
        )
        mlflow.log_params(
            {
                "n_train": len(X_train),
                "n_test": len(X_test),
                "n_classes": int(y.nunique()),
            }
        )

        # -- Build unified Pipeline (preprocessor + RF) --------------------
        print("[3/6] Building unified Pipeline (StandardScaler + PCA + RandomForest) ...")
        tech_pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("pca", PCA(n_components=2, random_state=random_seed)),
            ]
        )
        preprocessor = ColumnTransformer(
            transformers=[
                ("personality", "passthrough", PERSONALITY_FEATURES),
                ("tech", tech_pipeline, TECHNICAL_FEATURES),
            ]
        )
        pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                ("classifier", RandomForestClassifier(**rf_params)),
            ]
        )

        # -- Train unified Pipeline ----------------------------------------
        print("[4/6] Fitting unified Pipeline on training split ...")
        pipeline.fit(X_train, y_train)

        # -- Evaluate ------------------------------------------------------
        print("[5/6] Evaluating ...")
        train_acc = accuracy_score(y_train, pipeline.predict(X_train))
        test_acc = accuracy_score(y_test, pipeline.predict(X_test))
        test_f1 = f1_score(y_test, pipeline.predict(X_test), average="macro")

        # 5-fold stratified cross-validation on full dataset using Pipeline
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=random_seed)
        cv_scores = cross_val_score(pipeline, X, y, cv=skf, scoring="accuracy")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))

        metrics = {
            "train_accuracy": float(train_acc),
            "test_accuracy": float(test_acc),
            "test_f1_macro": float(test_f1),
            "cv_accuracy_mean": cv_mean,
            "cv_accuracy_std": cv_std,
        }

        mlflow.log_metrics(metrics)

        # Write DVC metrics.json
        with open(metrics_path, "w") as fh:
            json.dump(metrics, fh, indent=2)

        print(f"       Train accuracy  : {train_acc:.4f}")
        print(f"       Test  accuracy  : {test_acc:.4f}")
        print(f"       Test  F1-macro  : {test_f1:.4f}")
        print(f"       CV accuracy     : {cv_mean:.4f} +/- {cv_std:.4f}")
        print()
        print(classification_report(y_test, pipeline.predict(X_test)))

        # -- Persist candidate artifacts to ml-training/artifacts/ ---------
        print(f"[6/6] Saving candidate artifacts to {artifacts_dir} ...")
        tech_transformer = pipeline.named_steps["preprocessor"].named_transformers_["tech"]
        scaler = tech_transformer.named_steps["scaler"]
        pca = tech_transformer.named_steps["pca"]
        model = pipeline.named_steps["classifier"]

        frf_path = str(artifacts_dir / "frf.pkl")
        scaler_path = str(artifacts_dir / "scaler.pkl")
        pca_path = str(artifacts_dir / "pca.pkl")
        pipeline_path = str(artifacts_dir / "pipeline.pkl")

        joblib.dump(model, frf_path)
        joblib.dump(scaler, scaler_path)
        joblib.dump(pca, pca_path)
        joblib.dump(pipeline, pipeline_path)

        # Log candidate artifacts folder to MLflow
        mlflow.log_artifacts(str(artifacts_dir), artifact_path="artifacts")

        # Register unified Pipeline as career-rf so scaler+PCA+RF cannot desync
        mlflow.sklearn.log_model(
            pipeline,
            artifact_path="career_pipeline",
            registered_model_name="career-rf",
        )

        mlflow.set_tags(
            {
                "model_type": "Pipeline(StandardScaler+PCA+RandomForestClassifier)",
                "training_script": "ml-training/train.py",
                "sklearn_version": sklearn_version,
            }
        )

        run_id = mlflow.active_run().info.run_id
        print(f"\n[OK] Run logged to MLflow  run_id={run_id}")
        print(f"[OK] Tracking URI          {tracking_uri}")
        print(f"[OK] Candidate models      {artifacts_dir}")
        print(f"[OK] Metrics written to    {metrics_path}")
        print(f"[OK] sklearn version       {sklearn_version}  (pinned in requirements)")


if __name__ == "__main__":
    train()


