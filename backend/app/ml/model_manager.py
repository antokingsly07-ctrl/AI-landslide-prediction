"""Model manager: load/save the trained ML model artifact.

The Vercel runtime bundles only numpy + xgboost (no scikit-learn / scipy),
so predictions go through the pre-exported native artifacts:
    model.json        - XGBoost booster (JSON, from scripts/export_model_for_vercel.py)
    preprocess.json   - feature order + optional RobustScaler params
The legacy ``.joblib`` (sklearn pipeline) is still supported when present
(e.g. local dev after ``python -m app.ml.train``).
"""
import json
import os

import numpy as np

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "ml_artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "model.joblib")  # legacy sklearn pipeline
MODEL_BOOSTER_PATH = os.path.join(ARTIFACT_DIR, "model.json")
MODEL_PREPROCESS_PATH = os.path.join(ARTIFACT_DIR, "preprocess.json")


class NativeXGBoostModel:
    """numpy + xgboost-only inference wrapper (drop-in for the sklearn pipeline)."""

    def __init__(self, booster, preprocess: dict):
        self._booster = booster
        self._preprocess = preprocess
        self.feature_names_in_ = np.array(preprocess["features"], dtype=object)
        self.metadata = {k: v for k, v in preprocess.items() if k != "features"}

    @property
    def model_name(self) -> str:
        return self.metadata.get("model_name") or self.metadata.get("model", "xgboost")

    def _transform(self, X):
        X = np.asarray(X, dtype=np.float64)
        for g in self._preprocess.get("groups", []):
            idx = [self._preprocess["features"].index(c) for c in g["columns"]]
            cols = np.array(X[:, idx], dtype=np.float64, copy=True)
            if g.get("transformer", "") != "identity":
                if g.get("with_centering") and g.get("median"):
                    cols = cols - np.array(g["median"], dtype=np.float64)
                if g.get("with_scaling") and g.get("scale"):
                    cols = cols / np.array(g["scale"], dtype=np.float64)
            X[:, idx] = cols
        return X

    def predict_proba(self, X):
        import xgboost as xgb

        Xt = self._transform(X)
        d = xgb.DMatrix(Xt, feature_names=list(self.feature_names_in_))
        prob = np.asarray(self._booster.predict(d), dtype=np.float64).reshape(-1)
        return np.column_stack([1.0 - prob, prob])

    def predict(self, X):
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class ModelManager:
    def __init__(self):
        self.model = None
        self.metadata = {}

    def load(self):
        if self.model is not None:
            return self.model
        if os.path.exists(MODEL_BOOSTER_PATH) and os.path.exists(MODEL_PREPROCESS_PATH):
            try:
                import xgboost as xgb

                booster = xgb.Booster()
                booster.load_model(MODEL_BOOSTER_PATH)
                with open(MODEL_PREPROCESS_PATH, encoding="utf-8") as fh:
                    preprocess = json.load(fh)
                self.model = NativeXGBoostModel(booster, preprocess)
                self.metadata = self.model.metadata
                return self.model
            except Exception:
                self.model = None
        if os.path.exists(MODEL_PATH):
            try:
                import joblib

                artifact = joblib.load(MODEL_PATH)
                if isinstance(artifact, dict) and "pipeline" in artifact:
                    self.model = artifact["pipeline"]
                    self.metadata = {k: v for k, v in artifact.items() if k != "pipeline"}
                else:
                    self.model = artifact
            except Exception:
                self.model = None
        return self.model

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    @property
    def ready(self) -> bool:
        return (os.path.exists(MODEL_BOOSTER_PATH) and os.path.exists(MODEL_PREPROCESS_PATH)) or os.path.exists(
            MODEL_PATH
        )

    @property
    def model_name(self) -> str:
        if self.metadata:
            return self.metadata.get("model", self.metadata.get("model_name", "unknown"))
        return getattr(self.model, "model_name", "unknown")


model_manager = ModelManager()