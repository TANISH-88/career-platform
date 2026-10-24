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
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, train_test_split
from sklearn.inspection import permutation_importance
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import pairwise_distances

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


def print_seed_metrics(name: str, seeds: list[int], values: list[tuple[float, float]]) -> None:
    for seed, value in zip(seeds, values):
        print(f"{name}_SEED={seed}: accuracy={value[0]:.6f} macro_f1={value[1]:.6f}")


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


def group_fold_metrics(model_factory, x, y, groups):
    results = []
    splitter = GroupKFold(n_splits=5)
    for fold, (train_idx, test_idx) in enumerate(splitter.split(x, y, groups), 1):
        model = model_factory()
        model.fit(x.iloc[train_idx], y.iloc[train_idx])
        results.append((fold, *metrics(model, x.iloc[test_idx], y.iloc[test_idx])))
    return results


def main() -> None:
    curated = load(CURATED_PATH)
    raw = load(RAW_PATH)
    extra_mask = ~curated[train.ALL_FEATURES + [train.TARGET_COL]].apply(
        tuple, axis=1
    ).isin(set(raw[train.ALL_FEATURES + [train.TARGET_COL]].apply(tuple, axis=1)))
    extra = curated[extra_mask]
    raw_like = curated[~extra_mask]
    raw_dedup = raw_like.drop_duplicates(subset=train.ALL_FEATURES + [train.TARGET_COL]).reset_index(drop=True)
    template = joblib.load(ARTIFACT_PATH)

    random_results = []
    grouped_results = []
    raw_results = []
    extra_results = []
    technical_results = []
    personality_results = []
    importance_results = []
    grouped_raw_results = []
    grouped_permutation_results = []
    current_split_membership = []
    decomposition_results = []

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
        raw_groups = raw_like[train.PERSONALITY_FEATURES].apply(tuple, axis=1)
        raw_train_idx, raw_test_idx = next(
            GroupShuffleSplit(n_splits=1, test_size=train.TEST_SIZE, random_state=seed)
            .split(raw_like[train.ALL_FEATURES], labels(raw_like), groups=raw_groups)
        )
        grouped_raw_model = fit_clone(
            template,
            raw_like[train.ALL_FEATURES].iloc[raw_train_idx],
            labels(raw_like).iloc[raw_train_idx],
            seed,
        )
        grouped_raw_test_x = raw_like[train.ALL_FEATURES].iloc[raw_test_idx]
        grouped_raw_test_y = labels(raw_like).iloc[raw_test_idx]
        grouped_raw_results.append(metrics(grouped_raw_model, grouped_raw_test_x, grouped_raw_test_y))
        permutation = permutation_importance(
            grouped_raw_model,
            grouped_raw_test_x,
            grouped_raw_test_y,
            scoring="accuracy",
            n_repeats=5,
            random_state=seed,
        )
        grouped_permutation_results.append(
            (
                float(permutation.importances_mean[:10].sum()),
                float(permutation.importances_mean[10:].sum()),
            )
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
        membership = np.array([
            tuple(row) in set(map(tuple, x_train.itertuples(index=False, name=None)))
            for row in x_test.itertuples(index=False, name=None)
        ])
        predictions = model.predict(x_test)
        current_split_membership.append(
            (
                float(accuracy_score(y_test[membership], predictions[membership])),
                float(accuracy_score(y_test[~membership], predictions[~membership])),
                int(membership.sum()),
                int((~membership).sum()),
            )
        )
        raw_test_mask = x_test.apply(tuple, axis=1).isin(
            set(raw_like[train.ALL_FEATURES].apply(tuple, axis=1))
        ).to_numpy()
        decomposition_results.append(
            (
                float(accuracy_score(y_test[raw_test_mask], predictions[raw_test_mask])),
                float(accuracy_score(y_test[~raw_test_mask], predictions[~raw_test_mask])),
                int(raw_test_mask.sum()),
                int((~raw_test_mask).sum()),
            )
        )

    print(f"CURATED_ROWS={len(curated)} RAW_ROWS={len(raw_like)} EXTRA_ROWS={len(extra)}")
    summarize("CURRENT_RANDOM_STRATIFIED", random_results)
    summarize("GROUPED_BY_PERSONALITY_VECTOR", grouped_results)
    summarize("RAW_ROWS_ONLY", raw_results)
    summarize("RAW_TRAIN_EXTRA_TEST", extra_results)
    summarize("TECHNICAL_FEATURES_ONLY", technical_results)
    summarize("PERSONALITY_FEATURES_ONLY", personality_results)
    print_seed_metrics("CURRENT_RANDOM_STRATIFIED", SEEDS, random_results)
    print_seed_metrics("GROUPED_BY_PERSONALITY_VECTOR", SEEDS, grouped_results)
    print_seed_metrics("RAW_ROWS_ONLY", SEEDS, raw_results)
    print_seed_metrics("RAW_TRAIN_EXTRA_TEST", SEEDS, extra_results)
    print_seed_metrics("TECHNICAL_FEATURES_ONLY", SEEDS, technical_results)
    print_seed_metrics("PERSONALITY_FEATURES_ONLY", SEEDS, personality_results)
    print_seed_metrics("GROUPED_RAW_ROWS_ONLY", SEEDS, grouped_raw_results)
    personality_importance = np.array([value[0] for value in importance_results])
    pca_importance = np.array([value[1] for value in importance_results])
    print(
        f"CURRENT_SPLIT_FEATURE_IMPORTANCE: personality={personality_importance.mean():.6f} "
        f"+/- {personality_importance.std():.6f}; pca_2={pca_importance.mean():.6f} "
        f"+/- {pca_importance.std():.6f}"
    )
    grouped_personality = np.array([value[0] for value in grouped_permutation_results])
    grouped_technical = np.array([value[1] for value in grouped_permutation_results])
    print(
        f"GROUPED_RAW_PERMUTATION_IMPORTANCE: personality={grouped_personality.mean():.6f} "
        f"+/- {grouped_personality.std():.6f}; technical={grouped_technical.mean():.6f} "
        f"+/- {grouped_technical.std():.6f}"
    )

    x = curated[train.ALL_FEATURES]
    x_train, x_test, _, _ = train_test_split(
        x, labels(curated), test_size=train.TEST_SIZE, random_state=train.RANDOM_SEED, stratify=labels(curated)
    )
    train_vectors = set(map(tuple, x_train.itertuples(index=False, name=None)))
    overlap = sum(tuple(row) in train_vectors for row in x_test.itertuples(index=False, name=None))
    print(f"CURRENT_SPLIT_TEST_ROWS_WITH_TRAINING_VECTOR={overlap}/{len(x_test)}")
    for seed, (in_acc, out_acc, in_count, out_count) in zip(SEEDS, current_split_membership):
        print(
            f"CURRENT_SPLIT_MEMBERSHIP_SEED={seed}: in_training_vector_accuracy={in_acc:.6f} "
            f"({in_count}) out_of_training_vector_accuracy={out_acc:.6f} ({out_count})"
        )
    print("CURRENT_SPLIT_RAW_EXTRA_TEST_ACCURACY")
    for seed, (raw_acc, extra_acc, raw_count, extra_count) in zip(SEEDS, decomposition_results):
        print(
            f"SEED={seed}: raw_accuracy={raw_acc:.6f} ({raw_count}) "
            f"extra_accuracy={extra_acc:.6f} ({extra_count})"
        )
    raw_accs = np.array([v[0] for v in decomposition_results])
    extra_accs = np.array([v[1] for v in decomposition_results])
    print(
        f"CURRENT_SPLIT_RAW_TEST_ACCURACY_MEAN_STD={raw_accs.mean():.6f} +/- {raw_accs.std():.6f}"
    )
    print(
        f"CURRENT_SPLIT_EXTRA_TEST_ACCURACY_MEAN_STD={extra_accs.mean():.6f} +/- {extra_accs.std():.6f}"
    )

    personas = raw_dedup[train.PERSONALITY_FEATURES].apply(tuple, axis=1)
    persona_role = raw_dedup.assign(_persona=personas).drop_duplicates(
        subset=["_persona", train.TARGET_COL]
    )
    print(f"RAW_DISTINCT_ROWS_AFTER_EXACT_DEDUP={len(raw_dedup)}")
    print("PERSONAS_PER_ROLE")
    print(
        persona_role.groupby(train.TARGET_COL)["_persona"].nunique().sort_index().to_string()
    )

    x_raw = raw_dedup[train.ALL_FEATURES]
    y_raw = labels(raw_dedup)
    groups_raw = raw_dedup[train.PERSONALITY_FEATURES].apply(tuple, axis=1)
    model_factories = {
        "GROUPKFold_CURRENT_RF_PIPELINE": lambda: clone(template),
        "GROUPKFold_1NN_PERSONALITY": lambda: KNeighborsClassifier(n_neighbors=1),
        "GROUPKFold_LOGISTIC_PERSONALITY": lambda: Pipeline(
            [("scaler", StandardScaler()), ("classifier", LogisticRegression(max_iter=2000, random_state=42))]
        ),
        "GROUPKFold_RF_TECHNICAL": lambda: RandomForestClassifier(
            **template.named_steps["classifier"].get_params()
        ),
    }
    model_columns = {
        "GROUPKFold_CURRENT_RF_PIPELINE": train.ALL_FEATURES,
        "GROUPKFold_1NN_PERSONALITY": train.PERSONALITY_FEATURES,
        "GROUPKFold_LOGISTIC_PERSONALITY": train.PERSONALITY_FEATURES,
        "GROUPKFold_RF_TECHNICAL": train.TECHNICAL_FEATURES,
    }
    print("PERSONA_GROUPKFOlD_RESULTS")
    for name, factory in model_factories.items():
        columns = model_columns[name]
        results = group_fold_metrics(factory, x_raw[columns], y_raw, groups_raw)
        values = np.array([row[1] for row in results])
        print(f"{name}_MEAN_ACCURACY={values.mean():.6f} +/- {values.std():.6f}")
        for fold, accuracy, macro_f1 in results:
            print(f"{name}_FOLD={fold}: accuracy={accuracy:.6f} macro_f1={macro_f1:.6f}")

    persona_vectors = list(dict.fromkeys(groups_raw))
    persona_roles = persona_role.groupby("_persona")[train.TARGET_COL].agg(set).to_dict()
    distances = pairwise_distances(np.asarray(persona_vectors, dtype=float), metric="euclidean")
    same_role = []
    different_role = []
    for i in range(len(persona_vectors)):
        for j in range(i + 1, len(persona_vectors)):
            if persona_roles[persona_vectors[i]] & persona_roles[persona_vectors[j]]:
                same_role.append(distances[i, j])
            else:
                different_role.append(distances[i, j])
    print(
        f"PERSONA_DISTANCE_SAME_ROLE_MEAN={np.mean(same_role):.6f} "
        f"DIFFERENT_ROLE_MEAN={np.mean(different_role):.6f}"
    )
    majority_accuracy = y_raw.value_counts(normalize=True).max()
    print(f"MAJORITY_CLASS_BASELINE_ACCURACY={majority_accuracy:.6f}")


if __name__ == "__main__":
    main()
