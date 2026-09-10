"""ML management endpoints: model info, (re)training, and time-series forecasts."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import require_min_role
from app.db.session import get_db
from app.models.geo import User
from app.ml.model_manager import model_manager, MODEL_BOOSTER_PATH, MODEL_PATH
from app.services.config_service import get_risk_thresholds

router = APIRouter()


@router.get("/info")
def model_info(user: User = Depends(require_min_role("disaster_mgmt"))):
    metadata = model_manager.metadata or {}
    try:
        metrics = metadata.get("metrics", {})
    except Exception:
        metrics = {}
    return {
        "ready": model_manager.ready,
        "loaded": model_manager.is_loaded,
        "model_name": model_manager.model_name if model_manager.ready else None,
        "version": metadata.get("version", "v1"),
        "trained_at": metadata.get("trained_at"),
        "features": metadata.get("features"),
        "metrics": metrics,
        "artifacts": {
            "booster_json": model_manager.ready and MODEL_BOOSTER_PATH,
            "joblib": MODEL_PATH,
        },
    }


@router.get("/forecast")
def forecast_risk(days: int = Query(default=7, ge=1, le=14),
                  db: Session = Depends(get_db),
                  user: User = Depends(require_min_role("disaster_mgmt"))):
    from app.services.forecast_service import forecast_risk as frisk

    return frisk(db, days=days)


@router.get("/forecast/rainfall")
def forecast_rain(district_id: str | None = Query(default=None),
                  days: int = Query(default=5, ge=1, le=10),
                  db: Session = Depends(get_db),
                  user: User = Depends(require_min_role("disaster_mgmt"))):
    from app.services.forecast_service import forecast_rainfall

    return forecast_rainfall(db, district_id=district_id, days=days)


@router.post("/retrain", status_code=200)
def retrain_model(bg: bool = False,
                  user: User = Depends(require_min_role("super_admin"))):
    """Retrain on synthetic data (local legacy path). Returns job progress info."""
    if bg:
        raise HTTPException(status_code=400, detail="Background retrain not supported; run synchronously")
    try:
        from app.ml.train import train_synthetic

        result = train_synthetic(save=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}") from e
    return {
        "status": "ok",
        "best_model": result["best_model"],
        "results": result["results"],
        "note": "model.joblib updated. Restart to refresh NativeXGBoost model.json if needed.",
    }


@router.get("/thresholds")
def thresholds(db: Session = Depends(get_db), user: User = Depends(require_min_role("disaster_mgmt"))):
    return get_risk_thresholds(db)