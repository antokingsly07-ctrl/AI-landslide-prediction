"""Ensure an ML model artifact exists; trains one if missing."""
import os

from app.ml.model_manager import MODEL_BOOSTER_PATH, MODEL_PATH, model_manager


def ensure_model():
    if model_manager.ready:
        kind = "native (model.json)" if os.path.exists(MODEL_BOOSTER_PATH) else "joblib"
        print(f"ML model exists ({kind}) at {MODEL_PATH}")
        return
    print("No ML model found - training baseline model...")
    from app.ml.train import train_synthetic

    train_synthetic(save=True, n=4000)
    print("Model training complete.")
