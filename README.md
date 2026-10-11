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
- **Backend**: Python 3.11 unit tests (`pytest`), dependency validation, `ruff` linting.
- **Frontend**: Next.js build (`npm ci && npm run build`).
- **Docker**: Container build, container startup, health check `GET /`, and prediction smoke test `POST /predict`.

## Input Scale

`POST /predict` expects all 14 feature values in UI scale `[1, 10]`.  
The serving layer converts them to training units (`technical: [0, 6]`, `personality: [0, 1]`) before passing to the model.  
See [`ml-training/MODEL_CARD.md`](ml-training/MODEL_CARD.md#input-units-serving-boundary) for the conversion formula and history.
