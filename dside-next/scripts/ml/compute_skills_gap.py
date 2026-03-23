"""
Skills Gap Analysis for DSIDE.

Reads skills_gaps, unemployment_data, and training_programs from Supabase,
computes per-province demand vs supply, matches training programs to gaps,
and ranks sectors by opportunity. Outputs skills_gap_analysis.json.

Usage:
    python -m scripts.ml.compute_skills_gap
    python scripts/ml/compute_skills_gap.py
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from scripts.ml.config import SKILLS_GAP_PATH, get_supabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


def fetch_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fetch skills_gaps, unemployment_data, and training_programs from Supabase."""
    sb = get_supabase()

    logger.info("Fetching skills_gaps...")
    skills_resp = sb.table("skills_gaps").select("*").execute()
    skills_df = pd.DataFrame(skills_resp.data)

    logger.info("Fetching unemployment_data...")
    unemp_resp = sb.table("unemployment_data").select("*").execute()
    unemp_df = pd.DataFrame(unemp_resp.data)

    logger.info("Fetching training_programs...")
    training_resp = sb.table("training_programs").select("*").execute()
    training_df = pd.DataFrame(training_resp.data)

    logger.info(
        "Loaded: %d skills gaps, %d unemployment records, %d training programs",
        len(skills_df),
        len(unemp_df),
        len(training_df),
    )
    return skills_df, unemp_df, training_df


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def compute_province_breakdown(
    skills_df: pd.DataFrame,
    training_df: pd.DataFrame,
) -> dict:
    """Compute per-province skills gap analysis with matched training programs."""
    provinces = {}

    if skills_df.empty:
        logger.warning("No skills_gaps data available.")
        return provinces

    for province, group in skills_df.groupby("province"):
        # Per-sector demand vs supply
        sector_gaps = []
        for sector, sector_group in group.groupby("sector"):
            total_demand = pd.to_numeric(
                sector_group["demand_count"], errors="coerce"
            ).sum()
            total_supply = pd.to_numeric(
                sector_group["supply_count"], errors="coerce"
            ).sum()
            net_gap = total_demand - total_supply

            # Find matching training programs
            matched_training = []
            if not training_df.empty:
                matches = training_df[
                    (training_df["province"] == province)
                    & (training_df["sector"] == sector)
                ]
                if matches.empty:
                    # Fall back to national programs in the same sector
                    matches = training_df[training_df["sector"] == sector]

                for _, prog in matches.iterrows():
                    matched_training.append({
                        "name": prog.get("name", ""),
                        "provider": prog.get("provider", ""),
                        "cost": float(prog["cost"]) if pd.notna(prog.get("cost")) else None,
                        "is_free": bool(prog.get("is_free", False)),
                        "employment_rate": (
                            float(prog["employment_rate"])
                            if pd.notna(prog.get("employment_rate"))
                            else None
                        ),
                    })

            # Scarce skills in this sector
            scarce_occupations = group[
                (group["sector"] == sector)
                & (group.get("is_scarce", pd.Series(dtype=bool)).fillna(False))
            ]
            scarce_list = scarce_occupations["occupation"].tolist() if not scarce_occupations.empty else []

            # Opportunity score: high demand + low supply + available training
            training_available = len(matched_training) > 0
            opportunity_score = (
                (net_gap / max(total_demand, 1)) * 0.5
                + (1.0 if training_available else 0.0) * 0.3
                + (min(total_demand, 1000) / 1000) * 0.2
            )

            sector_gaps.append({
                "sector": sector,
                "total_demand": int(total_demand) if not np.isnan(total_demand) else 0,
                "total_supply": int(total_supply) if not np.isnan(total_supply) else 0,
                "net_gap": int(net_gap) if not np.isnan(net_gap) else 0,
                "opportunity_score": round(float(opportunity_score), 3),
                "scarce_occupations": scarce_list,
                "matched_training": matched_training,
            })

        # Sort sectors by opportunity
        sector_gaps.sort(key=lambda x: x["opportunity_score"], reverse=True)

        provinces[province] = {
            "sectors": sector_gaps,
            "total_gap": sum(s["net_gap"] for s in sector_gaps),
            "top_opportunity_sector": sector_gaps[0]["sector"] if sector_gaps else None,
        }

    return provinces


def compute_national_top_occupations(skills_df: pd.DataFrame, top_n: int = 10) -> list[dict]:
    """Compute the top N most in-demand occupations nationally."""
    if skills_df.empty:
        return []

    occupation_demand = (
        skills_df.groupby("occupation")
        .agg(
            total_demand=("demand_count", "sum"),
            total_supply=("supply_count", "sum"),
            provinces=("province", "nunique"),
            is_scarce=("is_scarce", "any"),
        )
        .reset_index()
    )
    occupation_demand["net_gap"] = (
        occupation_demand["total_demand"] - occupation_demand["total_supply"]
    )
    occupation_demand = occupation_demand.sort_values("total_demand", ascending=False)

    result = []
    for _, row in occupation_demand.head(top_n).iterrows():
        result.append({
            "occupation": row["occupation"],
            "total_demand": int(row["total_demand"]),
            "total_supply": int(row["total_supply"]),
            "net_gap": int(row["net_gap"]),
            "provinces": int(row["provinces"]),
            "is_scarce": bool(row["is_scarce"]),
        })

    return result


def compute_best_training_outcomes(training_df: pd.DataFrame, top_n: int = 10) -> list[dict]:
    """Find skills/training programs with highest employment rate after completion."""
    if training_df.empty:
        return []

    # Filter to programs with known employment rates
    valid = training_df[training_df["employment_rate"].notna()].copy()
    valid["employment_rate"] = pd.to_numeric(valid["employment_rate"], errors="coerce")
    valid = valid.sort_values("employment_rate", ascending=False)

    result = []
    for _, row in valid.head(top_n).iterrows():
        result.append({
            "name": row.get("name", ""),
            "provider": row.get("provider", ""),
            "sector": row.get("sector", ""),
            "province": row.get("province", ""),
            "employment_rate": float(row["employment_rate"]),
            "is_free": bool(row.get("is_free", False)),
            "cost": float(row["cost"]) if pd.notna(row.get("cost")) else None,
        })

    return result


def compute_recommended_paths(
    skills_df: pd.DataFrame,
    training_df: pd.DataFrame,
) -> dict:
    """Generate recommended skill paths per province."""
    paths = {}

    if skills_df.empty:
        return paths

    for province in skills_df["province"].unique():
        province_skills = skills_df[skills_df["province"] == province]

        # Find sectors with biggest gaps
        sector_gaps = (
            province_skills.groupby("sector")
            .agg(net_gap=("gap", "sum"), demand=("demand_count", "sum"))
            .reset_index()
            .sort_values("net_gap", ascending=False)
        )

        recommendations = []
        for _, sector_row in sector_gaps.head(3).iterrows():
            sector = sector_row["sector"]

            # Top occupations in this sector
            sector_occupations = province_skills[province_skills["sector"] == sector]
            top_occupations = (
                sector_occupations.sort_values("gap", ascending=False)
                .head(3)["occupation"]
                .tolist()
            )

            # Available training
            available_training = []
            if not training_df.empty:
                matches = training_df[
                    (training_df["sector"] == sector)
                    & (
                        (training_df["province"] == province)
                        | (training_df["province"].isna())
                    )
                ]
                available_training = matches["name"].tolist()[:5]

            # Qualification required
            qualifications = sector_occupations["qualification_required"].dropna().unique().tolist()

            recommendations.append({
                "sector": sector,
                "net_gap": int(sector_row["net_gap"]),
                "demand": int(sector_row["demand"]),
                "top_occupations": top_occupations,
                "available_training": available_training,
                "qualifications_required": qualifications[:3],
            })

        paths[province] = recommendations

    return paths


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def save_analysis(analysis: dict) -> None:
    """Save the complete skills gap analysis to JSON."""
    SKILLS_GAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SKILLS_GAP_PATH, "w") as f:
        json.dump(analysis, f, indent=2, default=str)
    logger.info("Skills gap analysis saved to %s", SKILLS_GAP_PATH)


def store_results_to_supabase(analysis: dict) -> None:
    """Optionally store summary results back to Supabase for API access."""
    # The API routes read from the JSON file or the skills_gaps table directly.
    # This is a placeholder for future denormalised storage.
    pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the skills gap analysis pipeline."""
    logger.info("Starting skills gap analysis...")

    skills_df, unemp_df, training_df = fetch_data()

    # Compute all analyses
    province_breakdown = compute_province_breakdown(skills_df, training_df)
    top_occupations = compute_national_top_occupations(skills_df)
    best_training = compute_best_training_outcomes(training_df)
    recommended_paths = compute_recommended_paths(skills_df, training_df)

    analysis = {
        "province_breakdown": province_breakdown,
        "top_occupations_national": top_occupations,
        "best_training_outcomes": best_training,
        "recommended_paths": recommended_paths,
        "metadata": {
            "total_skills_records": len(skills_df),
            "total_training_programs": len(training_df),
            "provinces_covered": list(province_breakdown.keys()),
        },
    }

    # Print summary
    print("\n" + "=" * 60)
    print("  Skills Gap Analysis Summary")
    print("=" * 60)
    print(f"  Provinces analysed:     {len(province_breakdown)}")
    print(f"  Skills records:         {len(skills_df)}")
    print(f"  Training programs:      {len(training_df)}")
    print(f"  Top occupations:        {len(top_occupations)}")

    if top_occupations:
        print("\n  Top 5 In-Demand Occupations:")
        for occ in top_occupations[:5]:
            print(f"    - {occ['occupation']} (demand: {occ['total_demand']}, gap: {occ['net_gap']})")

    if best_training:
        print("\n  Top 5 Training Programs by Employment Rate:")
        for prog in best_training[:5]:
            print(f"    - {prog['name']} ({prog['employment_rate']:.0%})")

    print("=" * 60 + "\n")

    save_analysis(analysis)
    store_results_to_supabase(analysis)

    logger.info("Skills gap analysis complete.")


if __name__ == "__main__":
    main()
