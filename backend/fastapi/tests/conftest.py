import logging
import os
import pathlib
import pandas as pd
import pytest

from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService

os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")

TESTS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent.parent  # tests/ → fastapi/ → backend/ → workspace root
MODELS_DIR = str(REPO_ROOT / "backend" / "fastapi" / "models")
DATA_PATH = str(TESTS_DIR / "fixtures" / "sample_careers.csv")



@pytest.fixture(scope="session")
def models_dir() -> str:
    return MODELS_DIR


@pytest.fixture(scope="session")
def sample_rows() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH).head(10)


@pytest.fixture(scope="session")
def feature_mapper(models_dir) -> FeatureMapper:
    return FeatureMapper(models_dir=models_dir)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "allow_clamping: opt-out marker for tests that exercise out-of-bounds input clamping on purpose",
    )


class ClampingLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.clamped_warnings = []

    def emit(self, record):
        if "clamped" in record.getMessage().lower():
            self.clamped_warnings.append(record)


@pytest.fixture(autouse=True)
def fail_on_clamping_warning(request):
    handler = ClampingLogHandler()
    logger = logging.getLogger("app.services.feature_mapper")
    logger.addHandler(handler)
    try:
        yield
    finally:
        logger.removeHandler(handler)

    if request.node.get_closest_marker("allow_clamping"):
        return
    if handler.clamped_warnings:
        messages = "\n".join(f"- {r.levelname}: {r.getMessage()}" for r in handler.clamped_warnings)
        pytest.fail(
            f"Test triggered clamping warning unexpectedly:\n{messages}\n"
            f"If this test is intended to exercise clamping, decorate it with @pytest.mark.allow_clamping"
        )


@pytest.fixture(scope="session")
def predictor_service(models_dir) -> PredictorService:
    return PredictorService(models_dir=models_dir)
