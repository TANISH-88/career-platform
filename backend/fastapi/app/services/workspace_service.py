from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Prediction, SkillProfile, Workspace
from app.schemas.prediction import TopRole
from app.schemas.workspace import PredictionHistoryItem, WorkspacePredictionResponse
from app.services.feature_mapper import FeatureMapper
from app.services.predictor import PredictorService


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace does not exist or is not owned by the caller."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
