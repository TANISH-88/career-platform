# Requirements Document

## Introduction

This document defines the requirements for refactoring the FastAPI backend of the AI-powered Career Prediction Platform from a single-file monolith (`main.py`) into a clean service-oriented architecture, while adding MLflow experiment tracking as a baseline for future retraining comparisons.

The refactor must preserve the external API contract so the existing Next.js frontend continues to work without modification. It must not change prediction logic or model accuracy. The new architecture must leave clean extension seams for upcoming phases: resume parsing, RAG, and an AI agent orchestrator.

All trained model files (`frf.pkl`, `scaler.pkl`, `pca.pkl`) remain in `backend/fastapi/models/` and must not be moved.

---

## Glossary

- **API**: Application Programming Interface — the HTTP interface exposed by the FastAPI backend.
- **FeatureMapper**: The service responsible for accepting 14 raw input values and returning 12 model-ready features via scaling and PCA transformation.
- **Predictor_Service**: The service that owns the loaded ML models and exposes a `predict` method returning a `PredictionResult`.
- **PredictionResult**: A structured result containing the top predicted role and the top-3 roles with their associated probabilities.
- **Model_Registry**: The service that wraps model loading with MLflow tracking, logging the current model artifacts as a baseline run on startup if one has not already been registered.
- **Role_Mapping**: The static index-to-role-name dictionary mapping integer class indices (0–15) to human-readable career role names.
- **Router**: A FastAPI `APIRouter` instance that groups related route handlers.
- **Agent_Orchestrator**: A future service (stubbed in this phase) that will coordinate AI agent workflows including resume parsing, RAG, and career advice.
- **CareerMapping1.csv**: The dataset file located at `data/CareerMapping1.csv` used as fixture data for tests. It contains 14 input feature columns and a `Role` label column.
- **Backward-Compatible**: A change that adds new fields to a response without removing or renaming existing fields, so existing consumers continue to work.
- **MLflow**: An open-source ML lifecycle management platform used here to log model artifacts and runs.

---

## Requirements

### Requirement 1: Extract Feature Transformation into FeatureMapper

**User Story:** As a backend developer, I want feature scaling and PCA transformation isolated in a dedicated class, so that the resume-parsing phase can reuse the same transformation pipeline without duplicating code.

#### Acceptance Criteria

1. THE `FeatureMapper` SHALL accept exactly 14 raw float values ordered as: `Computer Architecture`, `Programming Skills`, `Project Management`, `Communication skills`, `Openness`, `Conscientiousness`, `Extraversion`, `Agreeableness`, `Emotional_Range`, `Conversation`, `Openness to Change`, `Hedonism`, `Self-enhancement`, `Self-transcendence`.
2. THE `FeatureMapper` SHALL apply `scaler.transform` to the first 4 technical features and then apply `pca.transform` to produce 2 PCA components.
3. THE `FeatureMapper` SHALL return a NumPy array of shape `(1, 12)` representing the 10 personality features concatenated with the 2 PCA components.
4. THE `FeatureMapper` SHALL be implemented as the class `FeatureMapper` in `backend/fastapi/app/services/feature_mapper.py`.
5. IF the input list does not contain exactly 14 numeric values, THEN THE `FeatureMapper` SHALL raise a `ValueError` with a descriptive message.
6. THE `FeatureMapper` SHALL load `scaler.pkl` and `pca.pkl` from `backend/fastapi/models/` (the canonical path where these files currently reside and must remain); the constructor SHALL accept an optional `models_dir` parameter so tests can override the path without moving or renaming the files.

---

### Requirement 2: Extract Model Inference into PredictorService

**User Story:** As a backend developer, I want model inference encapsulated in a `PredictorService`, so that the prediction logic is testable in isolation and the top-3 role probabilities are available for future UI phases without a breaking change.

#### Acceptance Criteria

1. THE `Predictor_Service` SHALL load `frf.pkl` from `backend/fastapi/models/` (the canonical path where this file currently resides and must remain); the constructor SHALL accept an optional `models_dir` parameter so tests can override the path without moving or renaming the file.
2. WHEN `Predictor_Service.predict` is called with a NumPy array of shape `(1, 12)`, THE `Predictor_Service` SHALL return a `PredictionResult` containing `predicted_role` (a string) and `top_3_roles` (a list of exactly 3 objects, each containing `role` and `probability`).
3. THE `Predictor_Service` SHALL derive `predicted_role` using `frf_model.predict` and resolve the role name via `Role_Mapping`.
4. THE `Predictor_Service` SHALL derive `top_3_roles` using `frf_model.predict_proba`, selecting the 3 class indices with the highest probabilities and resolving their names via `Role_Mapping`.
5. THE `Predictor_Service` SHALL be implemented as the class `PredictorService` in `backend/fastapi/app/services/predictor.py`.
6. IF `frf.pkl` cannot be loaded from the configured path, THEN THE `Predictor_Service` SHALL raise a `FileNotFoundError` with the attempted path in the message.
7. THE `PredictionResult` SHALL be a `dataclass` or `Pydantic` model defined in `backend/fastapi/app/schemas/`.

---

### Requirement 3: Move Role Mapping into a Config/Constants Module

**User Story:** As a backend developer, I want the role index-to-name mapping defined in one place, so that both `PredictorService` and future services (e.g., resume parsing) share a single source of truth without duplication.

#### Acceptance Criteria

1. THE `Role_Mapping` dictionary (16 entries, indices 0–15) SHALL be defined as a module-level constant in `backend/fastapi/app/config/constants.py`.
2. THE `Predictor_Service` SHALL import `Role_Mapping` from `backend/fastapi/app/config/constants.py` and SHALL NOT define its own inline mapping.
3. THE `Role_Mapping` SHALL map integer indices to the exact role name strings currently used in production: `Database Administrator`, `Hardware Engineer`, `Application Support Engineer`, `Cyber Security Specialist`, `Networking Engineer`, `Software Developer`, `API Specialist`, `Project Manager`, `Information Security Specialist`, `Technical Writer`, `AI ML Specialist`, `Software Tester`, `Business Analyst`, `Customer Service Executive`, `Helpdesk Engineer`, `Graphics Designer`.
4. THE `constants.py` module SHALL also define `TECHNICAL_FEATURES` (list of 4 feature name strings) and `PERSONALITY_FEATURES` (list of 10 feature name strings) so all feature-name definitions are co-located with `Role_Mapping`.

---

### Requirement 4: Add MLflow Model Registry Baseline Logging

**User Story:** As an ML engineer, I want the current model artifacts logged to MLflow on startup, so that future retraining runs have a baseline experiment to compare against.

#### Acceptance Criteria

1. THE `Model_Registry` SHALL be implemented as the class `ModelRegistry` in `backend/fastapi/app/services/model_registry.py`.
2. WHEN the FastAPI application starts, THE `Model_Registry` SHALL check whether an MLflow run tagged with `baseline=true` and `model_version=frf_v1` already exists in the configured experiment.
3. IF no such run exists, THEN THE `Model_Registry` SHALL log `frf.pkl`, `scaler.pkl`, and `pca.pkl` — sourced from `backend/fastapi/models/` (the canonical path where these files currently reside and must remain) — as MLflow artifacts under a new run named `frf_baseline`, with tags `baseline=true` and `model_version=frf_v1`.
4. IF a baseline run already exists, THEN THE `Model_Registry` SHALL skip logging and emit a log message at INFO level: `"MLflow baseline run already registered, skipping."`.
5. THE `Model_Registry` SHALL use the MLflow experiment name configured via the environment variable `MLFLOW_EXPERIMENT_NAME`, defaulting to `"career-prediction"` if the variable is not set.
6. IF MLflow is unavailable or raises an exception during startup logging, THEN THE `Model_Registry` SHALL log the error at WARNING level and allow the application to start normally without crashing.
7. THE `Model_Registry` SHALL accept a `models_dir` parameter in its constructor defaulting to `backend/fastapi/models/`, allowing path override in tests without moving or renaming the model files.

---

### Requirement 5: Refactor main.py to Routing-Only

**User Story:** As a backend developer, I want `main.py` to contain only application wiring (app creation, middleware, router registration), so that ML logic does not leak into the application entry point.

#### Acceptance Criteria

1. THE `main.py` SHALL create the FastAPI application instance, register CORS middleware, and mount routers.
2. THE `main.py` SHALL NOT import `joblib`, `numpy`, `pandas`, or any ML model directly.
3. THE `main.py` SHALL register a router from `backend/fastapi/app/routes/predict.py` under the prefix `""` (no prefix), preserving the existing `/predict` path.
4. WHEN the FastAPI application starts up, THE `main.py` SHALL invoke `ModelRegistry` startup logic via a FastAPI `lifespan` context manager or `startup` event handler.
5. THE `main.py` SHALL preserve CORS configuration allowing `http://localhost:3000` as an allowed origin.

---

### Requirement 6: Implement Predict Router

**User Story:** As a backend developer, I want the `/predict` endpoint defined in a dedicated router module, so that routing concerns are separated from business logic.

#### Acceptance Criteria

1. THE Router in `backend/fastapi/app/routes/predict.py` SHALL expose `POST /predict` accepting a request body with a `values` field containing a list of 14 numbers.
2. WHEN `POST /predict` is called with a valid 14-value list, THE Router SHALL delegate feature transformation to `FeatureMapper` and inference to `Predictor_Service`, then return a JSON response.
3. THE Router response for `POST /predict` SHALL include `predicted_role` (string) as a top-level key, preserving backward compatibility with the existing frontend.
4. THE Router response for `POST /predict` SHALL additionally include `top_3_roles` (list of 3 objects with `role` and `probability` keys) as an additive, non-breaking field.
5. IF the `values` list does not contain exactly 14 items, THEN THE Router SHALL return HTTP 422 with a descriptive validation error message.
6. IF an unexpected error occurs during prediction, THEN THE Router SHALL return HTTP 500 with a JSON body containing `"detail": "Internal prediction error"`.
7. THE Router SHALL expose `GET /` returning `{"message": "Backend running"}` for health-check compatibility.

---

### Requirement 7: Add Agent Orchestrator Stub

**User Story:** As a backend developer, I want a placeholder `AgentOrchestrator` module in place now, so that the resume-parsing and RAG phases can slot in without requiring another structural reorganization.

#### Acceptance Criteria

1. THE file `backend/fastapi/app/services/agent_orchestrator.py` SHALL exist with a module-level docstring describing its future responsibilities: coordinating resume parsing, RAG retrieval, and AI career advisor agent workflows.
2. THE `agent_orchestrator.py` file SHALL define an empty class `AgentOrchestrator` with a `__init__` method and a stub method `run` that raises `NotImplementedError` with the message `"AgentOrchestrator is not yet implemented."`.
3. THE `AgentOrchestrator` class SHALL NOT contain any functional ML or API logic in this phase.

---

### Requirement 8: Add Tests for FeatureMapper and PredictorService

**User Story:** As a backend developer, I want automated tests for the two core service classes using real fixture data, so that regressions in the feature pipeline and prediction logic are caught before deployment.

#### Acceptance Criteria

1. THE test suite SHALL include a test file at `backend/fastapi/tests/test_feature_mapper.py` that loads rows from `data/CareerMapping1.csv` as fixture data.
2. WHEN `FeatureMapper.transform` is called with a valid row from `CareerMapping1.csv`, THE test SHALL assert that the output shape is `(1, 12)`.
3. THE test suite SHALL include a test file at `backend/fastapi/tests/test_predictor_service.py` that uses `FeatureMapper` output as input to `PredictorService.predict`.
4. WHEN `PredictorService.predict` is called with a mapped row from `CareerMapping1.csv`, THE test SHALL assert that `predicted_role` is one of the 16 valid role name strings defined in `Role_Mapping`.
5. WHEN `PredictorService.predict` is called with a mapped row from `CareerMapping1.csv`, THE test SHALL assert that `top_3_roles` contains exactly 3 entries and that each entry's `probability` is a float between 0.0 and 1.0 inclusive.
6. THE test suite SHALL include a test asserting that `FeatureMapper` raises `ValueError` when called with a list of fewer or more than 14 values.
7. THE tests SHALL be runnable with `pytest` from `backend/fastapi/` without requiring a running server or external services.
8. THE tests SHALL use a relative path to resolve model files and fixture data, so they are not environment-specific.

---

### Requirement 9: Update Requirements File

**User Story:** As a backend developer, I want `requirements.txt` updated to declare the new dependencies, so that any engineer can reproduce the environment with a single install command.

#### Acceptance Criteria

1. THE `backend/fastapi/requirements.txt` SHALL add `mlflow` pinned to a specific version compatible with Python 3.10+ and the existing scikit-learn version. This entry does not currently exist and must be added.
2. THE `backend/fastapi/requirements.txt` SHALL add `pytest` pinned to a specific version. This entry does not currently exist and must be added.
3. THE `backend/fastapi/requirements.txt` SHALL add `scikit-learn`, `joblib`, `numpy`, and `pandas` as explicit pinned entries, since these packages are not present in the existing file and are required by `FeatureMapper` and `Predictor_Service`.
4. THE `backend/fastapi/requirements.txt` SHALL preserve all existing entries without modification. The following packages are already present and MUST NOT be duplicated: `fastapi`, `uvicorn`, `starlette`, `pydantic`, `pydantic-core`, `annotated-types`, `typing_extensions`, `anyio`, `sniffio`, `idna`, `aiofiles`, `python-multipart`, `python-jose`, `passlib`, `bcrypt`, `ecdsa`, `rsa`, `pyasn1`, `SQLAlchemy`, `python-dotenv`, `click`, `six`.
