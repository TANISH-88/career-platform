from datetime import datetime, timezone
import threading

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config.constants import MAX_RESUME_VERSIONS_PER_WORKSPACE
from app.db.models import Prediction, ResumeVersion, SkillProfile, Workspace
from app.schemas.prediction import TopRole
from app.schemas.workspace import (
    PredictionHistoryItem,
    ResumeVersionResponse,
    WorkspacePredictionResponse,
)
from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace does not exist or is not owned by the caller."""


class ResumeVersionNotFoundError(Exception):
    """Raised when a resume version does not exist or does not belong to the caller's workspace."""


class ResumeVersionLimitError(Exception):
    """Raised when a workspace reaches MAX_RESUME_VERSIONS_PER_WORKSPACE."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_workspace_resume_locks_guard = threading.Lock()
_workspace_resume_locks: dict[str, threading.Lock] = {}


def _get_workspace_resume_lock(workspace_id: str) -> threading.Lock:
    with _workspace_resume_locks_guard:
        lock = _workspace_resume_locks.get(workspace_id)
        if lock is None:
            lock = threading.Lock()
            _workspace_resume_locks[workspace_id] = lock
        return lock


def create_workspace(db: Session, user_id: str, name: str) -> Workspace:
    now = _utcnow()
    workspace = Workspace(user_id=user_id, name=name, last_opened_at=now)
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


def list_workspaces(
    db: Session,
    user_id: str,
    include_archived: bool = False,
) -> list[Workspace]:
    stmt = select(Workspace).where(Workspace.user_id == user_id)
    if not include_archived:
        stmt = stmt.where(Workspace.archived_at.is_(None))
    stmt = stmt.order_by(Workspace.updated_at.desc())
    return list(db.scalars(stmt).all())


def get_workspace_for_user(
    db: Session,
    workspace_id: str,
    user_id: str,
    mark_opened: bool = False,
) -> Workspace:
    workspace = db.scalar(
        select(Workspace).where(Workspace.id == workspace_id, Workspace.user_id == user_id)
    )
    if workspace is None:
        raise WorkspaceNotFoundError("Workspace not found")
    if mark_opened:
        workspace.last_opened_at = _utcnow()
        db.commit()
        db.refresh(workspace)
    return workspace


def get_last_active_workspace(db: Session, user_id: str) -> Workspace:
    workspace = db.scalar(
        select(Workspace)
        .where(
            Workspace.user_id == user_id,
            Workspace.archived_at.is_(None),
            Workspace.last_opened_at.is_not(None),
        )
        .order_by(Workspace.last_opened_at.desc(), Workspace.created_at.desc())
    )
    if workspace is None:
        raise WorkspaceNotFoundError("No active workspace found")
    return workspace


def archive_workspace(db: Session, workspace_id: str, user_id: str) -> Workspace:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    if workspace.archived_at is None:
        workspace.archived_at = _utcnow()
        db.commit()
        db.refresh(workspace)
    return workspace


def unarchive_workspace(db: Session, workspace_id: str, user_id: str) -> Workspace:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    if workspace.archived_at is not None:
        workspace.archived_at = None
        db.commit()
        db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace_id: str, user_id: str) -> None:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    db.delete(workspace)
    db.commit()


def predict_in_workspace(
    db: Session,
    workspace_id: str,
    user_id: str,
    values: list[float],
    feature_mapper: FeatureMapper,
    predictor: PredictorService,
    model_version: str,
) -> WorkspacePredictionResponse:
    workspace = get_workspace_for_user(db, workspace_id, user_id)

    features = feature_mapper.transform(values)
    result = predictor.predict(features)

    skill_profile = SkillProfile(workspace_id=workspace.id, values=list(values))
    db.add(skill_profile)
    db.flush()

    now = _utcnow()
    top_k_payload = [role.model_dump() for role in result.top_3_roles]
    prediction = Prediction(
        workspace_id=workspace.id,
        skill_profile_id=skill_profile.id,
        predicted_role=result.predicted_role,
        top_k=top_k_payload,
        model_version=model_version,
    )
    db.add(prediction)
    workspace.updated_at = now
    workspace.last_opened_at = now
    db.commit()
    db.refresh(prediction)

    return WorkspacePredictionResponse(
        predicted_role=result.predicted_role,
        top_3_roles=result.top_3_roles,
        prediction_id=prediction.id,
        skill_profile_id=skill_profile.id,
        model_version=prediction.model_version,
        created_at=prediction.created_at,
    )


def get_workspace_history(
    db: Session,
    workspace_id: str,
    user_id: str,
) -> list[PredictionHistoryItem]:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    stmt = (
        select(Prediction, SkillProfile)
        .join(SkillProfile, Prediction.skill_profile_id == SkillProfile.id)
        .where(Prediction.workspace_id == workspace.id)
        .order_by(Prediction.created_at.desc())
    )
    rows = db.execute(stmt).all()
    return [
        PredictionHistoryItem(
            id=prediction.id,
            skill_profile_id=skill_profile.id,
            values=skill_profile.values,
            predicted_role=prediction.predicted_role,
            top_k=[TopRole(**item) for item in prediction.top_k],
            model_version=prediction.model_version,
            created_at=prediction.created_at,
        )
        for prediction, skill_profile in rows
    ]


def ensure_resume_version_capacity(db: Session, workspace_id: str, user_id: str) -> Workspace:
    """Verify caller owns the workspace and has fewer than MAX_RESUME_VERSIONS_PER_WORKSPACE."""
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    existing_count = db.scalar(
        select(func.count()).select_from(ResumeVersion).where(ResumeVersion.workspace_id == workspace.id)
    ) or 0
    if existing_count >= MAX_RESUME_VERSIONS_PER_WORKSPACE:
        raise ResumeVersionLimitError(
            f"Resume version limit reached (max {MAX_RESUME_VERSIONS_PER_WORKSPACE} per workspace). "
            "Delete an existing version before uploading another."
        )
    return workspace


def create_workspace_resume_version(
    db: Session,
    workspace_id: str,
    user_id: str,
    parsed_skills: list[float],
    feature_mapper: FeatureMapper,
    predictor: PredictorService,
    model_version: str,
    parser_model: str,
) -> ResumeVersionResponse:
    """Persist derived-only LLM skill scores and ML prediction for a workspace resume upload.

    Never accepts or stores raw file bytes, filenames, or extracted plaintext.
    Serializes per-workspace writes so concurrent uploads cannot exceed MAX_RESUME_VERSIONS_PER_WORKSPACE.
    """
    features = feature_mapper.transform(parsed_skills)
    result = predictor.predict(features)
    top_k_payload = [role.model_dump() for role in result.top_3_roles]

    lock = _get_workspace_resume_lock(workspace_id)
    with lock:
        workspace = db.scalar(
            select(Workspace)
            .where(Workspace.id == workspace_id, Workspace.user_id == user_id)
            .with_for_update()
        )
        if workspace is None:
            raise WorkspaceNotFoundError("Workspace not found")

        existing_count = db.scalar(
            select(func.count())
            .select_from(ResumeVersion)
            .where(ResumeVersion.workspace_id == workspace.id)
        ) or 0
        if existing_count >= MAX_RESUME_VERSIONS_PER_WORKSPACE:
            raise ResumeVersionLimitError(
                f"Resume version limit reached (max {MAX_RESUME_VERSIONS_PER_WORKSPACE} per workspace). "
                "Delete an existing version before uploading another."
            )

        max_ver = db.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.workspace_id == workspace.id
            )
        ) or 0

        now = _utcnow()
        version = ResumeVersion(
            workspace_id=workspace.id,
            version_number=int(max_ver) + 1,
            parsed_skills=[float(v) for v in parsed_skills],
            predicted_role=result.predicted_role,
            top_k=top_k_payload,
            model_version=model_version,
            parser_model=parser_model,
        )
        db.add(version)
        workspace.updated_at = now
        workspace.last_opened_at = now
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ResumeVersionLimitError(
                "Concurrent resume upload conflict; please retry."
            ) from exc
        db.refresh(version)

    return ResumeVersionResponse(
        id=version.id,
        workspace_id=version.workspace_id,
        version_number=version.version_number,
        parsed_skills=version.parsed_skills,
        predicted_role=version.predicted_role,
        top_k=[TopRole(**item) for item in version.top_k],
        model_version=version.model_version,
        parser_model=version.parser_model,
        created_at=version.created_at,
    )


def list_workspace_resume_versions(
    db: Session,
    workspace_id: str,
    user_id: str,
) -> list[ResumeVersionResponse]:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    stmt = (
        select(ResumeVersion)
        .where(ResumeVersion.workspace_id == workspace.id)
        .order_by(ResumeVersion.version_number.desc(), ResumeVersion.created_at.desc())
    )
    versions = db.scalars(stmt).all()
    return [
        ResumeVersionResponse(
            id=v.id,
            workspace_id=v.workspace_id,
            version_number=v.version_number,
            parsed_skills=v.parsed_skills,
            predicted_role=v.predicted_role,
            top_k=[TopRole(**item) for item in v.top_k],
            model_version=v.model_version,
            parser_model=v.parser_model,
            created_at=v.created_at,
        )
        for v in versions
    ]


def delete_workspace_resume_version(
    db: Session,
    workspace_id: str,
    version_id: str,
    user_id: str,
) -> None:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    version = db.scalar(
        select(ResumeVersion).where(
            ResumeVersion.id == version_id,
            ResumeVersion.workspace_id == workspace.id,
        )
    )
    if version is None:
        raise ResumeVersionNotFoundError("Resume version not found")
    db.delete(version)
    workspace.updated_at = _utcnow()
    db.commit()


def delete_all_workspace_resume_versions(
    db: Session,
    workspace_id: str,
    user_id: str,
) -> None:
    workspace = get_workspace_for_user(db, workspace_id, user_id)
    db.execute(delete(ResumeVersion).where(ResumeVersion.workspace_id == workspace.id))
    workspace.updated_at = _utcnow()
    db.commit()
