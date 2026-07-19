# Project Context

## Project Overview

This project is an AI-powered Career Prediction Platform.

The system predicts suitable technology careers using a trained Machine Learning model and will later include resume analysis, RAG, and an AI career advisor.

Current stack:

- FastAPI (Backend)
- Next.js (Frontend)
- Scikit-learn
- Python
- Pandas
- NumPy

---

## Current Project Structure

backend/
    fastapi/
        app/
        models/

my-app/

data/

ml-training/

docs/

infra/

---

## Machine Learning

The ML model is already trained.

Current model files are located in:

backend/fastapi/models/

These include:

- frf.pkl
- scaler.pkl
- pca.pkl

Do not retrain the model.

Do not modify prediction logic unless explicitly requested.

---

## Backend Goals

Refactor the backend into a clean architecture.

Preferred structure:

app/
    api/
    services/
    schemas/
    models/
    utils/
    config/

Business logic should live inside services.

Routes should stay lightweight.

---

## Frontend

Frontend is written in Next.js.

Existing API endpoints must remain compatible.

Do not break frontend integration.

---

## Future Roadmap

Future phases include:

- Resume Upload
- Resume Parsing
- Gemini API integration
- RAG
- Career Advisor Agent
- Docker
- MLflow
- CI/CD
- UML Documentation

These are NOT part of the current refactor.

---

## Coding Guidelines

- Keep code modular.
- Follow SOLID principles.
- Use type hints where appropriate.
- Preserve existing functionality.
- Avoid unnecessary dependencies.
- Do not change prediction accuracy.
