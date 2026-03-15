import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_PATH = BASE_DIR / "data" / "site_fit_training_ready.csv"
MODEL_DIR = BASE_DIR.parent / "backend/models"
MODEL_PATH = MODEL_DIR / "site_fit_catboost.cbm"

def train_model():
    print(f"Loading data from {DATA_PATH}...")
    try:
        df = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"Error: Could not find training data at {DATA_PATH}")
        return

    # Define features based on the CSV headers
    features = [
        "annual_mean_temp_c",
        "grid_carbon_intensity",
        "water_stress_score",
        "population_density",
        "business_density",
        "distance_to_nearest_dc_km",
        "dc_count_within_100km"
    ]
    
    target = "label"
    
    X = df[features]
    y = df[target]

    print("Splitting data into train/test sets...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    print("Initializing CatBoostClassifier...")
    model = CatBoostClassifier(
        iterations=500,
        learning_rate=0.05,
        depth=6,
        loss_function='Logloss',
        verbose=100,
        eval_metric='AUC',
        random_seed=42,
        thread_count=2
    )

    print("Training model...")
    model.fit(
        X_train, y_train,
        eval_set=(X_test, y_test),
        early_stopping_rounds=50
    )

    print("\nEvaluating model on test set...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    
    print(classification_report(y_test, y_pred))
    auc = roc_auc_score(y_test, y_prob)
    print(f"ROC AUC: {auc:.4f}")

    print(f"\nSaving model to {MODEL_PATH}...")
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))
    print("Model saved successfully.")

if __name__ == "__main__":
    train_model()
