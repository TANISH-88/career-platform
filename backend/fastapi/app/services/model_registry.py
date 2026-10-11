import logging
import os
import pathlib

import mlflow

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(
        self,
        models_dir: str = "models/",
        experiment_name: str | None = None,
        tracking_uri: str | None = None,
    ) -> None:
        self.models_dir = models_dir
        self.experiment_name = experiment_name or os.environ.get(
            "MLFLOW_EXPERIMENT_NAME", "career-prediction"
        )
        if tracking_uri:
            self.tracking_uri = tracking_uri
        elif "MLFLOW_TRACKING_URI" in os.environ:
            self.tracking_uri = os.environ["MLFLOW_TRACKING_URI"]
        else:
            repo_root = pathlib.Path(__file__).resolve().parents[4]
            self.tracking_uri = f"sqlite:///{repo_root.as_posix()}/mlflow.db"


    def register_baseline_if_needed(self) -> None:
        try:
            mlflow.set_tracking_uri(self.tracking_uri)
            mlflow.set_experiment(self.experiment_name)
            runs = mlflow.search_runs(
                filter_string='tags.baseline = "true" AND tags.model_version = "frf_v1"'
            )
            if not runs.empty:
                logger.info("MLflow baseline run already registered, skipping.")
                return
            with mlflow.start_run(run_name="frf_baseline"):
                mlflow.log_artifacts(self.models_dir)
                mlflow.set_tags({"baseline": "true", "model_version": "frf_v1"})
            logger.info("MLflow baseline run registered successfully.")
        except Exception as e:
            logger.warning(f"MLflow baseline registration failed (non-fatal): {e}")
