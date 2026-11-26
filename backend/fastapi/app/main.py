import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config.settings import get_cors_allowed_origins, validate_startup_settings
from app.db.engine import create_db_engine
from app.db.session import create_session_factory
from app.routes.auth import auth_router
from app.routes.predict import router
from app.routes.resume import resume_router
from app.routes.workspaces import workspaces_router
from app.services.feature_mapper import FeatureMapper
from app.services.model_registry import ModelRegistry
from app.services.predictor import PredictorService
from app.services.rate_limiter import InMemoryRateLimiter
from app.services.resume_parser import ResumeParser

# Resolve models directory relative to this file so the app works regardless
# of the working directory (e.g. when tests run from the repo root).
_HERE = pathlib.Path(__file__).resolve().parent
_MODELS_DIR = str(_HERE.parent / "models")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_startup_settings()
    engine = create_db_engine()
    app.state.db_engine = engine
    app.state.db_session_factory = create_session_factory(engine)
    app.state.auth_rate_limiter = InMemoryRateLimiter()
    app.state.login_email_rate_limiter = InMemoryRateLimiter()
    app.state.resume_rate_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60)
    app.state.feature_mapper = FeatureMapper(models_dir=_MODELS_DIR)
    app.state.predictor = PredictorService(models_dir=_MODELS_DIR)
    app.state.resume_parser = ResumeParser()
    app.state.model_version = "frf_v1"
    ModelRegistry(models_dir=_MODELS_DIR).register_baseline_if_needed()
    yield
    engine.dispose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal prediction error"},
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Request validation failed"})


app.include_router(router)
app.include_router(resume_router)
app.include_router(auth_router)
app.include_router(workspaces_router)
