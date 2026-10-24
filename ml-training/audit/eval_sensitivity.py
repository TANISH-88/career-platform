"""Read-only sensitivity experiments using the training pipeline configuration."""

from __future__ import annotations

import pathlib
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml-training"))
import train

CURATED_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"
RAW_PATH = REPO_ROOT / "data" / "CareerMap- Mapping Tech Roles With Personality & Skills.csv"
ARTIFACT_PATH = REPO_ROOT / "ml-training" / "artifacts" / "pipeline.pkl"
SEEDS = [42, 43, 44, 45, 46]


def load(path: pathlib.Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.columns[0].startswith("Unnamed"):
        frame = frame.drop(columns=frame.columns[0])
    return frame


def labels(frame: pd.DataFrame) -> pd.Series:
    return pd.Series(pd.factorize(frame[train.TARGET_COL], sort=True)[0], index=frame.index)


def metrics(model, x_test, y_test) -> tuple[float, float]:
    prediction = model.predict(x_test)
    return float(accuracy_score(y_test, prediction)), float(
        f1_score(y_test, prediction, average="macro")
    )


def summarize(name: str, values: list[tuple[float, float]]) -> None:
    accuracy = np.array([value[0] for value in values])
    macro_f1 = np.array([value[1] for value in values])
    print(
        f"{name}: accuracy={accuracy.mean():.6f} +/- {accuracy.std():.6f}; "
        f"macro_f1={macro_f1.mean():.6f} +/- {macro_f1.std():.6f}"
    )


def fit_clone(template, x_train, y_train, seed: int):
    model = clone(template)
    model.set_params(classifier__random_state=seed)
    model.fit(x_train, y_train)
    return model


def fit_feature_model(template, columns: list[str], x_train, y_train, seed: int):
    classifier = clone(template.named_steps["classifier"])
    classifier.set_params(random_state=seed)
    classifier.fit(x_train[columns], y_train)
    return classifier


def main() -> None:
    curated = load(CURATED_PATH)
    raw = load(RAW_PATH)
    extra_mask = ~curated[train.ALL_FEATURES + [train.TARGET_COL]].apply(
        tuple, axis=1
    ).isin(set(raw[train.ALL_FEATURES + [train.TARGET_COL]].apply(tuple, axis=1)))
    extra = curated[extra_mask]
    raw_like = curated[~extra_mask]
    template = joblib.load(ARTIFACT_PATH)

    random_results = []
    grouped_results = []
    raw_results = []
    extra_results = []
    technical_results = []
    personality_results = []
    importance_results = []

    for seed in SEEDS:
        x = curated[train.ALL_FEATURES]
        y = labels(curated)
        x_train, x_test, y_train, y_test = train_test_split(
            x, y, test_size=train.TEST_SIZE, random_state=seed, stratify=y
        )
        model = fit_clone(template, x_train, y_train, seed)
        random_results.append(metrics(model, x_test, y_test))
        importance = model.named_steps["classifier"].feature_importances_
        importance_results.append((float(importance[:10].sum()), float(importance[10:].sum())))

        groups = curated[train.PERSONALITY_FEATURES].apply(tuple, axis=1)
        train_idx, test_idx = next(
            GroupShuffleSplit(n_splits=1, test_size=train.TEST_SIZE, random_state=seed)
            .split(x, y, groups=groups)
        )
        grouped_model = fit_clone(template, x.iloc[train_idx], y.iloc[train_idx], seed)
        grouped_results.append(
            metrics(grouped_model, x.iloc[test_idx], y.iloc[test_idx])
        )

        raw_x = raw_like[train.ALL_FEATURES]
        raw_y = labels(raw_like)
        raw_train, raw_test, raw_y_train, raw_y_test = train_test_split(
            raw_x, raw_y, test_size=train.TEST_SIZE, random_state=seed, stratify=raw_y
        )
        raw_model = fit_clone(template, raw_train, raw_y_train, seed)
        raw_results.append(metrics(raw_model, raw_test, raw_y_test))

        extra_model = fit_clone(template, raw_x, raw_y, seed)
        extra_results.append(metrics(extra_model, extra[train.ALL_FEATURES], labels(extra)))

        tech_train, tech_test, tech_y_train, tech_y_test = train_test_split(
            x, y, test_size=train.TEST_SIZE, random_state=seed, stratify=y
        )
        tech_model = fit_feature_model(template, train.TECHNICAL_FEATURES, tech_train, tech_y_train, seed)
        technical_results.append(metrics(tech_model, tech_test[train.TECHNICAL_FEATURES], tech_y_test))
        personality_model = fit_feature_model(template, train.PERSONALITY_FEATURES, tech_train, tech_y_train, seed)
        personality_results.append(
            metrics(personality_model, tech_test[train.PERSONALITY_FEATURES], tech_y_test)
        )

    print(f"CURATED_ROWS={len(curated)} RAW_ROWS={len(raw_like)} EXTRA_ROWS={len(extra)}")
    summarize("CURRENT_RANDOM_STRATIFIED", random_results)
    summarize("GROUPED_BY_PERSONALITY_VECTOR", grouped_results)
    summarize("RAW_ROWS_ONLY", raw_results)
    summarize("RAW_TRAIN_EXTRA_TEST", extra_results)
    summarize("TECHNICAL_FEATURES_ONLY", technical_results)
    summarize("PERSONALITY_FEATURES_ONLY", personality_results)
    personality_importance = np.array([value[0] for value in importance_results])
    pca_importance = np.array([value[1] for value in importance_results])
    print(
        f"CURRENT_SPLIT_FEATURE_IMPORTANCE: personality={personality_importance.mean():.6f} "
        f"+/- {personality_importance.std():.6f}; pca_2={pca_importance.mean():.6f} "
        f"+/- {pca_importance.std():.6f}"
    )

    x = curated[train.ALL_FEATURES]
    x_train, x_test, _, _ = train_test_split(
        x, labels(curated), test_size=train.TEST_SIZE, random_state=train.RANDOM_SEED, stratify=labels(curated)
    )
    train_vectors = set(map(tuple, x_train.itertuples(index=False, name=None)))
    overlap = sum(tuple(row) in train_vectors for row in x_test.itertuples(index=False, name=None))
    print(f"CURRENT_SPLIT_TEST_ROWS_WITH_TRAINING_VECTOR={overlap}/{len(x_test)}")


if __name__ == "__main__":
    main()
