"""
SVM Municipality Profiling model for DSIDE.

Reads feature data from Supabase (same features as PCA analysis),
uses PCA cluster labels as the target, trains an SVM (RBF kernel)
pipeline with 5-fold stratified cross-validation, applies a quality
gate, and saves the model.

Usage:
    python -m scripts.ml.train_svm
    python -m scripts.ml.train_svm --force
    python scripts/ml/train_svm.py
"""

import argparse
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.config import (
    MUNICIPALITY_FEATURES,
    SVM_MODEL_PATH,
    get_supabase,
)
from scripts.ml.pca_analysis import engineer_features, fetch_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TEST_SIZE = 0.20
CV_FOLDS = 5
TOLERANCE = 0.02


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


def load_training_data() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Load feature data and PCA cluster labels from Supabase.

    Returns (X, y, feature_names).
    """
    sb = get_supabase()

    # Fetch PCA cluster assignments as labels
    pca_resp = sb.table("pca_results").select("mun_code, cluster").execute()
    pca_df = pd.DataFrame(pca_resp.data)

    if pca_df.empty:
        raise ValueError(
            "No pca_results found. Run pca_analysis.py first to generate cluster labels."
        )

    # Fetch raw data and engineer features
    merged = fetch_data()
    features = engineer_features(merged)

    # Join features with cluster labels
    df = features.merge(pca_df, on="mun_code", how="inner")

    feature_cols = [c for c in MUNICIPALITY_FEATURES if c in df.columns]
    if len(feature_cols) < 3:
        raise ValueError(f"Only {len(feature_cols)} feature columns available. Need at least 3.")

    logger.info("Training data: %d samples, %d features", len(df), len(feature_cols))

    X = df[feature_cols].copy()

    # Impute missing with median
    for col in feature_cols:
        median_val = X[col].median()
        X[col] = X[col].fillna(median_val if not np.isnan(median_val) else 0)

    y = df["cluster"].astype(int).values

    return X.values, y, feature_cols


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_svm(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: list[str],
    force: bool = False,
) -> None:
    """Train the SVM model with cross-validation and quality gating."""
    classes = np.unique(y)
    logger.info("Classes: %s", classes.tolist())
    logger.info("Class distribution: %s", {int(c): int((y == c).sum()) for c in classes})

    # Check minimum samples per class for stratified split
    min_class_count = min((y == c).sum() for c in classes)
    if min_class_count < 2:
        logger.warning(
            "At least one class has fewer than 2 samples. "
            "Using all data for training (no test split)."
        )
        X_train, X_test, y_train, y_test = X, X, y, y
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=42, stratify=y
        )

    # Build pipeline
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svc", SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42, probability=True)),
    ])

    # Cross-validation
    cv = StratifiedKFold(n_splits=min(CV_FOLDS, min_class_count), shuffle=True, random_state=42)
    cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")

    print(f"\nSVM Cross-Validation Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
    logger.info("CV scores: %s", cv_scores)

    # Fit on full training set
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    new_accuracy = accuracy_score(y_test, y_pred)
    new_f1 = f1_score(y_test, y_pred, average="weighted")

    print(f"Test Accuracy: {new_accuracy:.4f}")
    print(f"Test F1 (weighted): {new_f1:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # Quality gate
    should_save = force
    if not force:
        should_save = _quality_gate(X_test, y_test, new_accuracy)

    if should_save:
        joblib.dump(pipeline, SVM_MODEL_PATH)
        logger.info("SVM model saved to %s", SVM_MODEL_PATH)
        print(f"Model saved: {SVM_MODEL_PATH}")
    else:
        print("Model NOT saved (quality gate failed). Use --force to override.")


def _quality_gate(X_test: np.ndarray, y_test: np.ndarray, new_accuracy: float) -> bool:
    """Compare new model against existing model. Accept if no regression."""
    if not SVM_MODEL_PATH.exists():
        logger.info("No existing SVM model found. Accepting new model.")
        return True

    try:
        existing = joblib.load(SVM_MODEL_PATH)
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
    """Run the SVM training pipeline."""
    parser = argparse.ArgumentParser(description="Train SVM municipality profiling model")
    parser.add_argument("--force", action="store_true", help="Skip quality gate")
    args = parser.parse_args()

    logger.info("Starting SVM training pipeline...")

    X, y, feature_names = load_training_data()

    print("\n" + "=" * 60)
    print("  SVM Municipality Profiling")
    print("=" * 60)
    print(f"  Samples:  {len(y)}")
    print(f"  Features: {feature_names}")
    print(f"  Classes:  {np.unique(y).tolist()}")
    print("=" * 60)

    train_svm(X, y, feature_names, force=args.force)

    logger.info("SVM training pipeline complete.")


if __name__ == "__main__":
    main()
