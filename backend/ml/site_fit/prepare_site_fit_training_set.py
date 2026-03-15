
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import RobustScaler

try:
    from imblearn.over_sampling import SMOTE
except Exception:
    SMOTE = None

INPUT_CSV = "site_fit_training_v1_canada_completed.csv"
OUTPUT_CSV = "site_fit_training_ready.csv"
REPORT_JSON = "site_fit_training_report.json"

FEATURES = [
    "annual_mean_temp_c",
    "grid_carbon_intensity",
    "water_stress_score",
    "population_density",
    "business_density",
    "distance_to_nearest_dc_km",
    "dc_count_within_100km",
]

RANDOM_SEED = 42
NEGATIVE_TO_POSITIVE_RATIO = 1.0
APPLY_SMOTE = False   # CatBoost usually does not need this if classes are already balanced.


def transform_features(X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    log_cols = [
        "grid_carbon_intensity",
        "water_stress_score",
        "population_density",
        "business_density",
        "distance_to_nearest_dc_km",
        "dc_count_within_100km",
    ]
    for c in log_cols:
        X[c] = np.log1p(np.clip(X[c].astype(float), a_min=0, a_max=None))
    return X


def log_uniform(rng: np.random.Generator, low: float, high: float, size: int) -> np.ndarray:
    low = max(low, 1e-8)
    high = max(high, low * 1.01)
    return np.exp(rng.uniform(np.log(low), np.log(high), size=size))


def impute_positive_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    out = df.copy()
    out["label"] = 1
    imputer = SimpleImputer(strategy="median")
    out[FEATURES] = imputer.fit_transform(out[FEATURES])
    medians = {feat: float(val) for feat, val in zip(FEATURES, imputer.statistics_)}
    return out, medians


def sample_synthetic_negatives(pos_df: pd.DataFrame, n_neg: int, random_state: int = 42) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(random_state)
    pos_feats = pos_df[FEATURES].copy()
    q = pos_feats.quantile([0.05, 0.25, 0.50, 0.75, 0.95])

    # Fit novelty models on positive manifold
    X_pos_t = transform_features(pos_feats)
    scaler = RobustScaler()
    X_pos_s = scaler.fit_transform(X_pos_t)

    iforest = IsolationForest(
        n_estimators=300,
        contamination=0.08,
        random_state=random_state,
    )
    iforest.fit(X_pos_s)

    nbrs = NearestNeighbors(n_neighbors=min(5, len(pos_df)))
    nbrs.fit(X_pos_s)
    pos_nn = nbrs.kneighbors(X_pos_s)[0][:, -1]
    nn_thresh = float(np.quantile(pos_nn, 0.80))

    accepted = []
    tries = 0
    max_tries = n_neg * 600

    while len(accepted) < n_neg and tries < max_tries:
        tries += 1
        cand = {}

        # Climate: not a strong separator, so sample from empirical values with light noise.
        cand["annual_mean_temp_c"] = float(np.clip(
            rng.choice(pos_feats["annual_mean_temp_c"].to_numpy()) + rng.normal(0, 1.5),
            float(pos_feats["annual_mean_temp_c"].min()),
            float(pos_feats["annual_mean_temp_c"].max()),
        ))

        # Higher-carbon grids are more likely for "not a typical preferred site".
        gc = float(rng.choice(pos_feats["grid_carbon_intensity"].to_numpy()))
        gc = gc + (abs(rng.normal(35, 25)) if rng.random() < 0.75 else rng.normal(0, 20))
        cand["grid_carbon_intensity"] = float(np.clip(
            gc,
            max(0.0, float(pos_feats["grid_carbon_intensity"].min())),
            float(pos_feats["grid_carbon_intensity"].max()) * 1.5,
        ))

        # Higher water stress is more likely for negatives.
        ws = float(rng.choice(pos_feats["water_stress_score"].to_numpy()))
        ws = ws + (abs(rng.normal(4, 4)) if rng.random() < 0.75 else rng.normal(0, 2))
        cand["water_stress_score"] = float(np.clip(
            ws,
            0.0,
            max(30.0, float(pos_feats["water_stress_score"].max()) + 10.0),
        ))

        # Population: mostly sparse areas, occasionally dense urban core that still is not a precedent site.
        if rng.random() < 0.80:
            pop = log_uniform(
                rng,
                max(0.05, float(q.loc[0.05, "population_density"]) * 0.5),
                max(1.0, float(q.loc[0.50, "population_density"]) * 0.8),
                1,
            )[0]
        else:
            pop = log_uniform(
                rng,
                max(100.0, float(q.loc[0.75, "population_density"]) * 0.8),
                max(200.0, float(q.loc[0.95, "population_density"]) * 1.3),
                1,
            )[0]
        cand["population_density"] = float(pop)

        # Business density: most negatives should have weaker surrounding business/tech ecosystem.
        if rng.random() < 0.90:
            biz = log_uniform(
                rng,
                max(1e-6, float(q.loc[0.05, "business_density"]) * 0.25),
                max(1e-4, float(q.loc[0.50, "business_density"]) * 1.2 + 1e-6),
                1,
            )[0]
        else:
            biz = log_uniform(
                rng,
                max(1e-6, float(q.loc[0.50, "business_density"])),
                max(1e-4, float(q.loc[0.95, "business_density"]) * 0.7),
                1,
            )[0]
        cand["business_density"] = float(biz)

        # Precedent-negative sites should usually be farther from existing data-center clusters.
        if rng.random() < 0.85:
            dist = log_uniform(
                rng,
                max(10.0, float(q.loc[0.50, "distance_to_nearest_dc_km"])),
                max(25.0, float(q.loc[0.95, "distance_to_nearest_dc_km"]) * 1.25),
                1,
            )[0]
        else:
            dist = log_uniform(
                rng,
                max(0.2, float(q.loc[0.25, "distance_to_nearest_dc_km"])),
                max(5.0, float(q.loc[0.75, "distance_to_nearest_dc_km"])),
                1,
            )[0]
        cand["distance_to_nearest_dc_km"] = float(dist)

        # Nearby DC count is coupled to distance.
        lam = 0.15 + 2.5 * math.exp(-dist / 80.0)
        cnt = rng.poisson(lam)
        if dist > 150 and rng.random() < 0.85:
            cnt = 0
        cand["dc_count_within_100km"] = float(np.clip(cnt, 0, 6))

        cand_df = pd.DataFrame([cand])[FEATURES]
        X_c = scaler.transform(transform_features(cand_df))

        is_outlier = bool(iforest.predict(X_c)[0] == -1)
        nn_dist = float(nbrs.kneighbors(X_c)[0][0, -1])

        anti_score = 0
        anti_score += cand["distance_to_nearest_dc_km"] > float(q.loc[0.50, "distance_to_nearest_dc_km"])
        anti_score += cand["dc_count_within_100km"] <= 2
        anti_score += cand["business_density"] < float(q.loc[0.50, "business_density"]) * 3 + 1e-6
        anti_score += cand["population_density"] < float(q.loc[0.50, "population_density"])
        anti_score += cand["grid_carbon_intensity"] >= float(q.loc[0.75, "grid_carbon_intensity"])
        anti_score += cand["water_stress_score"] >= float(q.loc[0.75, "water_stress_score"])

        if (is_outlier or nn_dist > nn_thresh) and anti_score >= 3:
            cand["label"] = 0
            accepted.append(cand)

    if len(accepted) < n_neg:
        raise RuntimeError(f"Only generated {len(accepted)} negatives out of requested {n_neg}.")

    neg_df = pd.DataFrame(accepted, columns=FEATURES + ["label"]).iloc[:n_neg].copy()
    report = {
        "negative_generation": {
            "requested_negatives": int(n_neg),
            "accepted_negatives": int(len(neg_df)),
            "tries": int(tries),
            "nn_distance_threshold": nn_thresh,
        }
    }
    return neg_df, report


def maybe_apply_smote(df: pd.DataFrame, random_state: int = 42) -> tuple[pd.DataFrame, dict]:
    counts = df["label"].value_counts().to_dict()
    if not APPLY_SMOTE:
        return df, {"smote_applied": False, "reason": "disabled; balanced classes are already adequate for CatBoost demo"}

    if SMOTE is None:
        return df, {"smote_applied": False, "reason": "imbalanced-learn is not installed"}

    min_count = min(counts.values())
    max_count = max(counts.values())
    if min_count == max_count:
        return df, {"smote_applied": False, "reason": "classes already balanced"}

    X = df[FEATURES]
    y = df["label"]
    k_neighbors = max(1, min(5, min_count - 1))
    smote = SMOTE(random_state=random_state, k_neighbors=k_neighbors)
    X_res, y_res = smote.fit_resample(X, y)
    out = pd.DataFrame(X_res, columns=FEATURES)
    out["label"] = y_res
    return out, {"smote_applied": True, "k_neighbors": int(k_neighbors), "rows_after_smote": int(len(out))}


def main():
    src = pd.read_csv(INPUT_CSV)
    pos_df, medians = impute_positive_rows(src)

    n_pos = len(pos_df)
    n_neg = int(round(n_pos * NEGATIVE_TO_POSITIVE_RATIO))
    neg_df, neg_report = sample_synthetic_negatives(pos_df, n_neg=n_neg, random_state=RANDOM_SEED)

    train_df = pd.concat(
        [pos_df[FEATURES + ["label"]], neg_df[FEATURES + ["label"]]],
        ignore_index=True,
    )

    train_df, smote_report = maybe_apply_smote(train_df, random_state=RANDOM_SEED)

    train_df = train_df.sample(frac=1.0, random_state=RANDOM_SEED).reset_index(drop=True)
    train_df.to_csv(OUTPUT_CSV, index=False)

    report = {
        "input_rows": int(len(src)),
        "output_rows": int(len(train_df)),
        "feature_columns": FEATURES,
        "class_counts": {str(k): int(v) for k, v in train_df["label"].value_counts().sort_index().to_dict().items()},
        "median_imputation_values": medians,
    }
    report.update(neg_report)
    report.update(smote_report)

    Path(REPORT_JSON).write_text(json.dumps(report, indent=2))

    print(f"Saved {OUTPUT_CSV}")
    print(f"Saved {REPORT_JSON}")
    print(train_df.head(10).to_string(index=False))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
