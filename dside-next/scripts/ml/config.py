"""
ML pipeline configuration for the DSIDE platform.

Loads environment variables from ../../.env.local,
initialises the Supabase client (service role), and defines
model paths and feature lists used by the SVM and RF trainers.

Usage (standalone):
    python -m scripts.ml.config   # prints config summary
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# dside-next/scripts/ml/config.py  ->  dside-next/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = PROJECT_ROOT.parent  # DSIDE repo root

ENV_PATH = PROJECT_ROOT / ".env.local"
if not ENV_PATH.exists():
    # Fall back to repo-root .env.local
    ENV_PATH = REPO_ROOT / ".env.local"

load_dotenv(ENV_PATH)

MODEL_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "data"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

SUPABASE_URL: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print(
        "WARNING: NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set. "
        "ML scripts will fail when accessing Supabase.",
        file=sys.stderr,
    )


def get_supabase() -> Client:
    """Return an authenticated Supabase client using the service role key."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ---------------------------------------------------------------------------
# Model artefact paths
# ---------------------------------------------------------------------------

PCA_MODEL_PATH = MODEL_DIR / "pca_model.joblib"
SVM_MODEL_PATH = MODEL_DIR / "svm_profile.joblib"
RF_MODEL_PATH = MODEL_DIR / "rf_employment.joblib"

PCA_SUMMARY_PATH = DATA_DIR / "pca_summary.json"
SKILLS_GAP_PATH = DATA_DIR / "skills_gap_analysis.json"
FEATURE_IMPORTANCES_PATH = DATA_DIR / "feature_importances.json"

# ---------------------------------------------------------------------------
# Feature definitions
# ---------------------------------------------------------------------------

# PCA / SVM features (municipality-level)
MUNICIPALITY_FEATURES = [
    "youth_unemployment_rate",
    "neet_rate",
    "absorption_rate",
    "expenditure_per_capita",
    "service_delivery_per_capita",
    "capital_expenditure_ratio",
    "audit_outcome_encoded",
    "population_density",
    "revenue_per_capita",
    "expenditure_efficiency",
]

# SVM profiling model feature columns (same as PCA input)
SVM_FEATURE_COLS = MUNICIPALITY_FEATURES

# Random Forest employment prediction features
RF_FEATURE_COLS = [
    "household_employment_rate",
    "education_level_encoded",
    "access_to_internet",
    "neet_rate",
    "municipal_service_delivery_score",
    "skills_gap_in_area",
]

# Audit outcome encoding mapping
AUDIT_OUTCOME_MAP = {
    "Unqualified - No findings": 4,
    "Unqualified - With findings": 3,
    "Qualified": 2,
    "Adverse": 1,
    "Disclaimer": 0,
}

# PCA cluster profile labels
CLUSTER_LABELS = {
    0: "High Unemployment - Poor Services",
    1: "High Unemployment - Moderate Services",
    2: "Low Unemployment - Good Services",
    3: "Low Unemployment - Strong Economy",
}

# ---------------------------------------------------------------------------
# Entry point (config summary)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("DSIDE ML Pipeline Configuration")
    print("=" * 50)
    print(f"Project root:    {PROJECT_ROOT}")
    print(f"Env file:        {ENV_PATH} (exists={ENV_PATH.exists()})")
    print(f"Model dir:       {MODEL_DIR}")
    print(f"Data dir:        {DATA_DIR}")
    print(f"Supabase URL:    {SUPABASE_URL[:30]}..." if SUPABASE_URL else "Supabase URL:    NOT SET")
    print(f"Service key:     {'SET' if SUPABASE_SERVICE_KEY else 'NOT SET'}")
    print(f"PCA features:    {len(MUNICIPALITY_FEATURES)}")
    print(f"RF features:     {len(RF_FEATURE_COLS)}")
