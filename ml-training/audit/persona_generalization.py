"""
Step 5: Persona generalization on deduplicated raw rows, GroupKFold by persona.
  Models: (1) current RF pipeline, (2) 1-NN on standardized personality,
          (3) logistic regression on standardized personality,
          (4) RF on technical features only.
  Also: mean intra-role vs inter-role distance between personas.
  Also: majority-class baseline.
"""
import pathlib
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import GroupKFold
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
# Load + filter raw rows + exact dedup
# ---------------------------------------------------------------------------
df = pd.read_csv(DATA_PATH)
if df.columns[0].startswith("Unnamed"):
    df = df.drop(df.columns[0], axis=1)

def _all_integer(row):
    return all(float(v) == int(float(v)) for v in row)

mask_raw = df[TECHNICAL_FEATURES].apply(_all_integer, axis=1)
df_raw   = df[mask_raw].reset_index(drop=True)
df_dedup = df_raw.drop_duplicates().reset_index(drop=True)

print(f"Raw rows: {len(df_raw)}, after exact dedup: {len(df_dedup)}")
print()

# ---------------------------------------------------------------------------
# Encode labels
# ---------------------------------------------------------------------------
le = LabelEncoder()
y = le.fit_transform(df_dedup[TARGET_COL])
X = df_dedup[ALL_FEATURES]

# ---------------------------------------------------------------------------
# Persona groups (string key of personality vector)
# ---------------------------------------------------------------------------
groups = df_dedup[PERSONALITY_FEATURES].apply(
    lambda row: "_".join(f"{v:.4f}" for v in row), axis=1
).values

n_groups = len(np.unique(groups))
print(f"Distinct persona groups for GroupKFold: {n_groups}")
print()

# ---------------------------------------------------------------------------
# Majority-class baseline
# ---------------------------------------------------------------------------
from collections import Counter
counts = Counter(y)
majority_frac = counts.most_common(1)[0][1] / len(y)
print(f"Majority-class baseline (unduplicated raw): {majority_frac:.4f}")
print()

# ---------------------------------------------------------------------------
# GroupKFold (5 folds)
# ---------------------------------------------------------------------------
gkf = GroupKFold(n_splits=5)

RF_PARAMS = dict(
    bootstrap=True, max_depth=10, max_features="sqrt",
    min_samples_leaf=7, min_samples_split=7, n_estimators=200, random_state=42
)

def build_rf_pipeline():
    tech_pipe = Pipeline([("scaler", StandardScaler()), ("pca", PCA(n_components=2, random_state=42))])
    pre = ColumnTransformer([
        ("pers", "passthrough", PERSONALITY_FEATURES),
        ("tech", tech_pipe, TECHNICAL_FEATURES),
    ])
    return Pipeline([("pre", pre), ("rf", RandomForestClassifier(**RF_PARAMS))])

def build_1nn_personality():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("knn", KNeighborsClassifier(n_neighbors=1)),
    ])

def build_lr_personality():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000, random_state=42)),
    ])

def build_rf_technical():
    tech_pipe = Pipeline([("scaler", StandardScaler()), ("pca", PCA(n_components=2, random_state=42))])
    return Pipeline([("tech", tech_pipe), ("rf", RandomForestClassifier(**RF_PARAMS))])

models = {
    "RF_pipeline (full)":           (build_rf_pipeline,     X),
    "1-NN (personality only)":      (build_1nn_personality,  df_dedup[PERSONALITY_FEATURES]),
    "LogReg (personality only)":    (build_lr_personality,   df_dedup[PERSONALITY_FEATURES]),
    "RF (technical only)":          (build_rf_technical,     df_dedup[TECHNICAL_FEATURES]),
}

print("=" * 70)
print("STEP 5: GroupKFold by persona — per-fold accuracy")
print("=" * 70)

for name, (builder, X_use) in models.items():
    fold_accs = []
    for fold, (train_idx, test_idx) in enumerate(gkf.split(X_use, y, groups=groups)):
        X_tr = X_use.iloc[train_idx] if hasattr(X_use, 'iloc') else X_use[train_idx]
        X_te = X_use.iloc[test_idx]  if hasattr(X_use, 'iloc') else X_use[test_idx]
        y_tr, y_te = y[train_idx], y[test_idx]
        clf = builder()
        clf.fit(X_tr, y_tr)
        acc = accuracy_score(y_te, clf.predict(X_te))
        fold_accs.append(acc)
    mean_acc = np.mean(fold_accs)
    std_acc  = np.std(fold_accs)
    print(f"\n  {name}")
    for i, a in enumerate(fold_accs):
        print(f"    Fold {i+1}: {a:.4f}")
    print(f"    MEAN: {mean_acc:.4f}  STD: {std_acc:.4f}")

print()

# ---------------------------------------------------------------------------
# Mean intra-role vs inter-role distance between personas
# ---------------------------------------------------------------------------
print("=" * 70)
print("STEP 5: Mean distance between personas of same role vs different roles")
print("=" * 70)

persona_df = df_dedup[PERSONALITY_FEATURES + [TARGET_COL]].drop_duplicates(subset=PERSONALITY_FEATURES)
print(f"  Distinct persona rows: {len(persona_df)}")

scaler_p = StandardScaler()
P = scaler_p.fit_transform(persona_df[PERSONALITY_FEATURES].values)
roles = persona_df[TARGET_COL].values

from sklearn.metrics import pairwise_distances
D = pairwise_distances(P, metric="euclidean")

n = len(P)
intra, inter = [], []
for i in range(n):
    for j in range(i+1, n):
        if roles[i] == roles[j]:
            intra.append(D[i, j])
        else:
            inter.append(D[i, j])

print(f"  Intra-role pairs: {len(intra)}")
print(f"  Inter-role pairs: {len(inter)}")
print(f"  Mean intra-role distance: {np.mean(intra):.4f}  std: {np.std(intra):.4f}")
print(f"  Mean inter-role distance: {np.mean(inter):.4f}  std: {np.std(inter):.4f}")
print()
print("DONE")
