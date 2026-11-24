# Career Platform

[![CI](https://github.com/TANISH-88/career-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/TANISH-88/career-platform/actions/workflows/ci.yml)

An ML-powered career prediction platform featuring automated model training, experiment tracking with MLflow, dataset versioning with DVC, FastAPI serving, and a Next.js frontend.

## Architecture

- **`backend/fastapi/`**: Serving API (FastAPI, scikit-learn 1.7.1, Gemini resume parser).
- **`ml-training/`**: Model training pipeline (`train.py`), candidate promotion (`promote.py`), parity verification (`check_parity.py`).
- **`my-app/`**: Next.js React frontend.
- **`infra/docker/`**: Container definitions for reproducible deployment.

## CI / Testing

Continuous integration runs on every push and pull request via GitHub Actions:
- **Backend**: Python 3.11 unit tests (`pytest`), dependency validation, `ruff` linting, parity gate (`check_parity.py`), extra-row exclusion test.
- **Frontend**: Next.js build (`npm ci && npm run build`).
- **Docker**: Container build, container startup, health check `GET /`, and prediction smoke test `POST /predict`.

## Data Notes

The training dataset (`CareerMapping1.csv`) contains 10,179 rows, of which **1,000 rows at indices 9,179–10,178 are excluded from training and evaluation by default** because their origin cannot be established (fractional technical features outside the raw dataset's range; no generation script found). The raw dataset file is preserved unmodified. See [`ml-training/MODEL_CARD.md`](ml-training/MODEL_CARD.md#unknown-origin-extra-rows) for details.

> **Accuracy note:** Random-split accuracy (~0.902) reflects test rows that largely overlap with training personality profiles. Grouped (unseen-persona) accuracy is ~0.188. See MODEL_CARD.md for the full evaluation breakdown.

## M3 honest evaluation (review branch)

Train a development-only champion, optionally register it and the historical model,
then compare a candidate against the same frozen personas:

```bash
python ml-training/train.py bootstrap --register
python ml-training/train.py candidate
```

The holdout is 44 of 218 personas; no overlap with development. New scores appear
in `ml-training/m3-output/champion/report.json` and `candidate/report.json`.
CI #66 measured champion holdout accuracy **19.73%**, macro-F1 **16.64%**; the identical candidate was rejected (gain 0). Historical random-split accuracy is not generalization. The data is consistent
with a templated source and lacks external validation. Eligibility requires
a 2 percentage-point gain, positive paired-bootstrap lower bound and serving parity.
Promotion is disabled until M4; existing serving model files are untouched.

### Candidate-only GitHub Actions workflow

[M3 candidate training](https://github.com/TANISH-88/career-platform/actions/workflows/m3-candidate.yml)
runs on matching pushes and supports manual dispatch after the workflow is on the default branch. The default CLI (python ml-training/train.py) runs candidate-only; use a fresh output directory.
The champion reference is pinned by SHA256 and contains frozen row-aligned predictions from a one-time reproduction
of verified commit 5557227 (run 45487237769), not a retrained champion per candidate.
The original cleaned CSV and holdout remain frozen. Reviewed development-only additions use data/development/addendum_v1.json; validation rejects overlaps and duplicates. The gate uses eleven matched seeds and an equal-persona bootstrap plus macro-F1 non-regression. Changing the evaluation dataset requires a separately reviewed evaluation version.
Candidate rejection is a successful workflow outcome; validation or training crashes fail
the job. Candidate artifacts and report are retained for 14 days. No registry write,
approval email, promotion or deployment.

## Input Scale

`POST /predict` expects all 14 feature values in UI scale `[1, 10]`.  
The serving layer converts them to training units (`technical: [0, 6]`, `personality: [0, 1]`) before passing to the model.  
See [`ml-training/MODEL_CARD.md`](ml-training/MODEL_CARD.md#input-units-serving-boundary) for the conversion formula and history.
