"""
Random Forest Employment Prediction model for DSIDE.

Reads youth/employment features from Supabase, trains a
RandomForestClassifier with 5-fold stratified cross-validation,
ranks feature importances, and saves the model and a
feature_importances.json for frontend visualisation.

Usage:
    python -m scripts.ml.train_rf
    python -m scripts.ml.train_rf --force
    python scripts/ml/train_rf.py
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.config import (
    FEATURE_IMPORTANCES_PATH,
    RF_FEATURE_COLS,
    RF_MODEL_PATH,
    get_supabase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TEST_SIZE = 0.20
CV_FOLDS = 5
TOLERANCE = 0.02

# Education level encoding
EDUCATION_LEVEL_MAP = {
    "No schooling": 0,
    "Primary": 1,
    "Some secondary": 2,
    "Matric": 3,
    "Diploma/Certificate": 4,
    "Degree": 5,
    "Postgraduate": 6,
}


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def load_training_data() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Load employment prediction features from Supabase.

    Constructs features from unemployment_data, municipalities,
    municipal_finances, and skills_gaps tables.

    Returns (X, y, feature_names).
    """
    sb = get_supabase()

    # Fetch unemployment data
    logger.info("Fetching unemployment_data...")
    unemp_resp = sb.table("unemployment_data").select("*").execute()
    unemp_df = pd.DataFrame(unemp_resp.data)

    # Fetch municipalities
    logger.info("Fetching municipalities...")
    mun_resp = sb.table("municipalities").select("*").execute()
    mun_df = pd.DataFrame(mun_resp.data)

    # Fetch finances for service delivery scores
    logger.info("Fetching municipal_finances...")
    fin_resp = sb.table("municipal_finances").select("*").execute()
    fin_df = pd.DataFrame(fin_resp.data)

    # Fetch skills gaps
    logger.info("Fetching skills_gaps...")
    skills_resp = sb.table("skills_gaps").select("*").execute()
    skills_df = pd.DataFrame(skills_resp.data)

    if unemp_df.empty or mun_df.empty:
        raise ValueError("Insufficient data in Supabase for RF training.")

    # Use latest unemployment data per municipality
    unemp_df = unemp_df.sort_values("year", ascending=False)
    unemp_latest = unemp_df.groupby("mun_code").first().reset_index()

    # Merge with municipalities
    df = mun_df.merge(unemp_latest, on="mun_code", how="inner")

    # Add finance data
    if not fin_df.empty:
        fin_df = fin_df.sort_values("financial_year", ascending=False)
        fin_latest = fin_df.groupby("mun_code").first().reset_index()
        df = df.merge(fin_latest, on="mun_code", how="left")

    # Compute features
    features = pd.DataFrame(index=df.index)
    features["mun_code"] = df["mun_code"]

    # household_employment_rate: proxy from absorption_rate
    features["household_employment_rate"] = pd.to_numeric(
        df.get("absorption_rate", pd.Series(dtype=float)), errors="coerce"
    )

    # education_level_encoded: use a default proxy (will be overridden by
    # individual prediction inputs; for training, derive from area data)
    # Use matric proportion as proxy where available
    features["education_level_encoded"] = 3.0  # default: Matric level

    # access_to_internet: proxy (0-1 scale)
    features["access_to_internet"] = 0.5  # default placeholder

    # neet_rate
    features["neet_rate"] = pd.to_numeric(
        df.get("neet_rate", pd.Series(dtype=float)), errors="coerce"
    )

    # municipal_service_delivery_score
    total_exp = pd.to_numeric(
        df.get("total_expenditure", pd.Series(dtype=float)), errors="coerce"
    )
    service_spend = pd.to_numeric(
        df.get("service_delivery_spend", pd.Series(dtype=float)), errors="coerce"
    )
    features["municipal_service_delivery_score"] = (
        service_spend / total_exp.replace(0, np.nan)
    ).fillna(0)

    # skills_gap_in_area: average gap per province
    if not skills_df.empty:
        province_gap = (
            skills_df.groupby("province")["gap"]
            .mean()
            .reset_index()
            .rename(columns={"gap": "avg_skills_gap"})
        )
        df_with_gap = df[["mun_code"]].copy()
        df_with_gap["province"] = df.get("province", "")
        df_with_gap = df_with_gap.merge(province_gap, on="province", how="left")
        features["skills_gap_in_area"] = pd.to_numeric(
            df_with_gap["avg_skills_gap"], errors="coerce"
        ).fillna(0)
    else:
        features["skills_gap_in_area"] = 0.0

    # Target: binary employed/unemployed based on youth unemployment rate
    # Municipalities with youth_unemployment_rate > 50% -> high risk (1)
    # Otherwise -> lower risk (0)
    youth_unemp = pd.to_numeric(
        df.get("youth_unemployment_rate", pd.Series(dtype=float)), errors="coerce"
    )
    # Use median split for balanced classes
    median_rate = youth_unemp.median()
    if np.isnan(median_rate):
        median_rate = 50.0
    target = (youth_unemp > median_rate).astype(int)

    feature_cols = [c for c in RF_FEATURE_COLS if c in features.columns]
    if len(feature_cols) < 3:
        raise ValueError(f"Only {len(feature_cols)} features available. Need at least 3.")

    # Drop rows with all NaN features
    X = features[feature_cols].copy()
    valid_mask = X.notna().any(axis=1) & target.notna()
    X = X[valid_mask]
    y = target[valid_mask].values

    # Impute remaining NaN with median
    for col in feature_cols:
        median_val = X[col].median()
        X[col] = X[col].fillna(median_val if not np.isnan(median_val) else 0)

    logger.info("RF training data: %d samples, %d features", len(X), len(feature_cols))
    return X.values, y, feature_cols


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_rf(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    force: bool = False,
) -> None:
    """Train the Random Forest classifier with cross-validation and quality gating."""
    classes = np.unique(y)
    logger.info("Classes: %s", classes.tolist())
    logger.info("Class distribution: %s", {int(c): int((y == c).sum()) for c in classes})

    min_class_count = min((y == c).sum() for c in classes)
    if min_class_count < 2:
        logger.warning("Insufficient samples per class for stratified split.")
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=42, stratify=y
        )

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=None,
        min_samples_split=5,
        random_state=42,
        n_jobs=-1,
    )

    # Cross-validation
    cv = StratifiedKFold(
        n_splits=min(CV_FOLDS, min_class_count), shuffle=True, random_state=42
    )
    cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="accuracy")

    print(f"\nRF Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    logger.info("CV scores: %s", cv_scores)

    # Fit on full training set
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    new_accuracy = accuracy_score(y_test, y_pred)
    new_f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"Test Accuracy: {new_accuracy:.4f}")
    print(f"Test F1 (weighted): {new_f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Feature importances
    importances = dict(zip(feature_names, model.feature_importances_))
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)

    print("\nFeature Importances:")
    for feat, imp in sorted_imp:
        bar = "#" * int(imp * 50)
        print(f"  {feat:40s} {imp:.4f} {bar}")

    # Save feature importances JSON
    importance_data = {
        "features": [
            {"name": name, "importance": float(imp)}
            for name, imp in sorted_imp
        ],
        "model_accuracy": float(new_accuracy),
        "model_f1": float(new_f1),
        "cv_mean_accuracy": float(cv_scores.mean()),
        "cv_std_accuracy": float(cv_scores.std()),
        "n_samples": len(y),
        "n_features": len(feature_names),
    }
    FEATURE_IMPORTANCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FEATURE_IMPORTANCES_PATH, "w") as f:
        json.dump(importance_data, f, indent=2)
    logger.info("Feature importances saved to %s", FEATURE_IMPORTANCES_PATH)

    # Quality gate
    should_save = force
    if not force:
        should_save = _quality_gate(X_test, y_test, new_accuracy)

    if should_save:
        joblib.dump(model, RF_MODEL_PATH)
        logger.info("RF model saved to %s", RF_MODEL_PATH)
        print(f"\nModel saved: {RF_MODEL_PATH}")
    else:
        print("\nModel NOT saved (quality gate failed). Use --force to override.")


def _quality_gate(X_test: np.ndarray, y_test: np.ndarray, new_accuracy: float) -> bool:
    """Compare new model against existing. Accept if no regression beyond tolerance."""
    if not RF_MODEL_PATH.exists():
        logger.info("No existing RF model found. Accepting new model.")
        return True

    try:
        existing = joblib.load(RF_MODEL_PATH)
        existing_pred = existing.predict(X_test)
        existing_accuracy = accuracy_score(y_test, existing_pred)
    except Exception as exc:
        logger.warning("Could not evaluate existing model: %s. Accepting new model.", exc)
        return True

    threshold = existing_accuracy - TOLERANCE
    passed = new_accuracy >= threshold

    print(
        f"Quality gate: existing={existing_accuracy:.4f} "
        f"new={new_accuracy:.4f} threshold={threshold:.4f} -> "
        f"{'PASS' if passed else 'FAIL'}"
    )
    return passed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the RF training pipeline."""
    parser = argparse.ArgumentParser(description="Train Random Forest employment model")
    parser.add_argument("--force", action="store_true", help="Skip quality gate")
    args = parser.parse_args()

    logger.info("Starting RF training pipeline...")

    X, y, feature_names = load_training_data()

    print("\n" + "=" * 60)
    print("  Random Forest Employment Prediction")
    print("=" * 60)
    print(f"  Samples:  {len(y)}")
    print(f"  Features: {feature_names}")
    print(f"  Classes:  {np.unique(y).tolist()}")
    print("=" * 60)

    train_rf(X, y, feature_names, force=args.force)

    logger.info("RF training pipeline complete.")


if __name__ == "__main__":
    main()
