"""ML pipeline: data generation, preprocessing, training, evaluation.

Generates realistic synthetic training data for North-East India landslide risk,
trains baseline models, and persists the best artifact. Exposed via a CLI so
operators can retrain:  python -m app.ml.train
"""
import os

import joblib
import numpy as np
import pandas as pd

FEATURES = [
    "rain_1h",
    "rain_6h",
    "rain_24h",
    "rain_3d",
    "rain_7d",
    "soil_moisture",
    "slope_deg",
    "elevation_m",
    "historical_frequency",
    "distance_to_roads_m",
    "vegetation_change",
    "deformation_mm",
]

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "..", "ml_artifacts")
MODEL_PATH = os.path.join(ARTIFACT_DIR, "model.joblib")


def generate_dataset(n: int = 5000, seed: int = 42) -> pd.DataFrame:
    """Generate physically-plausible synthetic training data."""
    rng = np.random.default_rng(seed)
    # Monsoon North-East: frequently heavy, intense rainfall
    rain24 = rng.exponential(90, n) + rng.uniform(0, 80, n)
    rain3d = rain24 * rng.uniform(2.0, 3.5, n)
    data = {
        "rain_1h": rng.exponential(8, n),
        "rain_6h": rng.exponential(35, n),
        "rain_24h": rain24,
        "rain_3d": rain3d,
        "rain_7d": rain3d * rng.uniform(1.8, 2.5, n),
        "soil_moisture": np.clip(rng.normal(58, 24, n), 10, 100),
        "slope_deg": np.clip(rng.normal(22, 13, n), 0, 60),
        "elevation_m": np.clip(rng.normal(700, 450, n), 20, 2800),
        "historical_frequency": rng.poisson(1.6, n),
        "distance_to_roads_m": rng.exponential(350, n),
        "vegetation_change": rng.normal(0, 0.15, n),
        "deformation_mm": np.abs(rng.normal(5, 10, n)),
    }
    df = pd.DataFrame(data)

    # Risk score driven by dominant factors, mirroring the explainable engine.
    score = (
        np.clip((df["rain_24h"] - 40) / 200, 0, 1) * 32
        + np.clip((df["soil_moisture"] - 30) / 60, 0, 1) * 26
        + np.clip((df["slope_deg"] - 8) / 40, 0, 1) * 22
        + np.clip(df["historical_frequency"] / 4, 0, 1) * 10
        + np.clip((df["rain_3d"] - 80) / 400, 0, 1) * 8
        + np.clip(df["deformation_mm"] / 30, 0, 1) * 6
    )
    noise = rng.normal(0, 6, n)
    score = np.clip(score + noise, 0, 100)
    df["risk_score"] = np.round(score, 2)
    df["risk_level"] = pd.cut(
        df["risk_score"],
        bins=[-1, 20, 40, 60, 80, 101],
        labels=["VERY_LOW", "LOW", "MODERATE", "HIGH", "CRITICAL"],
    ).astype(str)
    return df


def _scale_pos_weight(y: pd.Series) -> float:
    neg = int((y == 0).sum())
    pos = int((y == 1).sum())
    if pos == 0:
        return 1.0
    return round(neg / max(pos, 1), 2)


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Handle missing values + clip outliers."""
    out = df.copy()
    for col in FEATURES:
        if col in out.columns:
            out[col] = out[col].fillna(out[col].median())
    # Winsorize extreme outliers to the 99th percentile
    for col in FEATURES:
        if col in out.columns:
            hi = out[col].quantile(0.99)
            out[col] = out[col].clip(upper=hi)
    return out


def train_synthetic(save: bool = True, n: int = 5000) -> dict:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import (
        accuracy_score,
        classification_report,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import RobustScaler
    from xgboost import XGBClassifier

    df_raw = generate_dataset(n)
    df = preprocess(df_raw)

    # Binary high/very-high risk target
    y_binary = (df["risk_score"] >= 60).astype(int)
    X = df[FEATURES]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_binary, test_size=0.25, random_state=42, stratify=y_binary
    )

    pre = ColumnTransformer(
        [("num", RobustScaler(), FEATURES)],
        remainder="drop",
    )

    models = {
        "xgboost": Pipeline(
            [("pre", pre), ("clf", XGBClassifier(
                n_estimators=200, max_depth=6, learning_rate=0.1,
                eval_metric="logloss", scale_pos_weight=_scale_pos_weight(y_train),
                random_state=42,
            ))]
        ),
        "gradient_boosting": Pipeline(
            [("pre", pre), ("clf", GradientBoostingClassifier(
                n_estimators=200, max_depth=4, random_state=42,
            ))]
        ),
        "random_forest": Pipeline(
            [("pre", pre), ("clf", RandomForestClassifier(
                n_estimators=200, max_depth=None, random_state=42, n_jobs=-1,
                class_weight="balanced",
            ))]
        ),
    }

    results = {}
    best = None
    best_recall = -1
    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        y_proba = (
            pipe.predict_proba(X_test)[:, 1]
            if hasattr(pipe, "predict_proba")
            else y_pred
        )
        try:
            auc = roc_auc_score(y_test, y_proba)
        except Exception:
            auc = float("nan")
        recall_val = recall_score(y_test, y_pred)
        metrics = {
            "accuracy": round(accuracy_score(y_test, y_pred), 4),
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall": round(recall_val, 4),
            "f1": round(f1_score(y_test, y_pred, zero_division=0), 4),
            "roc_auc": round(float(auc), 4),
            "confusion_matrix": None,
        }
        # confusion matrix elements
        from sklearn.metrics import confusion_matrix as cm

        tn, fp, fn, tp = cm(y_test, y_pred).ravel()
        metrics["confusion_matrix"] = {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        }
        results[name] = metrics
        print(f"\n--- {name} ---")
        print(classification_report(y_test, y_pred, zero_division=0))
        print(metrics)
        if recall_val > best_recall:
            best_recall = recall_val
            best = (name, pipe)

    chosen = best[0] if best else "xgboost"

    if save:
        os.makedirs(ARTIFACT_DIR, exist_ok=True)
        artifact = {
            "pipeline": best[1],
            "model_name": chosen,
            "features": FEATURES,
            "metrics": results[chosen],
            "model": chosen,
        }
        joblib.dump(artifact, MODEL_PATH)
        print(f"\nSaved best model '{chosen}' to {MODEL_PATH}")

    return {"results": results, "best_model": chosen}


if __name__ == "__main__":
    train_synthetic()
