from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.config.constants import GEMINI_MODEL
from app.db.models import User
from app.db.session import get_db
from app.schemas.prediction import PredictionRequest
from app.schemas.workspace import (
    PredictionHistoryItem,
    ResumeVersionResponse,
    WorkspaceCreateRequest,
    WorkspacePredictionResponse,
    WorkspaceResponse,
)
from app.services.auth_service import get_current_user
from app.services.rate_limiter import rate_limit_resume
from app.services.resume_parser import ResumeValidationError, extract_and_score_resume
from app.services.workspace_service import (
    ResumeVersionLimitError,
    ResumeVersionNotFoundError,
    WorkspaceNotFoundError,
    archive_workspace,
    create_workspace,
    create_workspace_resume_version,
    delete_all_workspace_resume_versions,
    delete_workspace,
    delete_workspace_resume_version,
    ensure_resume_version_capacity,
    get_last_active_workspace,
    get_workspace_for_user,
    get_workspace_history,
    list_workspace_resume_versions,
    list_workspaces,
    predict_in_workspace,
    unarchive_workspace,
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
    include_archived: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_workspaces(db, user_id=current_user.id, include_archived=include_archived)


@workspaces_router.get("/last-active", response_model=WorkspaceResponse)
def get_last_active_workspace_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_last_active_workspace(db, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return get_workspace_for_user(
            db, workspace_id=workspace_id, user_id=current_user.id, mark_opened=True
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.post("/{workspace_id}/archive", response_model=WorkspaceResponse)
def archive_workspace_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return archive_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.post("/{workspace_id}/unarchive", response_model=WorkspaceResponse)
def unarchive_workspace_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return unarchive_workspace(db, workspace_id=workspace_id, user_id=current_user.id)
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


@workspaces_router.post(
    "/{workspace_id}/resume-versions",
    response_model=ResumeVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace_resume_version_route(
    workspace_id: str,
    request: Request,
    file: UploadFile = File(...),
    consent: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a PDF/DOCX resume with explicit consent, extract derived scores + predict,
    and store only derived outputs (no raw bytes, filename, or plaintext).
    """
    # Rate limit first (DoS guard before any DB work)
    rate_limit_resume(request, user_id=current_user.id)

    try:
        ensure_resume_version_capacity(db, workspace_id=workspace_id, user_id=current_user.id)
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResumeVersionLimitError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if not consent:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Explicit consent is required before sending resume text for AI skill extraction.",
        )

    file_bytes = await file.read()
    parser = request.app.state.resume_parser
    try:
        _, ordered_scores = extract_and_score_resume(
            file_bytes=file_bytes,
            filename=file.filename,
            content_type=file.content_type,
            parser=parser,
        )
    except ResumeValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    feature_mapper = request.app.state.feature_mapper
    predictor = request.app.state.predictor
    model_version = getattr(request.app.state, "model_version", "frf_v1")
    try:
        return create_workspace_resume_version(
            db=db,
            workspace_id=workspace_id,
            user_id=current_user.id,
            parsed_skills=ordered_scores,
            feature_mapper=feature_mapper,
            predictor=predictor,
            model_version=model_version,
            parser_model=GEMINI_MODEL,
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ResumeVersionLimitError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@workspaces_router.get(
    "/{workspace_id}/resume-versions",
    response_model=list[ResumeVersionResponse],
)
def list_workspace_resume_versions_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return list_workspace_resume_versions(
            db=db, workspace_id=workspace_id, user_id=current_user.id
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@workspaces_router.delete(
    "/{workspace_id}/resume-versions/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_workspace_resume_version_route(
    workspace_id: str,
    version_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_workspace_resume_version(
            db=db, workspace_id=workspace_id, version_id=version_id, user_id=current_user.id
        )
    except (WorkspaceNotFoundError, ResumeVersionNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@workspaces_router.delete(
    "/{workspace_id}/resume-versions",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_all_workspace_resume_versions_route(
    workspace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        delete_all_workspace_resume_versions(
            db=db, workspace_id=workspace_id, user_id=current_user.id
        )
    except WorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
