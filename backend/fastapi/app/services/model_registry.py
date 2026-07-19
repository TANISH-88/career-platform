import logging
import os

import mlflow

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(
        self,
        models_dir: str = "models/",
        experiment_name: str | None = None,
    ) -> None:
        self.models_dir = models_dir
        self.experiment_name = experiment_name or os.environ.get(
            "MLFLOW_EXPERIMENT_NAME", "career-prediction"
        )

    def register_baseline_if_needed(self) -> None:
        try:
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
