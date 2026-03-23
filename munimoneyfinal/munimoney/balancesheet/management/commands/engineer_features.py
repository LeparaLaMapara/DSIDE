"""
Management command to engineer features for the SVM and Random Forest models.

Reads data from the Django database (BalSheet, ProfileStats) and optionally
from CSV files in data/raw/, computes the required feature columns, and saves
the result to data/processed/.

Usage:
    python manage.py engineer_features
    python manage.py engineer_features --csv-dir /path/to/csvs
"""

import logging
import os
from datetime import datetime

import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand

from balancesheet.models import BalSheet, ProfileStats

logger = logging.getLogger(__name__)

# Features expected by the SVM model (municipality profiling)
SVM_FEATURES = [
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

# Features expected by the Random Forest model (youth employment)
RF_FEATURES = [
    "Aleast_employedadult",
    "NO_employedadult",
    "doing_nothing",
    "Multi_poor",
    "Neither_parents",
    "matric",
]


class Command(BaseCommand):
    """Compute engineered features for ML models from raw municipal data."""

    help = (
        "Read raw municipal data, compute SVM and Random Forest features, "
        "and save to data/processed/."
    )

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--csv-dir",
            type=str,
            default=None,
            help="Path to directory containing raw CSV files to augment DB data.",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Override the default output directory for processed features.",
        )

    def handle(self, *args, **options):
        """Execute the feature engineering pipeline."""
        csv_dir = options["csv_dir"]
        output_dir = options["output_dir"]

        logger.info("Starting feature engineering.")

        # Resolve output directory
        if output_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )))
            repo_root = os.path.dirname(os.path.dirname(base))
            output_dir = os.path.join(repo_root, "data", "processed")
        os.makedirs(output_dir, exist_ok=True)

        # Resolve raw CSV directory
        if csv_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )))
            repo_root = os.path.dirname(os.path.dirname(base))
            csv_dir = os.path.join(repo_root, "data", "raw")

        # -----------------------------------------------------------
        # Step 1: Load data from Django ORM
        # -----------------------------------------------------------
        bal_df = self._load_balsheet_from_db()
        profile_df = self._load_profiles_from_db()

        # Step 2: Optionally augment with CSV data
        csv_df = self._load_csv_data(csv_dir)

        # Step 3: Merge data sources
        merged = self._merge_data(bal_df, profile_df, csv_df)

        if merged.empty:
            self.stdout.write(
                self.style.WARNING(
                    "No data available after merge. "
                    "Ensure the database or CSV directory contains data."
                )
            )
            logger.warning("Feature engineering aborted: no data after merge.")
            return

        self.stdout.write(f"Merged dataset: {len(merged)} rows, {len(merged.columns)} columns")

        # -----------------------------------------------------------
        # Step 4: Compute SVM features
        # -----------------------------------------------------------
        svm_df = self._compute_svm_features(merged)
        if svm_df is not None and not svm_df.empty:
            svm_path = os.path.join(output_dir, "svm_features.csv")
            svm_df.to_csv(svm_path, index=False)
            self._log_feature_stats(svm_df, "SVM")
            self.stdout.write(
                self.style.SUCCESS(f"SVM features: {len(svm_df)} rows saved to {svm_path}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Could not compute SVM features -- insufficient columns.")
            )

        # -----------------------------------------------------------
        # Step 5: Compute Random Forest features
        # -----------------------------------------------------------
        rf_df = self._compute_rf_features(merged)
        if rf_df is not None and not rf_df.empty:
            rf_path = os.path.join(output_dir, "rf_features.csv")
            rf_df.to_csv(rf_path, index=False)
            self._log_feature_stats(rf_df, "RandomForest")
            self.stdout.write(
                self.style.SUCCESS(f"RF features: {len(rf_df)} rows saved to {rf_path}")
            )
        else:
            self.stdout.write(
                self.style.WARNING("Could not compute RF features -- insufficient columns.")
            )

        logger.info("Feature engineering complete.")
        self.stdout.write(self.style.SUCCESS("Feature engineering complete."))

    # ------------------------------------------------------------------
    # Data loading helpers
    # ------------------------------------------------------------------

    def _load_balsheet_from_db(self):
        """Load BalSheet records into a DataFrame."""
        qs = BalSheet.objects.all().values(
            "mun_code",
            "mun_name",
            "province",
            "fin_year",
            "account_type",
            "label",
            "total_amount",
        )
        df = pd.DataFrame.from_records(qs)
        logger.info("Loaded %d BalSheet records from DB.", len(df))
        return df

    def _load_profiles_from_db(self):
        """Load ProfileStats records into a DataFrame."""
        qs = ProfileStats.objects.all().values(
            "mun_code",
            "efficient_measure",
            "wellfare_measure",
            "fin_date",
            "province",
            "profile",
        )
        df = pd.DataFrame.from_records(qs)
        logger.info("Loaded %d ProfileStats records from DB.", len(df))
        return df

    def _load_csv_data(self, csv_dir):
        """
        Load and concatenate all CSV files found in the given directory.

        Returns an empty DataFrame if no CSVs are found.
        """
        if not os.path.isdir(csv_dir):
            logger.info("CSV directory does not exist: %s", csv_dir)
            return pd.DataFrame()

        frames = []
        for fname in sorted(os.listdir(csv_dir)):
            if not fname.endswith(".csv"):
                continue
            fpath = os.path.join(csv_dir, fname)
            try:
                df = pd.read_csv(fpath)
                frames.append(df)
                logger.info("Loaded CSV %s: %d rows", fname, len(df))
            except Exception as exc:
                logger.warning("Failed to read %s: %s", fpath, exc)

        if frames:
            return pd.concat(frames, ignore_index=True, sort=False)
        return pd.DataFrame()

    def _merge_data(self, bal_df, profile_df, csv_df):
        """
        Merge all data sources into a single DataFrame.

        Priority: DB data is authoritative; CSV data fills gaps.
        """
        frames = []

        if not bal_df.empty:
            frames.append(bal_df)

        if not profile_df.empty:
            # Merge profile data on mun_code if balance sheet data exists
            if not bal_df.empty and "mun_code" in bal_df.columns:
                merged = bal_df.merge(profile_df, on="mun_code", how="outer", suffixes=("", "_prof"))
                frames = [merged]
            else:
                frames.append(profile_df)

        if not csv_df.empty:
            frames.append(csv_df)

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True, sort=False)
        result.drop_duplicates(inplace=True)
        return result

    # ------------------------------------------------------------------
    # Feature computation
    # ------------------------------------------------------------------

    def _compute_svm_features(self, df):
        """
        Compute features for the SVM municipality profiling model.

        Expected features:
        - At least one employed adult (proportion)
        - Income-poor (proportion)
        - Overcrowded (proportion)
        - Matric/matric equivalent (proportion)
        - Less than Grade9 (proportion)
        - Non-poor (proportion)
        - Yes_y (citizenship proportion)
        - repairs_PPE (PPE repairs proportion)
        - OppSurplusMargin (opportunity surplus margin)
        - currRatio (current ratio)
        - profile (target label)
        """
        feature_df = pd.DataFrame()

        # Map from possible CSV/DB column names to standard feature names
        col_map = {
            "At least one employed adult": [
                "At least one employed adult",
                "at_least_one_employed_adult",
                "employed_adult_prop",
            ],
            "Income-poor": ["Income-poor", "income_poor", "income_poverty_prop"],
            "Overcrowded": ["Overcrowded", "overcrowded", "overcrowded_prop"],
            "Matric/matric equivalent": [
                "Matric/matric equivalent",
                "matric_equivalent",
                "matric_prop",
            ],
            "Less than Grade9": [
                "Less than Grade9",
                "less_than_grade9",
                "less_grade9_prop",
            ],
            "Non-poor": ["Non-poor", "non_poor", "non_poor_prop"],
            "Yes_y": ["Yes_y", "citizenship_yes", "yes_prop"],
            "repairs_PPE": ["repairs_PPE", "ppe_repairs", "repairs_ppe"],
            "OppSurplusMargin": [
                "OppSurplusMargin",
                "opp_surplus_margin",
                "opportunity_surplus_margin",
            ],
            "currRatio": ["currRatio", "current_ratio", "curr_ratio"],
        }

        for target_name, candidates in col_map.items():
            matched = False
            for candidate in candidates:
                if candidate in df.columns:
                    feature_df[target_name] = pd.to_numeric(
                        df[candidate], errors="coerce"
                    )
                    matched = True
                    break
            if not matched:
                # Attempt to derive from balance sheet data
                feature_df[target_name] = self._derive_feature(df, target_name)

        # Include target column if available
        for target_col in ["profile", "Profile", "cluster", "label_target"]:
            if target_col in df.columns:
                feature_df["profile"] = df[target_col]
                break

        # Include mun_code for identification
        if "mun_code" in df.columns:
            feature_df["mun_code"] = df["mun_code"]

        # Drop rows that are entirely NaN across feature columns
        feature_cols = [c for c in SVM_FEATURES if c in feature_df.columns]
        if feature_cols:
            feature_df.dropna(subset=feature_cols, how="all", inplace=True)

        return feature_df

    def _compute_rf_features(self, df):
        """
        Compute features for the Random Forest youth employment model.

        Expected features:
        - Aleast_employedadult (%)
        - NO_employedadult (%)
        - doing_nothing (%)
        - Multi_poor (%)
        - Neither_parents (%)
        - matric (%)
        - target: youth unemployment rate or similar
        """
        feature_df = pd.DataFrame()

        col_map = {
            "Aleast_employedadult": [
                "Aleast_employedadult",
                "At least one employed adult",
                "at_least_one_employed_adult",
            ],
            "NO_employedadult": [
                "NO_employedadult",
                "No employed adults",
                "no_employed_adult",
            ],
            "doing_nothing": [
                "doing_nothing",
                "Doing nothing",
                "doing_nothing_pct",
            ],
            "Multi_poor": [
                "Multi_poor",
                "Multi-dimensional poor",
                "multi_dimensional_poor",
            ],
            "Neither_parents": [
                "Neither_parents",
                "Neither parents employed",
                "neither_parents_employed",
            ],
            "matric": ["matric", "Matric", "matric_qualification"],
        }

        for target_name, candidates in col_map.items():
            matched = False
            for candidate in candidates:
                if candidate in df.columns:
                    feature_df[target_name] = pd.to_numeric(
                        df[candidate], errors="coerce"
                    )
                    matched = True
                    break
            if not matched:
                feature_df[target_name] = np.nan

        # Include target if available
        for target_col in [
            "youth_unemployment",
            "youth_unemployment_rate",
            "target",
            "wellfare_measure",
        ]:
            if target_col in df.columns:
                feature_df["target"] = pd.to_numeric(df[target_col], errors="coerce")
                break

        if "mun_code" in df.columns:
            feature_df["mun_code"] = df["mun_code"]

        # Drop rows entirely NaN across feature columns
        feature_cols = [c for c in RF_FEATURES if c in feature_df.columns]
        if feature_cols:
            feature_df.dropna(subset=feature_cols, how="all", inplace=True)

        return feature_df

    def _derive_feature(self, df, feature_name):
        """
        Attempt to derive a feature from balance sheet line items.

        Falls back to NaN if derivation is not possible.
        """
        if "label" not in df.columns or "total_amount" not in df.columns:
            return np.nan

        # Map feature names to balance sheet labels for derivation
        derivation_map = {
            "repairs_PPE": {
                "numerator_labels": ["Repairs and Maintenance"],
                "denominator_labels": ["Property, Plant and Equipment"],
            },
            "OppSurplusMargin": {
                "numerator_labels": ["Net Surplus/(Deficit) for the year"],
                "denominator_labels": ["Total Revenue"],
            },
            "currRatio": {
                "numerator_labels": ["Total Current Assets"],
                "denominator_labels": ["Total Current Liabilities"],
            },
        }

        if feature_name not in derivation_map:
            return np.nan

        spec = derivation_map[feature_name]

        try:
            numerator_mask = df["label"].isin(spec["numerator_labels"])
            denominator_mask = df["label"].isin(spec["denominator_labels"])

            if numerator_mask.any() and denominator_mask.any():
                num = pd.to_numeric(
                    df.loc[numerator_mask, "total_amount"], errors="coerce"
                ).sum()
                den = pd.to_numeric(
                    df.loc[denominator_mask, "total_amount"], errors="coerce"
                ).sum()
                if den != 0:
                    return num / den
        except Exception as exc:
            logger.debug("Could not derive %s: %s", feature_name, exc)

        return np.nan

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _log_feature_stats(self, df, model_name):
        """Log summary statistics for computed features."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.empty:
            return

        stats = df[numeric_cols].describe().T
        stats["missing"] = df[numeric_cols].isnull().sum()

        logger.info(
            "%s feature statistics:\n%s",
            model_name,
            stats[["mean", "std", "missing"]].to_string(),
        )
        self.stdout.write(f"\n{model_name} Feature Statistics:")
        self.stdout.write(stats[["mean", "std", "missing"]].to_string())
        self.stdout.write("")
