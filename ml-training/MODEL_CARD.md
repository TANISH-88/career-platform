# Model Card — Career Prediction Random Forest (career-rf)

## Data

| Property | Value |
|---|---|
| Source file | `data/CareerMapping1.csv` |
| MD5 (at training time) | `7192e48953b32a0448b020198591567b` |
| Total rows | 10,179 |
| Roles (classes) | 16 |
| Train rows (80%) | 8,143 |
| Test rows (20%) | 2,036 |

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

## Evaluation on Held-Out Test Set (seed 42 stratified split, 2,036 rows)

| Metric | Value |
|---|---|
| Top-1 accuracy | **0.906** |
| 5-seed ablation mean | 0.907 ± 0.008 |

### 5-Seed Ablation Summary (train-only preprocessing, stratified split)

| Seeds | Per-seed accuracy | Mean | Std |
|---|---|---|---|
| 42, 123, 456, 789, 2024 | 0.906, 0.924, 0.899, 0.902, 0.909 | 0.908 | 0.009 |

The ablation also compared fitting scaler/PCA on all data (leakage) vs. train only.
Mean difference between conditions: < 0.002 — within one standard deviation of seed
noise. **Leakage is not a detectable effect on this dataset.**

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
