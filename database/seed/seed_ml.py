"""Ensure an ML model artifact exists; trains one if missing."""
import os

from app.ml.model_manager import MODEL_PATH


def ensure_model():
    if os.path.exists(MODEL_PATH):
        print(f"ML model exists at {MODEL_PATH}")
        return
    print("No ML model found - training baseline model...")
    from app.ml.train import train_synthetic

    train_synthetic(save=True, n=4000)
    print("Model training complete.")
