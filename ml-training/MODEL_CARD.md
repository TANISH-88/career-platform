# Model Card — Career Prediction Random Forest (career-rf)

## Data

| Property | Value |
|---|---|
| Source file | `data/CareerMapping1.csv` |
| MD5 (at training time) | `7192e48953b32a0448b020198591567b` |
| Total rows in file | 10,179 |
| Raw rows used for training | **9,179** (1,000 unknown-origin extra rows excluded by default) |
| Roles (classes) | 16 |
| Train rows (80% of 9,179) | 7,343 |
| Test rows (20% of 9,179) | 1,836 |

> [!NOTE]
> The 1,000 extra rows at indices 9,179–10,178 are **excluded by default** from training
> and evaluation (`train.load_data(exclude_extra_rows=True)`). Their origin is unknown.
> The original dataset file is preserved unmodified.

## Training Configuration

| Parameter | Value |
|---|---|
| Script | `ml-training/train.py` |
| Random seed | 42 |
| Split | 80 / 20, stratified by role |
| Preprocessing | `StandardScaler` + `PCA` fit on **train only** |
| sklearn version | 1.7.1 |
| Params file | `ml-training/params.yaml` |
| MLflow experiment | `career-prediction` |
| Registered model | `career-rf` (full `sklearn.Pipeline`) |

## Evaluation on Held-Out Test Set (seed 42 stratified split, 1,836 rows)

> [!IMPORTANT]
> The test set is a **random stratified split of the same 9,179 raw rows** used for training
> (the 1,000 unknown-origin extra rows are excluded by default).
> Due to severe exact-duplicate contamination (see Data Quality section below),
> random-split accuracy does **not** represent generalisation to unseen individuals.
> Do not interpret these numbers as proof of real-world performance.

| Metric | Value |
|---|---|
| Top-1 accuracy (random split, seed 42) | **0.906** |
| 5-seed mean (random split) | 0.907 ± 0.008 |

### 5-Seed Ablation (train-only preprocessing, stratified split)

| Seeds | Per-seed accuracy | Mean | Std |
|---|---|---|---|
| 42, 123, 456, 789, 2024 | 0.906, 0.924, 0.899, 0.902, 0.909 | 0.908 | 0.009 |

The ablation also compared fitting scaler/PCA on all data (leakage) vs. train only.
Mean difference between conditions: < 0.002 — within one standard deviation of seed
noise. **Leakage is not a detectable effect on this dataset.**

## Data Quality and Generalisation Warning

### Exact duplicates

The raw dataset (`CareerMap-...csv`, 9,179 rows) contains **1,073 distinct rows** that
appear more than once, accounting for **6,063 extra occurrences**.
When training on this data with a random split, identical rows appear in both train and
test sets, inflating accuracy artificially.

### Unknown-origin extra rows

`CareerMapping1.csv` (the training source, 10,179 rows) contains **1,000 additional rows**
not present in the raw dataset. These rows:

- Have **fractional technical features** in `[0, 1]` (raw data uses integers in `[0, 6]`)
- Have **personality profiles not matching any raw-dataset vector** (0/1,000 match)
- Cover the **full `[0, 1]` range** uniformly, unlike the skewed raw distributions
- Were appended as rows 9,179–10,178 in `CareerMapping1.csv` at the initial commit

**Origin: unknown.** The generation mechanism has not been identified.

**Decision: `origin unknown, excluded`** — these rows are excluded from default training
and evaluation by `train.load_data(exclude_extra_rows=True)` (the default).
The original dataset file is never modified. Pass `exclude_extra_rows=False` only
when explicitly investigating these rows.

A reproducible test proves the exclusion:
```
python -m pytest ml-training/tests/test_extra_row_exclusion.py -v
```

> `origin unknown, excluded` from grouped-accuracy evaluation (see below).

### Grouped-by-personality accuracy (unseen-persona test)

When the model is evaluated on personality profiles **not seen during training**
(grouped cross-validation), accuracy drops dramatically.

Reproduce with: `python ml-training/audit/eval_sensitivity.py`

| Evaluation method | Accuracy | Macro-F1 |
|---|---|---|
| Random stratified split (5 seeds) | **0.902 ± 0.004** | 0.902 ± 0.005 |
| Grouped by personality vector (5 seeds) | **0.188 ± 0.045** | 0.149 ± 0.019 |
| GroupKFold persona generalisation (5 folds) | **0.256 ± 0.058** | — |
| Raw rows only (random split, 5 seeds) | 0.995 ± 0.003 | — |
| Raw-trained, extra-rows test (5 seeds) | 0.056 ± 0.003 | — |
| Majority-class baseline | 0.113 | — |

> [!WARNING]
> The random-split accuracy of **0.902** reflects test rows that largely share
> personality vectors with training rows (1,411 / 2,036 test rows, ~69%, have an
> exact personality vector twin in training). On those in-training-vector rows,
> accuracy is ~0.999; on out-of-training-vector rows it falls to ~0.69.
> Grouped accuracy of **0.188** is a more realistic upper bound for new individuals.
> The GroupKFold result of **0.256** (barely above majority-class baseline of 0.113)
> corroborates this.

**Random-split accuracy must not be cited as proof of generalisation.**

## Comparison with Previous Model (pre-M1, commit `2d999ed`)

### Uncorrected comparison (all 2,036 new-split test rows)

The old model was trained without a fixed split on many of these rows; this
comparison is **not fair** because the rows being evaluated were likely in the
old model's training set.

| | Count | % |
|---|---|---|
| Predictions changed | 108 / 2,036 | 5.30% |
| Largest probability shift | 50.88% | — |
| Mean probability shift | 0.79% | — |

### Fair comparison — intersection of both held-out sets

Only rows that were **held out by both** the old (unstratified, seed 42) and new
(stratified, seed 42) splits are used here. Rows that were in the old training
set but in the new test set are excluded.

| | Value |
|---|---|
| Rows in intersection | **388** (of 2,036 in each set) |
| Old model accuracy | **92.5%** |
| New model accuracy | **91.5%** |
| Accuracy delta | −1.0 pp |
| Predictions changed | 17 / 388 (4.38%) |

The −1.0 pp gap on the intersection is within the ±0.9 pp seed-noise standard
deviation from the ablation. It is **not statistically distinguishable** from
sampling variance on 388 rows. The old model's apparent advantage likely comes
from training on the unstratified split, which happened to place easier examples
in the test set for that particular seed.

## Known Limitations

1. **Single dataset.** Trained and evaluated on one proprietary dataset
   (`CareerMapping1.csv`). No external validation set exists.
2. **16 fixed roles.** The model cannot predict roles outside the 16 classes it
   was trained on. Adding or renaming a role requires full retraining.
3. **No temporal validation.** All rows are treated as i.i.d. If the dataset has
   any time ordering, the current split leaks future information into training.
4. **No demographic audit.** Fairness across gender, geography, or other
   sensitive attributes has not been measured.
5. **Serving path uses separate pkl files.** The serving code
   (`feature_mapper.py`, `predictor.py`) loads `scaler.pkl`, `pca.pkl`,
   `frf.pkl` independently. The MLflow-registered `Pipeline` artifact is not
   yet used at serve time; sync is maintained by `promote.py` convention, not
   enforced structurally.

## Input Units (Serving Boundary)

Training data uses two different scales:

| Feature group | Training scale | UI scale |
|---|---|---|
| Technical (4 features: Computer Architecture, Programming Skills, Project Management, Communication skills) | `[0, 6]` (integers, occasionally fractional) | `[1, 10]` |
| Personality (10 features: Openness … Self-transcendence) | `[0, 1]` (continuous floats) | `[1, 10]` |

`FeatureMapper.transform(ui_values)` converts UI → training units via:

```
technical_train  = (ui - 1) / 9 * 6
personality_train = (ui - 1) / 9 * 1
```

Values outside `[1, 10]` are clamped and logged at WARNING level (the
frontend sends `0` for empty inputs).

### History

Prior to commit `fix(serve): convert UI [1-10] inputs to training units`,
`FeatureMapper.transform()` passed UI-scale values directly to the scaler.
Personality values of `1–10` were all far above the model's training range
`[0, 1]`, landing in a region where the random forest has no training data.
All personality inputs produced **identical** probability vectors. Technical
inputs (1–10) partially overlapped training range (0–6), masking the bug.

The 160-row fixture converted to UI units then passed through the old
transform matched only **29 of 160** (18%) top-1 predictions vs. direct
training-unit prediction.

### Limitation

The linear map from `[1, 10]` to training range is an assumption. The
personality features (mean ~0.13–0.71 in `[0, 1]`) appear to follow skewed
distributions — the linear mapping from `[1, 10]` to `[0, 1]` preserves
the rank ordering but not the density. A percentile-aware rescaling would
require distributional calibration and is not implemented.
