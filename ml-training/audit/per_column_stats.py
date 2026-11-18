"""
Step 3: Per-column stats for raw vs extra rows.
Step 4: Accuracy on raw test rows vs extra-rows test set (5 seeds, mean±std);
         distinct raw row count after exact dedup; personas-per-role table.
"""
import sys
import pathlib
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"

TECHNICAL_FEATURES = [
    "Computer Architecture",
    "Programming Skills",
    "Project Management",
    "Communication skills",
]
PERSONALITY_FEATURES = [
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
ALL_FEATURES = TECHNICAL_FEATURES + PERSONALITY_FEATURES
TARGET_COL = "Role"

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
if not DATA_PATH.exists():
    print(f"ERROR: dataset not found at {DATA_PATH}")
    sys.exit(1)

df = pd.read_csv(DATA_PATH)
if df.columns[0].startswith("Unnamed"):
    df = df.drop(df.columns[0], axis=1)

print(f"Total rows loaded: {len(df)}")

def _all_integer(row: pd.Series) -> bool:
    return all(float(v) == int(float(v)) for v in row)

mask_raw = df[TECHNICAL_FEATURES].apply(_all_integer, axis=1)
df_raw   = df[mask_raw].reset_index(drop=True)
df_extra = df[~mask_raw].reset_index(drop=True)

print(f"Raw rows:   {len(df_raw)}")
print(f"Extra rows: {len(df_extra)}")
print()

# ---------------------------------------------------------------------------
# STEP 3A: Per-column stats for TECHNICAL features — raw rows
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 3A: Per-column technical feature stats — RAW rows")
print("=" * 60)
for col in TECHNICAL_FEATURES:
    s = df_raw[col]
    print(f"  {col}")
    print(f"    min={s.min():.4f}  max={s.max():.4f}  mean={s.mean():.4f}  std={s.std():.4f}")
print()

print("=" * 60)
print("STEP 3B: Per-column technical feature stats — EXTRA rows")
print("=" * 60)
for col in TECHNICAL_FEATURES:
    s = df_extra[col]
    print(f"  {col}")
    print(f"    min={s.min():.4f}  max={s.max():.4f}  mean={s.mean():.4f}  std={s.std():.4f}")
print()

# ---------------------------------------------------------------------------
# STEP 3C: Per-column personality min/max — raw vs extra
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 3C: Per-column personality feature min/max (raw vs extra)")
print("=" * 60)
print(f"{'Feature':<30} {'raw_min':>8} {'raw_max':>8} {'ext_min':>8} {'ext_max':>8}")
print("-" * 70)
for col in PERSONALITY_FEATURES:
    rmin = df_raw[col].min()
    rmax = df_raw[col].max()
    emin = df_extra[col].min()
    emax = df_extra[col].max()
    print(f"  {col:<28} {rmin:>8.4f} {rmax:>8.4f} {emin:>8.4f} {emax:>8.4f}")
print()

# ---------------------------------------------------------------------------
# STEP 4A: Distinct raw rows after exact dedup
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 4A: Distinct raw rows after exact duplicate removal")
print("=" * 60)
n_raw          = len(df_raw)
n_raw_dedup    = len(df_raw.drop_duplicates())
n_duplicates   = n_raw - n_raw_dedup
print(f"  Raw rows total      : {n_raw}")
print(f"  Exact duplicates    : {n_duplicates}")
print(f"  Distinct raw rows   : {n_raw_dedup}")
print()

# ---------------------------------------------------------------------------
# STEP 4B: Personas-per-role table
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 4B: Distinct personality vectors (personas) per role — raw rows")
print("=" * 60)
personas_per_role = (
    df_raw.groupby(TARGET_COL)[PERSONALITY_FEATURES]
    .apply(lambda g: len(g.drop_duplicates()))
    .sort_values(ascending=False)
)
for role, count in personas_per_role.items():
    print(f"  {role:<40} {count:>5} distinct personas")
print(f"\n  TOTAL distinct personality vectors: {len(df_raw[PERSONALITY_FEATURES].drop_duplicates())}")
print()

# ---------------------------------------------------------------------------
# STEP 4C: Accuracy on raw test rows vs extra-rows test set (5 seeds)
# ---------------------------------------------------------------------------
print("=" * 60)
print("STEP 4C: Accuracy — 5 seeds, raw test set vs extra-row test set")
print("=" * 60)

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import accuracy_score

RF_PARAMS = dict(
    bootstrap=True, max_depth=10, max_features="sqrt",
    min_samples_leaf=7, min_samples_split=7, n_estimators=200
)

SEEDS = [0, 1, 2, 3, 4]

le = LabelEncoder()
le.fit(df_raw[TARGET_COL])

raw_accs   = []
extra_accs = []

for seed in SEEDS:
    # Build pipeline
    tech_pipe = Pipeline([("scaler", StandardScaler()), ("pca", PCA(n_components=2, random_state=seed))])
    pre = ColumnTransformer([
        ("pers", "passthrough", PERSONALITY_FEATURES),
        ("tech", tech_pipe, TECHNICAL_FEATURES),
    ])
    clf = Pipeline([("pre", pre), ("rf", RandomForestClassifier(random_state=seed, **RF_PARAMS))])

    # Train on raw rows
    X_raw = df_raw[ALL_FEATURES]
    y_raw = le.transform(df_raw[TARGET_COL])
    X_tr, X_te, y_tr, y_te = train_test_split(X_raw, y_raw, test_size=0.20, random_state=seed, stratify=y_raw)
    clf.fit(X_tr, y_tr)

    # Accuracy on raw test set
    raw_accs.append(accuracy_score(y_te, clf.predict(X_te)))

    # Accuracy on extra rows (predict only; labels must be in le.classes_)
    # Some extra-row roles may not exist in raw training labels — keep only known
    extra_known_mask = df_extra[TARGET_COL].isin(le.classes_)
    df_extra_known = df_extra[extra_known_mask]
    if len(df_extra_known) > 0:
        X_ext = df_extra_known[ALL_FEATURES]
        y_ext = le.transform(df_extra_known[TARGET_COL])
        extra_accs.append(accuracy_score(y_ext, clf.predict(X_ext)))
    else:
        extra_accs.append(float("nan"))

print(f"  Seeds: {SEEDS}")
print(f"  Raw test accuracy per seed  : {[round(a,4) for a in raw_accs]}")
print(f"  Raw test accuracy mean±std  : {np.mean(raw_accs):.4f} ± {np.std(raw_accs):.4f}")
print()
print(f"  Extra-row accuracy per seed : {[round(a,4) for a in extra_accs]}")
print(f"  Extra-row accuracy mean±std : {np.nanmean(extra_accs):.4f} ± {np.nanstd(extra_accs):.4f}")
print()
print("DONE")
