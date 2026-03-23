"""
PCA Analysis for DSIDE municipal profiling.

Reads unemployment_data, municipal_finances, and municipalities from Supabase,
constructs a feature matrix per municipality, runs PCA + K-Means clustering,
and stores results back into Supabase (pca_results table) and local artefacts.

Usage:
    python -m scripts.ml.pca_analysis
    python scripts/ml/pca_analysis.py
"""

import json
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Allow running as standalone script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.config import (
    AUDIT_OUTCOME_MAP,
    CLUSTER_LABELS,
    DATA_DIR,
    MUNICIPALITY_FEATURES,
    PCA_MODEL_PATH,
    PCA_SUMMARY_PATH,
    get_supabase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

N_CLUSTERS = 4
VARIANCE_THRESHOLD = 0.90


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def fetch_data() -> pd.DataFrame:
    """Fetch and join unemployment, finance, and municipality data from Supabase."""
    sb = get_supabase()

    logger.info("Fetching municipalities...")
    mun_resp = sb.table("municipalities").select("*").execute()
    mun_df = pd.DataFrame(mun_resp.data)

    logger.info("Fetching unemployment_data...")
    unemp_resp = sb.table("unemployment_data").select("*").execute()
    unemp_df = pd.DataFrame(unemp_resp.data)

    logger.info("Fetching municipal_finances...")
    fin_resp = sb.table("municipal_finances").select("*").execute()
    fin_df = pd.DataFrame(fin_resp.data)

    if mun_df.empty:
        raise ValueError("No municipalities data found in Supabase.")

    # Use most recent year of unemployment data per municipality
    if not unemp_df.empty:
        unemp_df = unemp_df.sort_values("year", ascending=False)
        unemp_latest = unemp_df.groupby("mun_code").first().reset_index()
    else:
        logger.warning("No unemployment_data found. Using empty DataFrame.")
        unemp_latest = pd.DataFrame(columns=["mun_code"])

    # Use most recent financial year per municipality
    if not fin_df.empty:
        fin_df = fin_df.sort_values("financial_year", ascending=False)
        fin_latest = fin_df.groupby("mun_code").first().reset_index()
    else:
        logger.warning("No municipal_finances found. Using empty DataFrame.")
        fin_latest = pd.DataFrame(columns=["mun_code"])

    # Merge all three
    merged = mun_df.merge(unemp_latest, on="mun_code", how="left")
    merged = merged.merge(fin_latest, on="mun_code", how="left")

    logger.info("Merged dataset: %d municipalities", len(merged))
    return merged


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute the PCA feature matrix from merged municipal data."""
    features = pd.DataFrame(index=df.index)
    features["mun_code"] = df["mun_code"]

    # Direct columns
    features["youth_unemployment_rate"] = pd.to_numeric(
        df.get("youth_unemployment_rate", pd.Series(dtype=float)), errors="coerce"
    )
    features["neet_rate"] = pd.to_numeric(
        df.get("neet_rate", pd.Series(dtype=float)), errors="coerce"
    )
    features["absorption_rate"] = pd.to_numeric(
        df.get("absorption_rate", pd.Series(dtype=float)), errors="coerce"
    )

    # Per-capita calculations
    population = pd.to_numeric(df.get("population", pd.Series(dtype=float)), errors="coerce")
    total_expenditure = pd.to_numeric(
        df.get("total_expenditure", pd.Series(dtype=float)), errors="coerce"
    )
    total_revenue = pd.to_numeric(
        df.get("total_revenue", pd.Series(dtype=float)), errors="coerce"
    )
    service_delivery_spend = pd.to_numeric(
        df.get("service_delivery_spend", pd.Series(dtype=float)), errors="coerce"
    )
    capital_expenditure = pd.to_numeric(
        df.get("capital_expenditure", pd.Series(dtype=float)), errors="coerce"
    )

    # Avoid division by zero
    pop_safe = population.replace(0, np.nan)
    exp_safe = total_expenditure.replace(0, np.nan)

    features["expenditure_per_capita"] = total_expenditure / pop_safe
    features["service_delivery_per_capita"] = service_delivery_spend / pop_safe
    features["capital_expenditure_ratio"] = capital_expenditure / exp_safe
    features["revenue_per_capita"] = total_revenue / pop_safe
    features["expenditure_efficiency"] = service_delivery_spend / exp_safe

    # Audit outcome encoding
    features["audit_outcome_encoded"] = (
        df.get("audit_outcome", pd.Series(dtype=str))
        .map(AUDIT_OUTCOME_MAP)
        .astype(float)
    )

    # Population density (approximate: use latitude/longitude spread as proxy
    # or area if available; here we use population as a proxy rank)
    features["population_density"] = population  # will be normalised by scaler

    return features


# ---------------------------------------------------------------------------
# PCA + Clustering
# ---------------------------------------------------------------------------


def run_pca_clustering(
    features: pd.DataFrame,
) -> tuple[pd.DataFrame, PCA, StandardScaler, KMeans]:
    """Run StandardScaler -> PCA -> KMeans on the feature matrix."""
    feature_cols = [c for c in MUNICIPALITY_FEATURES if c in features.columns]
    logger.info("Using %d features: %s", len(feature_cols), feature_cols)

    X = features[feature_cols].copy()

    # Impute missing values with column median
    for col in feature_cols:
        median_val = X[col].median()
        X[col] = X[col].fillna(median_val if not np.isnan(median_val) else 0)

    # Scale
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # PCA - keep components explaining >= 90% variance
    pca_full = PCA()
    pca_full.fit(X_scaled)
    cumulative_var = np.cumsum(pca_full.explained_variance_ratio_)
    n_components = int(np.argmax(cumulative_var >= VARIANCE_THRESHOLD) + 1)
    n_components = max(n_components, 3)  # at least 3 components
    logger.info(
        "PCA: keeping %d components (%.1f%% variance)",
        n_components,
        cumulative_var[n_components - 1] * 100,
    )

    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    logger.info("Explained variance ratios: %s", pca.explained_variance_ratio_)

    # K-Means clustering
    kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_pca)

    # Build results DataFrame
    results = features[["mun_code"]].copy()
    for i in range(min(3, n_components)):
        results[f"pc{i + 1}"] = X_pca[:, i]

    # Pad missing PC columns if n_components < 3
    for i in range(n_components, 3):
        results[f"pc{i + 1}"] = 0.0

    results["cluster"] = clusters
    results["profile_label"] = results["cluster"].map(CLUSTER_LABELS)

    # Feature loadings per component (as JSON)
    loadings_matrix = pca.components_.tolist()
    results["feature_loadings"] = [
        {
            feat: float(pca.components_[0, j])
            for j, feat in enumerate(feature_cols)
        }
        for _ in range(len(results))
    ]

    # Print top loadings per component
    for i in range(n_components):
        loading_pairs = sorted(
            zip(feature_cols, pca.components_[i]),
            key=lambda x: abs(x[1]),
            reverse=True,
        )
        logger.info(
            "PC%d top loadings: %s",
            i + 1,
            [(name, f"{val:.3f}") for name, val in loading_pairs[:5]],
        )

    return results, pca, scaler, kmeans


# ---------------------------------------------------------------------------
# Store results
# ---------------------------------------------------------------------------


def store_results(results: pd.DataFrame) -> None:
    """Upsert PCA results into the pca_results Supabase table."""
    sb = get_supabase()

    records = results.to_dict(orient="records")
    for rec in records:
        # Ensure JSON-serialisable types
        for key in ["pc1", "pc2", "pc3"]:
            if key in rec and rec[key] is not None:
                rec[key] = float(rec[key])
        rec["cluster"] = int(rec["cluster"])
        if isinstance(rec.get("feature_loadings"), dict):
            rec["feature_loadings"] = json.dumps(rec["feature_loadings"])

    # Upsert in batches
    batch_size = 50
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("pca_results").upsert(batch, on_conflict="mun_code").execute()

    logger.info("Upserted %d rows into pca_results", len(records))


def save_summary(
    pca: PCA,
    kmeans: KMeans,
    feature_cols: list[str],
) -> None:
    """Generate and save the PCA summary JSON for the frontend."""
    summary = {
        "explained_variance_ratios": pca.explained_variance_ratio_.tolist(),
        "feature_names": feature_cols,
        "loadings_matrix": pca.components_.tolist(),
        "cluster_centers": kmeans.cluster_centers_.tolist(),
        "cluster_labels": CLUSTER_LABELS,
        "n_components": pca.n_components_,
        "total_variance_explained": float(sum(pca.explained_variance_ratio_)),
    }

    PCA_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PCA_SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info("PCA summary saved to %s", PCA_SUMMARY_PATH)


def save_models(pca: PCA, scaler: StandardScaler, kmeans: KMeans) -> None:
    """Save PCA model, scaler, and kmeans to disk."""
    artefacts = {
        "pca": pca,
        "scaler": scaler,
        "kmeans": kmeans,
    }
    joblib.dump(artefacts, PCA_MODEL_PATH)
    logger.info("PCA artefacts saved to %s", PCA_MODEL_PATH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the full PCA analysis pipeline."""
    logger.info("Starting PCA analysis pipeline...")

    # 1. Fetch data
    merged = fetch_data()

    # 2. Engineer features
    features = engineer_features(merged)
    logger.info("Engineered features for %d municipalities", len(features))

    # 3. Run PCA + Clustering
    feature_cols = [c for c in MUNICIPALITY_FEATURES if c in features.columns]
    results, pca, scaler, kmeans = run_pca_clustering(features)

    # 4. Print summary
    print("\n" + "=" * 60)
    print("  PCA Analysis Summary")
    print("=" * 60)
    print(f"  Municipalities analysed: {len(results)}")
    print(f"  Features used:           {len(feature_cols)}")
    print(f"  PCA components kept:     {pca.n_components_}")
    print(f"  Variance explained:      {sum(pca.explained_variance_ratio_):.1%}")
    print(f"  Clusters:                {N_CLUSTERS}")
    print("\n  Cluster distribution:")
    for cluster_id, label in CLUSTER_LABELS.items():
        count = (results["cluster"] == cluster_id).sum()
        print(f"    {cluster_id}: {label} ({count} municipalities)")
    print("=" * 60 + "\n")

    # 5. Store results
    store_results(results)

    # 6. Save artefacts
    save_models(pca, scaler, kmeans)
    save_summary(pca, kmeans, feature_cols)

    logger.info("PCA analysis pipeline complete.")


if __name__ == "__main__":
    main()
