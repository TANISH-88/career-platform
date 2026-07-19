from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.schemas.prediction import PredictionRequest, PredictionResult

router = APIRouter()


@router.get("/")
def health_check():
    return {"message": "Backend running"}


@router.post("/predict", response_model=PredictionResult)
def predict_career(data: PredictionRequest, request: Request):
    feature_mapper = request.app.state.feature_mapper
    predictor = request.app.state.predictor
    features = feature_mapper.transform(data.values)
    result = predictor.predict(features)
    return result
