"""
Step 4 extended audit:
  a. Per-role mean of each of the 4 technical columns on raw rows.
  b. Persona count per role, with min and max rows per persona.
  c. Repeated persona-grouped CV (10 repeats, StratifiedGroupKFold with shuffle
     and different seeds) for RF pipeline, LogReg, 1-NN.
     Print mean and std over repeats, plus RF-minus-LogReg per repeat.
"""
import pathlib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"

TECHNICAL_FEATURES = [
    "Computer Architecture", "Programming Skills",
    "Project Management", "Communication skills",
]
PERSONALITY_FEATURES = [
    "Openness", "Conscientousness", "Extraversion", "Agreeableness",
    "Emotional_Range", "Conversation", "Openness to Change", "Hedonism",
    "Self-enhancement", "Self-transcendence",
]
ALL_FEATURES = TECHNICAL_FEATURES + PERSONALITY_FEATURES
TARGET_COL = "Role"

# ---------------------------------------------------------------------------
# Load + filter raw rows
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA_PATH)
if df.columns[0].startswith("Unnamed"):
    df = df.drop(df.columns[0], axis=1)

def _all_integer(row):
    return all(float(v) == int(float(v)) for v in row)

mask_raw = df[TECHNICAL_FEATURES].apply(_all_integer, axis=1)
df_raw = df[mask_raw].reset_index(drop=True)
print(f"Raw rows: {len(df_raw)}")
print()

# ---------------------------------------------------------------------------
# STEP 4a: Per-role mean of each technical column
# ---------------------------------------------------------------------------
print("=" * 70)
print("STEP 4a: Per-role mean of each of the 4 technical columns (raw rows)")
print("=" * 70)
roles_sorted = sorted(df_raw[TARGET_COL].unique())
header = f"{'Role':<42}" + "".join(f"  {c[:8]:>8}" for c in TECHNICAL_FEATURES)
print(header)
print("-" * (42 + 4 * 10))
for role in roles_sorted:
    sub = df_raw[df_raw[TARGET_COL] == role]
    means = [sub[c].mean() for c in TECHNICAL_FEATURES]
    row_str = f"  {role:<40}" + "".join(f"  {m:>8.4f}" for m in means)
    print(row_str)
print()

# ---------------------------------------------------------------------------
# STEP 4b: Persona count per role, with min/max rows per persona
# ---------------------------------------------------------------------------
print("=" * 70)
print("STEP 4b: Persona count per role, with min and max rows per persona")
print("=" * 70)
print(f"{'Role':<42} {'#Personas':>9} {'min_rows':>9} {'max_rows':>9} {'total_rows':>10}")
print("-" * 80)
for role in roles_sorted:
    sub = df_raw[df_raw[TARGET_COL] == role]
    persona_counts = sub.groupby(PERSONALITY_FEATURES).size()
    print(
        f"  {role:<40} {len(persona_counts):>9} "
        f"{persona_counts.min():>9} {persona_counts.max():>9} "
        f"{len(sub):>10}"
    )
print()

# ---------------------------------------------------------------------------
# STEP 4c: Repeated StratifiedGroupKFold (10 repeats)
# ---------------------------------------------------------------------------
print("=" * 70)
print("STEP 4c: Repeated StratifiedGroupKFold (10 repeats, 5 folds each)")
print("         Dataset: deduplicated raw rows (3,116)")
print("=" * 70)

df_dedup = df_raw.drop_duplicates().reset_index(drop=True)
print(f"Deduplicated raw rows: {len(df_dedup)}")

le = LabelEncoder()
y = le.fit_transform(df_dedup[TARGET_COL])
X = df_dedup[ALL_FEATURES]

groups = df_dedup[PERSONALITY_FEATURES].apply(
    lambda row: "_".join(f"{v:.4f}" for v in row), axis=1
).values

RF_PARAMS = dict(
    bootstrap=True, max_depth=10, max_features="sqrt",
    min_samples_leaf=7, min_samples_split=7, n_estimators=200
)

SEEDS = list(range(10))  # 10 repeat seeds

def build_rf(seed):
    tech = Pipeline([("sc", StandardScaler()), ("pca", PCA(n_components=2, random_state=seed))])
    pre = ColumnTransformer([
        ("pers", "passthrough", PERSONALITY_FEATURES),
        ("tech", tech, TECHNICAL_FEATURES),
    ])
    return Pipeline([("pre", pre), ("rf", RandomForestClassifier(random_state=seed, **RF_PARAMS))])

def build_lr(seed):
    return Pipeline([("sc", StandardScaler()), ("lr", LogisticRegression(max_iter=2000, random_state=seed))])

def build_1nn():
    return Pipeline([("sc", StandardScaler()), ("knn", KNeighborsClassifier(n_neighbors=1))])

rf_means, lr_means, nn_means = [], [], []

print()
print(f"{'Repeat':<8} {'RF_mean':>9} {'LR_mean':>9} {'1NN_mean':>9} {'RF-LR':>9}")
print("-" * 50)

for seed in SEEDS:
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
    rf_folds, lr_folds, nn_folds = [], [], []

    for train_idx, test_idx in sgkf.split(X, y, groups=groups):
        X_tr, X_te = X.iloc[train_idx], X.iloc[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]

        # RF
        clf_rf = build_rf(seed)
        clf_rf.fit(X_tr, y_tr)
        rf_folds.append(accuracy_score(y_te, clf_rf.predict(X_te)))

        # LogReg (personality only)
        clf_lr = build_lr(seed)
        clf_lr.fit(X_tr[PERSONALITY_FEATURES], y_tr)
        lr_folds.append(accuracy_score(y_te, clf_lr.predict(X_te[PERSONALITY_FEATURES])))

        # 1-NN (personality only)
        clf_nn = build_1nn()
        clf_nn.fit(X_tr[PERSONALITY_FEATURES], y_tr)
        nn_folds.append(accuracy_score(y_te, clf_nn.predict(X_te[PERSONALITY_FEATURES])))

    rf_m = np.mean(rf_folds)
    lr_m = np.mean(lr_folds)
    nn_m = np.mean(nn_folds)
    rf_means.append(rf_m)
    lr_means.append(lr_m)
    nn_means.append(nn_m)
    diff = rf_m - lr_m
    print(f"  {seed:<6} {rf_m:>9.4f} {lr_m:>9.4f} {nn_m:>9.4f} {diff:>+9.4f}")

print("-" * 50)
print(f"  {'MEAN':<6} {np.mean(rf_means):>9.4f} {np.mean(lr_means):>9.4f} {np.mean(nn_means):>9.4f} {np.mean(np.array(rf_means)-np.array(lr_means)):>+9.4f}")
print(f"  {'STD':<6} {np.std(rf_means):>9.4f} {np.std(lr_means):>9.4f} {np.std(nn_means):>9.4f} {np.std(np.array(rf_means)-np.array(lr_means)):>9.4f}")
print()
print("DONE")
