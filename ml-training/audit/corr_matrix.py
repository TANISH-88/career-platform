"""Step 4: Correlation matrix of the 4 raw technical columns,
   whether any two columns are identical, and whether columns are
   permutations of each other (same sorted values)."""
import pathlib
import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "data" / "CareerMapping1.csv"

TECHNICAL_FEATURES = [
    "Computer Architecture",
    "Programming Skills",
    "Project Management",
    "Communication skills",
]

df = pd.read_csv(DATA_PATH)
if df.columns[0].startswith("Unnamed"):
    df = df.drop(df.columns[0], axis=1)

def _all_integer(row):
    return all(float(v) == int(float(v)) for v in row)

mask_raw = df[TECHNICAL_FEATURES].apply(_all_integer, axis=1)
df_raw   = df[mask_raw].reset_index(drop=True)

print(f"Raw rows: {len(df_raw)}")
print()

# Correlation matrix
print("=" * 60)
print("CORRELATION MATRIX (raw rows, 4 technical columns)")
print("=" * 60)
corr = df_raw[TECHNICAL_FEATURES].corr()
print(corr.to_string())
print()

# Are any two columns identical (element-wise)?
print("=" * 60)
print("ARE ANY TWO COLUMNS IDENTICAL (element-wise)?")
print("=" * 60)
cols = TECHNICAL_FEATURES
for i in range(len(cols)):
    for j in range(i+1, len(cols)):
        identical = (df_raw[cols[i]].values == df_raw[cols[j]].values).all()
        print(f"  {cols[i]} == {cols[j]}: {identical}")
print()

# Are any two columns permutations of each other (same sorted values)?
print("=" * 60)
print("ARE ANY TWO COLUMNS PERMUTATIONS (same sorted values)?")
print("=" * 60)
for i in range(len(cols)):
    for j in range(i+1, len(cols)):
        perm = (np.sort(df_raw[cols[i]].values) == np.sort(df_raw[cols[j]].values)).all()
        print(f"  sort({cols[i]}) == sort({cols[j]}): {perm}")
print()

# Value counts for each column
print("=" * 60)
print("VALUE COUNTS PER COLUMN (raw rows)")
print("=" * 60)
for col in TECHNICAL_FEATURES:
    vc = df_raw[col].value_counts().sort_index()
    print(f"  {col}: {vc.to_dict()}")
print()

print("DONE")
