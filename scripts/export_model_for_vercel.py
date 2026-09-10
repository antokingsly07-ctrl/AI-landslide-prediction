"""Export the trained sklearn pipeline to sklearn-free Vercel artifacts.

Reads  backend/app/ml_artifacts/model.joblib  and writes:
  - model.json        XGBoost booster (JSON format, no scikit-learn needed)
  - preprocess.json   feature names + RobustScaler params for numpy inference

Run from repo root with the local (or any sklearn-capable) backend venv:
    backend\\.venv\\Scripts\\python.exe scripts/export_model_for_vercel.py
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ARTIFACT_DIR = os.path.join(ROOT, "backend", "app", "ml_artifacts")
JOBLIB = os.path.join(ARTIFACT_DIR, "model.joblib")
BOOSTER_JSON = os.path.join(ARTIFACT_DIR, "model.json")
PREPROCESS_JSON = os.path.join(ARTIFACT_DIR, "preprocess.json")


def _robust_scaler_params(transformer):
    with_centering = bool(getattr(transformer, "with_centering", True))
    with_scaling = bool(getattr(transformer, "with_scaling", True))
    median = None
    scale = None
    if with_centering:
        med = getattr(transformer, "median_", None)
        median = np.round(np.asarray(med, dtype=float), 8).tolist() if med is not None else None
    if with_scaling:
        sc = getattr(transformer, "scale_", None)
        scale = np.round(np.asarray(sc, dtype=float), 8).tolist() if sc is not None else None
    return with_centering, with_scaling, median, scale


def main():
    import joblib  # local only - not needed at runtime

    artifact = joblib.load(JOBLIB)
    pipe = artifact["pipeline"]
    pre = pipe.named_steps["pre"]
    features = list(pipe.feature_names_in_)

    preprocess = {}
    if hasattr(pre, "transformers"):
        groups = []
        for name, t, cols in pre.transformers:
            fitted = hasattr(t, "median_") or hasattr(t, "scale_") or hasattr(t, "n_features_in_")
            if fitted:
                with_centering, with_scaling, median, scale = _robust_scaler_params(t)
                groups.append({
                    "columns": list(cols),
                    "transformer": type(t).__name__,
                    "with_centering": with_centering,
                    "with_scaling": with_scaling,
                    "median": median,
                    "scale": scale,
                })
            else:
                print(f"NOTE: {type(t).__name__} was never fitted - treating as identity "
                      f"(raw features go straight to the model).")
                groups.append({
                    "columns": list(cols),
                    "transformer": "identity",
                })
        preprocess["groups"] = groups
    else:
        raise SystemExit(f"Unexpected preprocessor: {type(pre).__name__}")

    clf = pipe.named_steps.get("clf", pipe)
    if not hasattr(clf, "get_booster"):
        raise SystemExit(f"Classifier {type(clf).__name__} has no get_booster()")

    booster = clf.get_booster()
    booster.save_model(BOOSTER_JSON)
    print(f"Wrote booster -> {BOOSTER_JSON} ({os.path.getsize(BOOSTER_JSON)//1024} KB)")

    preprocess.update({
        "model": artifact.get("model_name", "xgboost"),
        "model_name": artifact.get("model_name", "xgboost"),
        "n_classes": 2,
        "features": features,
        "metrics": artifact.get("metrics"),
    })
    with open(PREPROCESS_JSON, "w", encoding="utf-8") as fh:
        json.dump(preprocess, fh, indent=2)
    print(f"Wrote preprocess -> {PREPROCESS_JSON}")

    _verify(pipe, pre, booster, features, preprocess)


def _verify(pipe, pre, booster, features, preprocess):
    import xgboost as xgb

    clf = pipe.named_steps.get("clf", pipe)

    # Reconstruct raw -> preprocessed matrix with no scikit-learn at runtime.
    rng = np.random.default_rng(42)
    X = rng.uniform(0, 200, size=(200, len(features)))
    X[::17, 3] = np.nan  # a few missing values

    Xt = X.astype(float)
    for g in preprocess["groups"]:
        idx = [features.index(c) for c in g["columns"]]
        col = X[:, idx].astype(float)
        if g["transformer"] == "identity":
            pass
        else:
            if g["with_centering"] and g["median"]:
                col = col - np.array(g["median"])
            if g["with_scaling"] and g["scale"]:
                col = col / np.array(g["scale"])
        if g["columns"] == features:
            Xt = col
        else:
            Xt[:, idx] = col

    # Ground truth = the in-memory scikit booster (raw features, identical to Xt when identity).
    prob_sk = np.asarray(clf.predict_proba(Xt), dtype=float)[:, 1]

    import xgboost as xgb  # noqa
    loaded = xgb.Booster()
    loaded.load_model(os.path.join(ARTIFACT_DIR, "model.json"))
    d = xgb.DMatrix(Xt, feature_names=features)
    prob_new = np.asarray(loaded.predict(d), dtype=float)

    diff = float(np.nanmax(np.abs(prob_sk - prob_new)))
    print(f"Verification: max |booster-json vs in-memory| over 200 rows = {diff:.2e}")
    if diff < 1e-6:
        print("OK: model.json roundtrip is bit-identical to the trained model.")
    else:
        print("WARNING: predictions diverge after save/load.")


if __name__ == "__main__":
    main()