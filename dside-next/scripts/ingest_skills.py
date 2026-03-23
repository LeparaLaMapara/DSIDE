#!/usr/bin/env python3
"""
Ingest scarce skills and training programme seed data into Supabase.

Sources
-------
- ``dside-next/data/seed/scarce_skills_2024.csv``  — DHET scarce skills list
- ``dside-next/data/seed/training_programs.csv``    — SETA learnerships, TVET programmes

Tables
------
- ``skills_gaps``
- ``training_programs``
"""

from __future__ import annotations

import argparse

import pandas as pd

from config import SEED_DIR, get_supabase, setup_logging

logger = setup_logging("ingest_skills")


# ---------------------------------------------------------------------------
# Load seed data
# ---------------------------------------------------------------------------

def load_scarce_skills() -> pd.DataFrame:
    path = SEED_DIR / "scarce_skills_2024.csv"
    if not path.exists():
        logger.error("Scarce skills seed file not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    logger.info("Loaded %d scarce skills from %s", len(df), path)

    # Normalise column names
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Ensure boolean
    if "is_scarce" in df.columns:
        df["is_scarce"] = df["is_scarce"].astype(bool)

    return df


def load_training_programs() -> pd.DataFrame:
    path = SEED_DIR / "training_programs.csv"
    if not path.exists():
        logger.error("Training programs seed file not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    logger.info("Loaded %d training programs from %s", len(df), path)

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Type coercion
    if "duration_months" in df.columns:
        df["duration_months"] = pd.to_numeric(df["duration_months"], errors="coerce").astype("Int64")
    if "cost" in df.columns:
        df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    if "estimated_employment_rate" in df.columns:
        df["estimated_employment_rate"] = pd.to_numeric(df["estimated_employment_rate"], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_skills(df: pd.DataFrame, dry_run: bool = False) -> int:
    if df.empty:
        return 0
    records = df.where(df.notna(), None).to_dict(orient="records")

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d skills_gaps rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("skills_gaps").upsert(batch, on_conflict="ofo_code").execute()
        total += len(batch)
        logger.info("Upserted skills_gaps batch %d–%d", i, i + len(batch))
    return total


def upsert_training(df: pd.DataFrame, dry_run: bool = False) -> int:
    if df.empty:
        return 0
    records = df.where(df.notna(), None).to_dict(orient="records")

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d training_programs rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("training_programs").upsert(
            batch, on_conflict="name,provider"
        ).execute()
        total += len(batch)
        logger.info("Upserted training_programs batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}

    logger.info("=== Loading scarce skills seed data ===")
    skills_df = load_scarce_skills()
    summary["skills_gaps"] = upsert_skills(skills_df, dry_run=dry_run)

    logger.info("=== Loading training programs seed data ===")
    training_df = load_training_programs()
    summary["training_programs"] = upsert_training(training_df, dry_run=dry_run)

    logger.info("=== Skills ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d rows", k, v)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest skills and training seed data into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    args = parser.parse_args()

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
