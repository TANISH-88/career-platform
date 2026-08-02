from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.predict import router
from app.routes.resume import resume_router
from app.services.feature_mapper import FeatureMapper
from app.services.model_registry import ModelRegistry
from app.services.predictor import PredictorService
from app.services.resume_parser import ResumeParser


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load models and register MLflow baseline
    app.state.feature_mapper = FeatureMapper()
    app.state.predictor = PredictorService()
    app.state.resume_parser = ResumeParser()
    ModelRegistry().register_baseline_if_needed()
    yield
    # Shutdown: nothing to clean up in Phase 1


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


app.include_router(router)
app.include_router(resume_router)
