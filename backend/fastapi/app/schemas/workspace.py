from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.prediction import TopRole


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def strip_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Workspace name must not be blank")
        return stripped


class WorkspaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    updated_at: datetime


class WorkspacePredictionResponse(BaseModel):
    predicted_role: str
    top_3_roles: list[TopRole]
    prediction_id: str
    skill_profile_id: str
    model_version: str
    created_at: datetime


class PredictionHistoryItem(BaseModel):
    id: str
    skill_profile_id: str
    values: list[float]
    predicted_role: str
    top_k: list[TopRole]
    model_version: str
    created_at: datetime
