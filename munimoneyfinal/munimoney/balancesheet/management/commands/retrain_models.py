"""
Management command to retrain the SVM and Random Forest models.

Loads engineered features from data/processed/, trains new models with
cross-validation, evaluates against existing models, and only replaces
when the new model meets the quality gate.

Usage:
    python manage.py retrain_models
    python manage.py retrain_models --tolerance 0.05
    python manage.py retrain_models --force
"""

import logging
import os
import shutil
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    r2_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

logger = logging.getLogger(__name__)

# Feature column names (must match engineer_features output)
SVM_FEATURE_COLS = [
    "At least one employed adult",
    "Income-poor",
    "Overcrowded",
    "Matric/matric equivalent",
    "Less than Grade9",
    "Non-poor",
    "Yes_y",
    "repairs_PPE",
    "OppSurplusMargin",
    "currRatio",
]

RF_FEATURE_COLS = [
    "Aleast_employedadult",
    "NO_employedadult",
    "doing_nothing",
    "Multi_poor",
    "Neither_parents",
    "matric",
]


class Command(BaseCommand):
    """Retrain SVM and Random Forest models with quality gating."""

    help = (
        "Retrain the SVM and Random Forest models using engineered features. "
        "Only replaces existing models if the new model meets the quality gate."
    )

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--tolerance",
            type=float,
            default=0.02,
            help="Allowed score drop (default 0.02 = 2%%) before rejecting a new model.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="Skip quality gate and always replace existing models.",
        )
        parser.add_argument(
            "--features-dir",
            type=str,
            default=None,
            help="Directory containing engineered feature CSVs.",
        )
        parser.add_argument(
            "--test-size",
            type=float,
            default=0.20,
            help="Proportion of data reserved for the test set (default 0.20).",
        )
        parser.add_argument(
            "--cv-folds",
            type=int,
            default=5,
            help="Number of cross-validation folds (default 5).",
        )

    def handle(self, *args, **options):
        """Execute the model retraining pipeline."""
        tolerance = options["tolerance"]
        force = options["force"]
        test_size = options["test_size"]
        cv_folds = options["cv_folds"]
        features_dir = options["features_dir"]

        logger.info(
            "Starting model retrain. tolerance=%.3f force=%s cv_folds=%d",
            tolerance,
            force,
            cv_folds,
        )

        # Resolve paths
        app_base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )))
        repo_root = os.path.dirname(os.path.dirname(app_base))

        if features_dir is None:
            features_dir = os.path.join(repo_root, "data", "processed")

        svm_model_dir = os.path.join(app_base, "balancesheet", "static", "SVM")
        rf_model_dir = os.path.join(app_base, "balancesheet", "static", "Model")
        archive_dir = os.path.join(repo_root, "data", "models_archive")

        os.makedirs(svm_model_dir, exist_ok=True)
        os.makedirs(rf_model_dir, exist_ok=True)
        os.makedirs(archive_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d")

        # -------------------------------------------------------
        # SVM Model
        # -------------------------------------------------------
        svm_features_path = os.path.join(features_dir, "svm_features.csv")
        if os.path.isfile(svm_features_path):
            self.stdout.write("\n--- SVM Model Retraining ---")
            self._retrain_svm(
                svm_features_path,
                svm_model_dir,
                archive_dir,
                timestamp,
                tolerance,
                force,
                test_size,
                cv_folds,
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"SVM features not found at {svm_features_path}. Skipping.")
            )

        # -------------------------------------------------------
        # Random Forest Model
        # -------------------------------------------------------
        rf_features_path = os.path.join(features_dir, "rf_features.csv")
        if os.path.isfile(rf_features_path):
            self.stdout.write("\n--- Random Forest Model Retraining ---")
            self._retrain_rf(
                rf_features_path,
                rf_model_dir,
                archive_dir,
                timestamp,
                tolerance,
                force,
                test_size,
                cv_folds,
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"RF features not found at {rf_features_path}. Skipping.")
            )

        logger.info("Model retraining complete.")
        self.stdout.write(self.style.SUCCESS("\nModel retraining complete."))

    # ------------------------------------------------------------------
    # SVM retraining
    # ------------------------------------------------------------------

    def _retrain_svm(
        self,
        features_path,
        model_dir,
        archive_dir,
        timestamp,
        tolerance,
        force,
        test_size,
        cv_folds,
    ):
        """Train a new SVM model, evaluate, and conditionally replace."""
        df = pd.read_csv(features_path)
        logger.info("SVM features loaded: %d rows", len(df))

        # Identify available feature columns
        available = [c for c in SVM_FEATURE_COLS if c in df.columns]
        if len(available) < 3:
            self.stdout.write(
                self.style.ERROR(
                    f"Only {len(available)} SVM feature columns found. Need at least 3."
                )
            )
            return

        # Determine target column
        target_col = None
        for candidate in ["profile", "Profile", "target"]:
            if candidate in df.columns:
                target_col = candidate
                break

        if target_col is None:
            self.stdout.write(self.style.ERROR("No target column found for SVM."))
            return

        # Clean data
        df = df.dropna(subset=available + [target_col])
        if len(df) < 20:
            self.stdout.write(
                self.style.ERROR(f"Too few samples ({len(df)}) for SVM training.")
            )
            return

        X = df[available].values
        y = df[target_col].astype(int).values

        self.stdout.write(f"Features: {available}")
        self.stdout.write(f"Samples: {len(X)}, Classes: {np.unique(y).tolist()}")

        # Train/test split (stratified)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )

        # Build pipeline
        pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("svc", SVC(kernel="rbf", C=1.0, gamma="scale", random_state=42)),
        ])

        # Cross-validation
        cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
        self.stdout.write(
            f"CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})"
        )
        logger.info("SVM CV scores: %s", cv_scores)

        # Fit on full training set
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        new_accuracy = accuracy_score(y_test, y_pred)
        new_f1 = f1_score(y_test, y_pred, average="weighted")

        self.stdout.write(f"Test Accuracy: {new_accuracy:.4f}")
        self.stdout.write(f"Test F1 (weighted): {new_f1:.4f}")
        self.stdout.write("Classification Report:")
        self.stdout.write(classification_report(y_test, y_pred))
        logger.info("SVM new model accuracy=%.4f f1=%.4f", new_accuracy, new_f1)

        # Quality gate: compare to existing model
        existing_model_path = os.path.join(model_dir, "finalized_model.sav")
        should_replace = force

        if not force:
            should_replace = self._quality_gate(
                existing_model_path, X_test, y_test, new_accuracy, tolerance, "SVM"
            )

        if should_replace:
            # Archive old model
            self._archive_model(existing_model_path, archive_dir, "svm_model", timestamp)

            # Save new model with joblib
            new_model_path = os.path.join(model_dir, "finalized_model.sav")
            joblib.dump(pipeline, new_model_path)
            logger.info("SVM model saved to %s", new_model_path)
            self.stdout.write(
                self.style.SUCCESS(f"New SVM model saved: {new_model_path}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("SVM model NOT replaced (quality gate failed).")
            )

    # ------------------------------------------------------------------
    # Random Forest retraining
    # ------------------------------------------------------------------

    def _retrain_rf(
        self,
        features_path,
        model_dir,
        archive_dir,
        timestamp,
        tolerance,
        force,
        test_size,
        cv_folds,
    ):
        """Train a new Random Forest model, evaluate, and conditionally replace."""
        df = pd.read_csv(features_path)
        logger.info("RF features loaded: %d rows", len(df))

        available = [c for c in RF_FEATURE_COLS if c in df.columns]
        if len(available) < 3:
            self.stdout.write(
                self.style.ERROR(
                    f"Only {len(available)} RF feature columns found. Need at least 3."
                )
            )
            return

        # Determine target
        target_col = None
        for candidate in ["target", "youth_unemployment", "wellfare_measure"]:
            if candidate in df.columns:
                target_col = candidate
                break

        if target_col is None:
            self.stdout.write(self.style.ERROR("No target column found for Random Forest."))
            return

        df = df.dropna(subset=available + [target_col])
        if len(df) < 20:
            self.stdout.write(
                self.style.ERROR(f"Too few samples ({len(df)}) for RF training.")
            )
            return

        X = df[available].values
        y = df[target_col].values

        self.stdout.write(f"Features: {available}")
        self.stdout.write(f"Samples: {len(X)}")

        # Decide classification vs regression based on target cardinality
        unique_targets = np.unique(y[~np.isnan(y.astype(float))])
        is_classification = len(unique_targets) <= 10

        if is_classification:
            y = y.astype(int)
            self.stdout.write(f"Mode: Classification, Classes: {unique_targets.tolist()}")
            model = RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1
            )
            scoring = "accuracy"
        else:
            y = y.astype(float)
            self.stdout.write("Mode: Regression")
            model = RandomForestRegressor(
                n_estimators=100, random_state=42, n_jobs=-1
            )
            scoring = "r2"

        # Train/test split
        if is_classification:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42, stratify=y
            )
            cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42
            )
            cv = cv_folds

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=cv, scoring=scoring)
        self.stdout.write(
            f"CV {scoring}: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})"
        )
        logger.info("RF CV scores: %s", cv_scores)

        # Fit on full training set
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        if is_classification:
            new_score = accuracy_score(y_test, y_pred)
            new_f1 = f1_score(y_test, y_pred, average="weighted")
            self.stdout.write(f"Test Accuracy: {new_score:.4f}")
            self.stdout.write(f"Test F1 (weighted): {new_f1:.4f}")
            self.stdout.write("Classification Report:")
            self.stdout.write(classification_report(y_test, y_pred))
        else:
            new_score = r2_score(y_test, y_pred)
            self.stdout.write(f"Test R2: {new_score:.4f}")

        # Feature importances
        importances = dict(zip(available, model.feature_importances_))
        sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        self.stdout.write("Feature Importances:")
        for feat, imp in sorted_imp:
            self.stdout.write(f"  {feat}: {imp:.4f}")
        logger.info("RF feature importances: %s", sorted_imp)

        # Quality gate
        existing_model_path = os.path.join(model_dir, "forest.pkl")
        should_replace = force

        if not force:
            should_replace = self._quality_gate(
                existing_model_path, X_test, y_test, new_score, tolerance, "RF"
            )

        if should_replace:
            self._archive_model(existing_model_path, archive_dir, "rf_model", timestamp)

            new_model_path = os.path.join(model_dir, "forest.pkl")
            joblib.dump(model, new_model_path)
            logger.info("RF model saved to %s", new_model_path)
            self.stdout.write(
                self.style.SUCCESS(f"New RF model saved: {new_model_path}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("RF model NOT replaced (quality gate failed).")
            )

    # ------------------------------------------------------------------
    # Quality gate
    # ------------------------------------------------------------------

    def _quality_gate(self, existing_path, X_test, y_test, new_score, tolerance, label):
        """
        Compare new model score against the existing model.

        Returns True if the new model should replace the existing one.
        The new model is accepted if:
            new_score >= existing_score - tolerance
        or if no existing model is found.
        """
        if not os.path.isfile(existing_path):
            logger.info(
                "%s: No existing model at %s. New model accepted by default.",
                label,
                existing_path,
            )
            self.stdout.write(f"  No existing {label} model found. Accepting new model.")
            return True

        try:
            existing_model = joblib.load(existing_path)
        except Exception:
            # Fall back to pickle for legacy .sav/.pkl files
            try:
                import pickle
                with open(existing_path, "rb") as f:
                    existing_model = pickle.load(f)
            except Exception as exc:
                logger.warning(
                    "%s: Could not load existing model: %s. Accepting new model.",
                    label,
                    exc,
                )
                self.stdout.write(
                    f"  Could not load existing {label} model. Accepting new model."
                )
                return True

        try:
            existing_pred = existing_model.predict(X_test)
            existing_score = accuracy_score(y_test, existing_pred)
        except Exception as exc:
            logger.warning(
                "%s: Existing model prediction failed: %s. Accepting new model.",
                label,
                exc,
            )
            self.stdout.write(
                f"  Existing {label} model prediction failed. Accepting new model."
            )
            return True

        threshold = existing_score - tolerance
        passed = new_score >= threshold

        logger.info(
            "%s quality gate: existing=%.4f new=%.4f threshold=%.4f passed=%s",
            label,
            existing_score,
            new_score,
            threshold,
            passed,
        )
        self.stdout.write(
            f"  Quality gate: existing={existing_score:.4f} "
            f"new={new_score:.4f} threshold={threshold:.4f} -> "
            f"{'PASS' if passed else 'FAIL'}"
        )
        return passed

    # ------------------------------------------------------------------
    # Archiving
    # ------------------------------------------------------------------

    def _archive_model(self, model_path, archive_dir, prefix, timestamp):
        """
        Archive an existing model file by copying it to the archive directory.

        Does nothing if the model file does not exist.
        """
        if not os.path.isfile(model_path):
            return

        ext = os.path.splitext(model_path)[1]
        archive_name = f"{prefix}_{timestamp}{ext}"
        archive_path = os.path.join(archive_dir, archive_name)

        try:
            shutil.copy2(model_path, archive_path)
            logger.info("Archived %s -> %s", model_path, archive_path)
            self.stdout.write(f"  Archived: {archive_path}")
        except Exception as exc:
            logger.warning("Failed to archive %s: %s", model_path, exc)
