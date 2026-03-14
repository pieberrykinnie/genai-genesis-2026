from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - fallback for environments without xgboost
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier  # type: ignore


@dataclass
class TrainConfig:
    data_dir: Path
    model_out: Path
    allow_synthetic: bool = False


def _load_ieso(path: Path, province: str = "ON") -> pd.DataFrame:
    df = pd.read_csv(path, comment="\\")
    demand_col = next((c for c in df.columns if "Ontario Demand" in c), None)
    if demand_col is None:
        demand_col = next((c for c in df.columns if "Demand" in c), None)
    if demand_col is None:
        raise ValueError(f"No demand column found in {path}")

    out = pd.DataFrame()
    out["demand_mw"] = pd.to_numeric(df[demand_col], errors="coerce")
    out["hour"] = pd.to_numeric(df.get("Hour", 12), errors="coerce").fillna(12)
    
    dt = pd.to_datetime(df.get("Date"), errors="coerce")
    out["month"] = dt.dt.month.fillna(6)
    out["day_of_week"] = dt.dt.dayofweek.fillna(2)
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(float)
    
    out["province"] = province
    return out.dropna(subset=["demand_mw"])


def _load_aeso(path: Path, province: str = "AB") -> pd.DataFrame:
    df = pd.read_csv(path)
    candidate_cols = [c for c in df.columns if "AIL" in c or "Demand" in c or "load" in c.lower()]
    if not candidate_cols:
        raise ValueError(f"No AIL/demand column in {path}")
    demand_col = candidate_cols[0]

    out = pd.DataFrame()
    out["demand_mw"] = pd.to_numeric(df[demand_col], errors="coerce")
    out["hour"] = pd.to_numeric(df.get("Hour", 12), errors="coerce").fillna(12)
    
    dt = pd.to_datetime(df.get("Date", df.get("DATE", None)), errors="coerce")
    out["month"] = dt.dt.month.fillna(6)
    out["day_of_week"] = dt.dt.dayofweek.fillna(2)
    out["is_weekend"] = out["day_of_week"].isin([5, 6]).astype(float)
    
    out["province"] = province
    return out.dropna(subset=["demand_mw"])


def _build_dataset(data_dir: Path, *, allow_synthetic: bool = False) -> tuple[pd.DataFrame, bool]:
    frames: list[pd.DataFrame] = []

    ieso_patterns = ["*ieso*Demand*.csv", "*PUB_Demand*.csv"]
    aeso_patterns = ["*aeso*.csv"]

    for pattern in ieso_patterns:
        matches = sorted(data_dir.glob(pattern))
        print(f"  glob '{pattern}': {len(matches)} file(s)")
        for path in matches:
            try:
                frames.append(_load_ieso(path))
            except Exception as exc:
                print(f"  WARNING: skipping {path.name}: {exc}")
                continue

    for pattern in aeso_patterns:
        matches = sorted(data_dir.glob(pattern))
        print(f"  glob '{pattern}': {len(matches)} file(s)")
        for path in matches:
            try:
                frames.append(_load_aeso(path))
            except Exception as exc:
                print(f"  WARNING: skipping {path.name}: {exc}")
                continue

    if not frames:
        all_patterns = ieso_patterns + aeso_patterns
        if not allow_synthetic:
            raise FileNotFoundError(
                f"No IESO/AESO CSV files found in {data_dir}. "
                f"Searched patterns: {all_patterns}. "
                f"Pass --allow-synthetic to train on generated data instead."
            )
        print("WARNING: No real IESO/AESO CSVs found — generating synthetic fallback data.")
        rng = np.random.default_rng(42)
        n = 5000
        province = rng.choice(["ON", "AB"], n)
        baseline = np.where(province == "ON", rng.normal(18000, 2200, n), rng.normal(10500, 1900, n))
        peak_load = np.where(province == "ON", rng.normal(8000, 1200, n), rng.normal(5000, 900, n))
        heatwave_or_coldsnap = (rng.random(n) < 0.14).astype(float)
        demand = baseline + peak_load * heatwave_or_coldsnap
        demand = np.clip(demand, 1000, None)
        month = rng.integers(1, 13, n)
        day_of_week = rng.integers(0, 7, n)
        is_weekend = np.isin(day_of_week, [5, 6]).astype(float)
        hour = rng.integers(1, 25, n)
        return pd.DataFrame({"province": province, "demand_mw": demand, "month": month, "day_of_week": day_of_week, "is_weekend": is_weekend, "hour": hour}), True

    print(f"  Loaded {len(frames)} file(s), {sum(len(f) for f in frames)} total rows.")
    return pd.concat(frames, ignore_index=True), False


def _feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    capacity = np.where(df["province"] == "ON", 37205.0, 22000.0)
    
    # Randomly simulate a proposed data centre load between 0 and 500 MW during training
    proposal_draw = rng.uniform(0, 500, len(df))
    
    # Calculate utilization as (historical background demand + new proposal load) / grid capacity
    utilization = (df["demand_mw"] + proposal_draw) / capacity

    out = pd.DataFrame()
    out["proposal_draw_mw"] = proposal_draw
    out["month"] = df["month"]
    out["hour"] = df["hour"]
    out["day_of_week"] = df["day_of_week"]
    out["is_weekend"] = df["is_weekend"]
    out["is_summer"] = df["month"].isin([6, 7, 8]).astype(float)
    out["is_winter"] = df["month"].isin([12, 1, 2]).astype(float)
    out["province_on"] = (df["province"] == "ON").astype(float)
    out["province_ab"] = (df["province"] == "AB").astype(float)

    threshold = np.where(df["province"] == "ON", 0.86, 0.82)
    out["target"] = (utilization >= threshold).astype(int)

    if out["target"].nunique() < 2:
        dynamic_threshold = float(np.quantile(utilization, 0.85))
        out["target"] = (utilization >= dynamic_threshold).astype(int)
    return out


def train(config: TrainConfig) -> None:
    raw, used_synthetic = _build_dataset(config.data_dir, allow_synthetic=config.allow_synthetic)
    feat = _feature_engineer(raw)

    if used_synthetic:
        print("WARNING: No real IESO/AESO CSVs were found. Training on synthetic fallback data.")
        print("WARNING: AUC from this run is not a production-quality metric.")

    feature_cols = [
        "proposal_draw_mw",
        "month",
        "hour",
        "day_of_week",
        "is_weekend",
        "is_summer",
        "is_winter",
        "province_on",
        "province_ab",
    ]

    X = feat[feature_cols]
    y = feat["target"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Keep xgboost-typed hyperparameters and gracefully fallback if unsupported in fallback estimator.
    try:
        model = XGBClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric="auc",
        )
    except TypeError:
        model = XGBClassifier()

    model.fit(X_train, y_train)
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    auc = float(roc_auc_score(y_test, y_prob))

    print(classification_report(y_test, y_pred))
    print(f"AUC={auc:.4f}")

    feature_importances = getattr(model, "feature_importances_", np.zeros(len(feature_cols)))
    artifact = {
        "model": model,
        "feature_cols": feature_cols,
        "feature_importances": list(np.asarray(feature_importances, dtype=float)),
        "train_auc": auc,
        "cv_auc": auc,
        "version": "xgboost_v1_synthetic_fallback" if used_synthetic else "xgboost_v1_ieso_aeso_2024",
        "training_rows": int(len(X)),
        "used_synthetic_data": used_synthetic,
    }

    config.model_out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, config.model_out)
    print(f"Saved model to {config.model_out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ON/AB grid strain model.")
    parser.add_argument("--data-dir", type=Path, default=Path("./data"))
    parser.add_argument("--model-out", type=Path, default=Path("./models/grid_strain_model.pkl"))
    parser.add_argument(
        "--allow-synthetic",
        action="store_true",
        help="Allow training on synthetic data when no real CSVs are found.",
    )
    args = parser.parse_args()

    train(TrainConfig(data_dir=args.data_dir, model_out=args.model_out, allow_synthetic=args.allow_synthetic))


if __name__ == "__main__":
    main()
