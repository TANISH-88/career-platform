from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.prediction import PredictionRequest
from app.schemas.workspace import (
    PredictionHistoryItem,
    WorkspaceCreateRequest,
    WorkspacePredictionResponse,
    WorkspaceResponse,
)
from app.services.auth_service import get_current_user
from app.services.workspace_service import (
    WorkspaceNotFoundError,
    create_workspace,
    delete_workspace,
    get_workspace_for_user,
    get_workspace_history,
    list_workspaces,
    predict_in_workspace,
)

workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@workspaces_router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace_route(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return create_workspace(db, user_id=current_user.id, name=payload.name)


@workspaces_router.get("", response_model=list[WorkspaceResponse])
def list_workspaces_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_workspaces(db, user_id=current_user.id)


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_workspace_for_user(db, workspace_id=workspace_id, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@workspaces_router.post("/{workspace_id}/predict", response_model=WorkspacePredictionResponse)
def predict_workspace_route(
    workspace_id: str,
    payload: PredictionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    feature_mapper = request.app.state.feature_mapper
    predictor = request.app.state.predictor
    model_version = getattr(request.app.state, "model_version", "frf_v1")
    try:
        return predict_in_workspace(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            values=payload.values,
            feature_mapper=feature_mapper,
            predictor=predictor,
            model_version=model_version,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.get("/{workspace_id}/history", response_model=list[PredictionHistoryItem])
def get_workspace_history_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_workspace_history(db, workspace_id=workspace_id, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
