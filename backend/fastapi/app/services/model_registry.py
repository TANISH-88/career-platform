import logging
import os
import pathlib

logger = logging.getLogger(__name__)



def _resolve_tracking_uri(tracking_uri: str | None) -> str:
    """Resolve the MLflow tracking URI, falling back to repo-root sqlite."""
    if tracking_uri:
        return tracking_uri
    if "MLFLOW_TRACKING_URI" in os.environ:
        return os.environ["MLFLOW_TRACKING_URI"]
    # Walk up from this file to find the repo root.  Robust against any
    # number of parent directories (avoids hard-coded parents[N] index).
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        if (parent / ".git").exists() or (parent / "dvc.yaml").exists():
            return f"sqlite:///{parent.as_posix()}/mlflow.db"
    # Last resort: current working directory
    return f"sqlite:///{pathlib.Path.cwd().as_posix()}/mlflow.db"


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
        self.tracking_uri = _resolve_tracking_uri(tracking_uri)


    @property
    def is_enabled(self) -> bool:
        return os.environ.get("MLFLOW_ENABLED", "true").lower() not in ("false", "0", "no")


    def register_baseline_if_needed(self) -> None:
        if not self.is_enabled:
            logger.warning(
                "MLflow disabled (MLFLOW_ENABLED=false). Skipping baseline registration."
            )
            return

        try:
            import mlflow  # deferred: MLflow is optional at serve time

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
            logger.warning(
                f"MLflow baseline registration failed (non-fatal): {e}. "
                "Set MLFLOW_ENABLED=false to suppress this warning."
            )
