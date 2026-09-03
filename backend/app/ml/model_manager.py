"""Model manager: load/save the trained ML model artifact."""
import os

import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml_artifacts", "model.joblib")


class ModelManager:
    def __init__(self, path: str | None = None):
        self.path = path or MODEL_PATH
        self.model = None
        self.metadata = {}

    def load(self):
        if self.model is not None:
            return self.model
        if os.path.exists(self.path):
            try:
                artifact = joblib.load(self.path)
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
        return os.path.exists(self.path)

    @property
    def model_name(self) -> str:
        if self.metadata:
            return self.metadata.get("model", "unknown")
        return getattr(self.model, "model_name", "unknown")


model_manager = ModelManager()
