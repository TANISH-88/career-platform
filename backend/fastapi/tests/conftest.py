import pathlib
import pandas as pd
import pytest

from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService

TESTS_DIR = pathlib.Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent.parent.parent  # tests/ → fastapi/ → backend/ → workspace root
MODELS_DIR = str(REPO_ROOT / "backend" / "fastapi" / "models")
DATA_PATH = str(REPO_ROOT / "data" / "CareerMapping1.csv")


@pytest.fixture(scope="session")
def models_dir() -> str:
    return MODELS_DIR


@pytest.fixture(scope="session")
def sample_rows() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH).head(10)


@pytest.fixture(scope="session")
def feature_mapper(models_dir) -> FeatureMapper:
    return FeatureMapper(models_dir=models_dir)


@pytest.fixture(scope="session")
def predictor_service(models_dir) -> PredictorService:
    return PredictorService(models_dir=models_dir)
