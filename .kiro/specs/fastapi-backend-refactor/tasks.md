# Implementation Plan: FastAPI Backend Refactor

## Overview

Break the existing `main.py` monolith into a layered service architecture. The work proceeds in dependency order: constants → schemas → services → routes → main.py → tests → requirements. No prediction logic changes. Model files stay in `backend/fastapi/models/`.

All paths below are relative to the workspace root unless noted. Run `pytest` from `backend/fastapi/`.

---

## Tasks

- [x] 1. Create `app/config/constants.py` — shared constants module
  - Create the file `backend/fastapi/app/config/constants.py`
  - Define `TECHNICAL_FEATURES: list[str]` with the 4 technical feature names in canonical order: `Computer Architecture`, `Programming Skills`, `Project Management`, `Communication skills`
  - Define `PERSONALITY_FEATURES: list[str]` with the 10 personality feature names in canonical order matching `main.py`'s `other_features` list
  - Define `ROLE_MAPPING: dict[int, str]` with all 16 entries (indices 0–15) using the exact role name strings from the existing `main.py`
  - No classes, no runtime logic — pure module-level constants only
  - _Requirements: 3.1, 3.3, 3.4_

- [x] 2. Create `app/schemas/prediction.py` — Pydantic data models
  - Create the file `backend/fastapi/app/schemas/prediction.py`
  - Define `PredictionRequest(BaseModel)` with a `values: list[float]` field and a `@field_validator("values")` that raises `ValueError` if `len(v) != 14`, message: `"Expected exactly 14 values, got {len(v)}"`
  - Define `TopRole(BaseModel)` with `role: str` and `probability: float`
  - Define `PredictionResult(BaseModel)` with `predicted_role: str` and `top_3_roles: list[TopRole]`
  - Import from `pydantic` — no other runtime imports needed in this file
  - _Requirements: 2.7, 6.1, 6.3, 6.4, 6.5_

- [x] 3. Create `app/services/feature_mapper.py` — `FeatureMapper` class
  - Create the file `backend/fastapi/app/services/feature_mapper.py`
  - Define class `FeatureMapper` with `__init__(self, models_dir: str = "backend/fastapi/models/") -> None`
  - In `__init__`: load `scaler.pkl` and `pca.pkl` using `joblib.load` from `models_dir`; raise `FileNotFoundError` if either file is missing
  - Define `transform(self, values: list[float]) -> np.ndarray`
    - Raise `ValueError` if `len(values) != 14`
    - Build a `pd.DataFrame` with columns `TECHNICAL_FEATURES + PERSONALITY_FEATURES` (import from `app.config.constants`)
    - Apply `self.scaler.transform` to the 4 technical columns → shape `(1, 4)`
    - Apply `self.pca.transform` to the scaled result → shape `(1, 2)`
    - Concatenate the 10 personality columns (as numpy array) with the 2 PCA components → shape `(1, 12)`
    - Return the concatenated `np.ndarray`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 4. Create `app/services/predictor.py` — `PredictorService` class
  - Create the file `backend/fastapi/app/services/predictor.py`
  - Define class `PredictorService` with `__init__(self, models_dir: str = "backend/fastapi/models/") -> None`
  - In `__init__`: load `frf.pkl` using `joblib.load`; raise `FileNotFoundError` (with the attempted path in the message) if the file is missing
  - Define `predict(self, features: np.ndarray) -> PredictionResult`
    - Call `self.frf_model.predict(features)` to get the class index → look up `ROLE_MAPPING` for `predicted_role`
    - Call `self.frf_model.predict_proba(features)` to get probabilities over all 16 classes
    - Compute `top3_indices = np.argsort(proba[0])[-3:][::-1]`
    - Build `top_3_roles` as a list of 3 `TopRole` objects, each with `role=ROLE_MAPPING[idx]` and `probability=float(proba[0][idx])`
    - Return `PredictionResult(predicted_role=predicted_role, top_3_roles=top_3_roles)`
  - Import `ROLE_MAPPING` from `app.config.constants`; import `PredictionResult`, `TopRole` from `app.schemas.prediction`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.2_

- [x] 5. Create `app/services/model_registry.py` — `ModelRegistry` class
  - Create the file `backend/fastapi/app/services/model_registry.py`
  - Define class `ModelRegistry` with `__init__(self, models_dir: str = "backend/fastapi/models/", experiment_name: str | None = None) -> None`
  - In `__init__`: set `self.models_dir = models_dir`; set `self.experiment_name` to the parameter value or `os.environ.get("MLFLOW_EXPERIMENT_NAME", "career-prediction")` if `None`
  - Define `register_baseline_if_needed(self) -> None`:
    - Wrap the entire body in `try/except Exception` — on any exception, log a `WARNING` with the error message and return
    - Call `mlflow.set_experiment(self.experiment_name)`
    - Search for existing runs: `mlflow.search_runs(filter_string='tags.baseline = "true" AND tags.model_version = "frf_v1"')`
    - If matching runs exist: log INFO `"MLflow baseline run already registered, skipping."` and return
    - Otherwise: start a run with `mlflow.start_run(run_name="frf_baseline")`, log artifacts with `mlflow.log_artifacts(self.models_dir)`, set tags `{"baseline": "true", "model_version": "frf_v1"}`, end the run
  - Use Python's `logging` module (`import logging; logger = logging.getLogger(__name__)`)
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 6. Create `app/services/agent_orchestrator.py` — `AgentOrchestrator` stub
  - Create the file `backend/fastapi/app/services/agent_orchestrator.py`
  - Add a module-level docstring describing future responsibilities: coordinating resume parsing, RAG retrieval, and AI career advisor agent workflows
  - Define class `AgentOrchestrator` with `__init__(self) -> None: pass`
  - Define `run(self, *args, **kwargs)` that raises `NotImplementedError("AgentOrchestrator is not yet implemented.")`
  - No functional logic, no ML imports
  - _Requirements: 7.1, 7.2, 7.3_

- [x] 7. Create `app/routes/predict.py` — APIRouter
  - Create the file `backend/fastapi/app/routes/predict.py`
  - Define `router = APIRouter()`
  - Implement `GET /` handler returning `{"message": "Backend running"}`
  - Implement `POST /predict` handler with `response_model=PredictionResult`:
    - Accept `data: PredictionRequest` (Pydantic validates the 14-value constraint automatically → 422 on failure)
    - Retrieve `feature_mapper` and `predictor` from `request.app.state` (injected by lifespan in `main.py`)
    - Call `features = feature_mapper.transform(data.values)`
    - Call `result = predictor.predict(features)`
    - Return `result`
  - The route handler must accept `request: Request` as a parameter to access `app.state`
  - Do not instantiate services inside the router — use `app.state` only
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7_

- [x] 8. Rewrite `app/main.py` — routing-only application wiring
  - Overwrite `backend/fastapi/app/main.py` with the new implementation
  - Import: `asynccontextmanager` from `contextlib`; `FastAPI`, `Request` from `fastapi`; `CORSMiddleware` from `fastapi.middleware.cors`; `JSONResponse` from `fastapi.responses`; `router` from `app.routes.predict`; `ModelRegistry` from `app.services.model_registry`; `FeatureMapper` from `app.services.feature_mapper`; `PredictorService` from `app.services.predictor`
  - Define `@asynccontextmanager async def lifespan(app: FastAPI)`:
    - Startup: `app.state.feature_mapper = FeatureMapper()`, `app.state.predictor = PredictorService()`, `ModelRegistry().register_baseline_if_needed()`
    - `yield`
    - Shutdown: no-op (nothing to clean up)
  - Instantiate `app = FastAPI(lifespan=lifespan)`
  - Add `CORSMiddleware` with `allow_origins=["http://localhost:3000"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`
  - Register global exception handler for `Exception` returning `JSONResponse(status_code=500, content={"detail": "Internal prediction error"})`
  - Mount router: `app.include_router(router)` (no prefix)
  - The file must contain zero imports of `joblib`, `numpy`, `pandas`, or any ML model
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 9. Checkpoint — verify the app starts and the existing route works
  - Ensure all imports resolve: run `python -c "from app.main import app"` from `backend/fastapi/` and confirm no import errors
  - Verify `GET /` returns `{"message": "Backend running"}` and `POST /predict` accepts a 14-value payload

- [x] 10. Create `tests/conftest.py` — shared pytest fixtures
  - Create the file `backend/fastapi/tests/conftest.py`
  - Resolve paths using `pathlib`:
    - `TESTS_DIR = pathlib.Path(__file__).parent`
    - `REPO_ROOT = TESTS_DIR.parent.parent.parent.parent`
    - `MODELS_DIR = str(REPO_ROOT / "backend" / "fastapi" / "models")`
    - `DATA_PATH = str(REPO_ROOT / "data" / "CareerMapping1.csv")`
  - Define `@pytest.fixture(scope="session") def models_dir() -> str` returning `MODELS_DIR`
  - Define `@pytest.fixture(scope="session") def sample_rows(models_dir) -> pd.DataFrame` loading the first 10 rows from `DATA_PATH` via `pd.read_csv(DATA_PATH).head(10)`
  - Define `@pytest.fixture(scope="session") def feature_mapper(models_dir) -> FeatureMapper` returning `FeatureMapper(models_dir=models_dir)`
  - Define `@pytest.fixture(scope="session") def predictor_service(models_dir) -> PredictorService` returning `PredictorService(models_dir=models_dir)`
  - All fixtures use `scope="session"` so model files are loaded once per test run
  - _Requirements: 8.7, 8.8_

- [x] 11. Create `tests/test_feature_mapper.py` — FeatureMapper unit tests
  - Create the file `backend/fastapi/tests/test_feature_mapper.py`
  - Import `pytest`, `FeatureMapper` from `app.services.feature_mapper`, `TECHNICAL_FEATURES` and `PERSONALITY_FEATURES` from `app.config.constants`
  - `test_feature_mapper_smoke(models_dir)`: instantiate `FeatureMapper(models_dir=models_dir)` and assert it is not `None`
  - `test_feature_mapper_output_shape(feature_mapper, sample_rows)`: for each row in `sample_rows`, extract `TECHNICAL_FEATURES + PERSONALITY_FEATURES` columns as a list of floats, call `feature_mapper.transform(values)`, and assert `result.shape == (1, 12)`
  - `test_feature_mapper_rejects_wrong_length(feature_mapper)`: assert `pytest.raises(ValueError)` when calling `transform([0.5] * 13)`, and again with `[0.5] * 15`
  - _Requirements: 8.1, 8.2, 8.6_

- [x] 12. Create `tests/test_predictor_service.py` — PredictorService unit tests
  - Create the file `backend/fastapi/tests/test_predictor_service.py`
  - Import `pytest`, `PredictorService` from `app.services.predictor`, `ROLE_MAPPING`, `TECHNICAL_FEATURES`, `PERSONALITY_FEATURES` from `app.config.constants`
  - `test_predictor_service_smoke(models_dir)`: instantiate `PredictorService(models_dir=models_dir)` and assert it is not `None`
  - `test_predicted_role_is_valid(feature_mapper, predictor_service, sample_rows)`: transform `sample_rows.iloc[0]` via `feature_mapper`, call `predictor_service.predict(features)`, assert `result.predicted_role in ROLE_MAPPING.values()`
  - `test_top_3_roles_structure(feature_mapper, predictor_service, sample_rows)`: transform `sample_rows.iloc[0]`, call `predict`, assert `len(result.top_3_roles) == 3` and for each entry `0.0 <= entry.probability <= 1.0`
  - `test_predictor_service_bad_models_dir()`: assert `pytest.raises(FileNotFoundError)` when constructing `PredictorService(models_dir="/nonexistent/path")`
  - _Requirements: 8.3, 8.4, 8.5_

- [x] 13. Add HTTP-layer tests using `TestClient` to `tests/test_predictor_service.py`
  - Append to `backend/fastapi/tests/test_predictor_service.py` (or create a separate `tests/test_predict_route.py` if preferred)
  - Import `TestClient` from `starlette.testclient` and `app` from `app.main`
  - `test_predict_valid_input_returns_200()`: POST `{"values": [5, 7, 6, 8, 0.6, 0.7, 0.5, 0.8, 0.4, 0.6, 0.7, 0.3, 0.5, 0.6]}` to `/predict`; assert `status_code == 200`, `"predicted_role" in body`, `"top_3_roles" in body`, `len(body["top_3_roles"]) == 3`
  - `test_predict_wrong_length_returns_422()`: POST `{"values": [1.0, 2.0, 3.0]}` to `/predict`; assert `status_code == 422`
  - Use a module-level `client = TestClient(app)` so the ASGI lifespan runs once for the module
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 14. Update `backend/fastapi/requirements.txt` — add missing packages
  - Append the following pinned entries to `backend/fastapi/requirements.txt` (do not duplicate any existing entry):
    - `mlflow==2.15.1`
    - `pytest==8.3.2`
    - `scikit-learn==1.5.1`
    - `joblib==1.4.2`
    - `numpy==1.26.4`
    - `pandas==2.2.2`
  - Preserve all existing entries unchanged — do not remove or modify them
  - _Requirements: 9.1, 9.2, 9.3, 9.4_

- [x] 15. Final checkpoint — run the full test suite
  - Run `pytest tests/` from `backend/fastapi/` and confirm all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- No optional tasks: all sub-tasks are required as defined by the Phase 1 scope constraint
- The `AgentOrchestrator` (task 6) is a required stub — it is the extension seam for future phases but contains no logic now
- Model files (`frf.pkl`, `scaler.pkl`, `pca.pkl`) must not be moved from `backend/fastapi/models/` at any point
- No Hypothesis, no property-based tests — `pytest` only
- No resume parsing, RAG, PySpark, CI/CD, or frontend changes in this phase
- `tests/conftest.py` uses four `.parent` steps to reach the workspace root from `backend/fastapi/tests/`; verify this resolves correctly for your environment if the layout changes
