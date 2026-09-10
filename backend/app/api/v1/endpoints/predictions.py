"""Prediction endpoint - computes AI risk score from features."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.geo import User
from app.schemas.domain import (
    FactorContribution,
    PredictionRequest,
    PredictionResponse,
)
from app.services.prediction_service import predict

router = APIRouter()


@router.post("", response_model=PredictionResponse)
async def create_prediction(
    payload: PredictionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    features = {
        "rainfall_1h": payload.rainfall_1h,
        "rainfall_6h": payload.rainfall_6h,
        "rainfall_24h": payload.rainfall_24h,
        "rain_3d": payload.rain_3d,
        "rain_7d": payload.rain_7d,
        "soil_moisture": payload.soil_moisture,
        "slope_deg": payload.slope_deg,
        "elevation_m": payload.elevation_m,
        "historical_frequency": payload.historical_frequency,
        "distance_to_roads_m": payload.distance_to_roads_m,
        "vegetation_change": payload.vegetation_change,
        "deformation_mm": payload.deformation_mm,
    }
    try:
        pred = predict(
            features, db,
            lat=payload.latitude, lon=payload.longitude,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

    import json as _json

    factor_contribs = _json.loads(pred.factor_contributions or "[]")
    return PredictionResponse(
        risk_score=pred.risk_score,
        risk_level=pred.risk_level,
        confidence=pred.confidence,
        factors=_json.loads(pred.factors or "[]"),
        factor_contributions=[FactorContribution(**c) for c in factor_contribs],
        recommended_action=pred.recommended_action,
        model=pred.model,
        predicted_at=datetime.now(timezone.utc),
    )
