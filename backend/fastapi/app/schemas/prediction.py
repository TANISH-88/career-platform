from pydantic import BaseModel, field_validator


class PredictionRequest(BaseModel):
    values: list[float]

    @field_validator("values")
    @classmethod
    def must_have_14_values(cls, v: list[float]) -> list[float]:
        if len(v) != 14:
            raise ValueError(f"Expected exactly 14 values, got {len(v)}")
        return v


class TopRole(BaseModel):
    role: str
    probability: float


class PredictionResult(BaseModel):
    predicted_role: str
    top_3_roles: list[TopRole]
