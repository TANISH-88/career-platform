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

## Backend Database, Migrations & Environment Setup

### Database & Alembic Migrations

The FastAPI backend uses SQLAlchemy 2.x + Alembic (`backend/fastapi/alembic/`). By default in local development it uses SQLite (`sqlite:///./app.db`), and supports PostgreSQL in production via `DATABASE_URL` (with SQLite `PRAGMA foreign_keys=ON` enforced automatically).

```bash
cd backend/fastapi
alembic upgrade head
```

### Environment Variables

**Backend (`backend/.env` or process environment):**
- `GEMINI_API_KEY` *(required on startup)* — Gemini API key for resume skill extraction (fail-closed if missing).
- `JWT_SECRET` *(required in `production`)* — HMAC signing secret for JWT access tokens (an ephemeral per-process secret is generated in non-production if unset).
- `ENVIRONMENT` — `development`, `production`, or `test` (fail-closed if unset when `DATABASE_URL` is non-SQLite).
- `DATABASE_URL` — SQLAlchemy database URL (default: `sqlite:///./app.db`).
- `GOOGLE_CLIENT_ID` — Google OAuth 2.0 Web Client ID for verifying Google ID tokens (`POST /auth/google`, `POST /auth/google/link`).
- `CORS_ALLOWED_ORIGINS` — Comma-separated allowed origins (default: `http://localhost:3000`).
- `COOKIE_SECURE` / `COOKIE_SAMESITE_NONE` — Refresh cookie security flags (`COOKIE_SECURE` is forced `true` in `production`).
- `MLFLOW_ENABLED` — Set `false` locally to skip MLflow baseline registration on startup.

**Frontend (`my-app/.env.local`):**
- `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — Google OAuth Web Client ID (enables the Google Sign-In button on `/login` and `/register`).
- `BACKEND_URL` — Origin used by the Next.js `/api/*` same-origin proxy (default: `http://127.0.0.1:8000`).
