#!/usr/bin/env python3
"""
Ingest youth opportunity data into Supabase.

This module provides:
1. Seed data loading from ``dside-next/data/seed/opportunities.csv``
2. Scaffolded scrapers for live sources (SAYouth.mobi, SETA pages,
   YES4Youth) — structure only, to be completed once terms-of-service
   review is done.

Data is upserted into the ``opportunities`` table.
"""

from __future__ import annotations

import argparse

import pandas as pd

from config import SEED_DIR, get_supabase, setup_logging

logger = setup_logging("ingest_opportunities")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

def load_seed_opportunities() -> pd.DataFrame:
    path = SEED_DIR / "opportunities.csv"
    if not path.exists():
        logger.error("Opportunities seed file not found: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    logger.info("Loaded %d opportunities from %s", len(df), path)

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Type coercion
    if "is_active" in df.columns:
        df["is_active"] = df["is_active"].astype(bool)

    return df


# ---------------------------------------------------------------------------
# Scraper scaffolds
# ---------------------------------------------------------------------------

def scrape_sayouth() -> pd.DataFrame:
    """
    Scaffold for SAYouth.mobi opportunity scraping.

    NOTE: SAYouth.mobi terms of service must be reviewed before enabling
    automated scraping.  This function is a placeholder that returns an
    empty DataFrame.  When cleared for use, implement:
      - Login / session handling
      - Paginate opportunity listings
      - Extract: title, provider, type, province, description, url
    """
    logger.info("[SCAFFOLD] SAYouth.mobi scraper — not yet implemented (TOS review needed)")
    # TODO: Implement after TOS review
    # from bs4 import BeautifulSoup
    # import requests
    # base = "https://sayouth.mobi/opportunities"
    return pd.DataFrame()


def scrape_seta_learnerships() -> pd.DataFrame:
    """
    Scaffold for SETA learnership page scraping.

    Target sites include:
      - https://www.merseta.org.za/learnership-programmes/
      - https://www.bankseta.org.za/learnerships/
      - https://www.maborisha.com/learnerships/  (aggregator)
      - https://www.ewseta.org.za/learnerships/
      - https://www.mict.org.za/learnerships/

    NOTE: Each SETA site has its own structure.  This scaffold
    should be expanded per-site once HTML structures are mapped.
    """
    logger.info("[SCAFFOLD] SETA learnership scraper — not yet implemented")
    # TODO: Implement per-SETA scrapers
    return pd.DataFrame()


def scrape_yes4youth() -> pd.DataFrame:
    """
    Scaffold for YES4Youth (Youth Employment Service) opportunities.

    Target: https://www.yes4youth.co.za/
    API or listing page to be identified.
    """
    logger.info("[SCAFFOLD] YES4Youth scraper — not yet implemented")
    # TODO: Implement YES4Youth scraper
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_opportunities(df: pd.DataFrame, dry_run: bool = False) -> int:
    if df.empty:
        return 0

    records = df.where(df.notna(), None).to_dict(orient="records")

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d opportunity rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("opportunities").upsert(
            batch, on_conflict="title,provider"
        ).execute()
        total += len(batch)
        logger.info("Upserted opportunities batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(seed_only: bool = False, dry_run: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}

    # Always load seed data
    logger.info("=== Loading seed opportunities ===")
    seed_df = load_seed_opportunities()

    # Optionally run scrapers
    live_frames: list[pd.DataFrame] = []
    if not seed_only:
        for scraper_fn in [scrape_sayouth, scrape_seta_learnerships, scrape_yes4youth]:
            try:
                result = scraper_fn()
                if not result.empty:
                    live_frames.append(result)
            except Exception:
                logger.exception("Scraper %s failed", scraper_fn.__name__)

    if live_frames:
        live_df = pd.concat(live_frames, ignore_index=True)
        combined = pd.concat([seed_df, live_df], ignore_index=True)
    else:
        combined = seed_df

    # De-duplicate by title + provider
    if not combined.empty and "title" in combined.columns and "provider" in combined.columns:
        combined.drop_duplicates(subset=["title", "provider"], keep="last", inplace=True)

    summary["opportunities"] = upsert_opportunities(combined, dry_run=dry_run)

    logger.info("=== Opportunities ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d rows", k, v)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest youth opportunities into Supabase")
    parser.add_argument("--seed-only", action="store_true", help="Only load seed CSV data")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    args = parser.parse_args()

    run(seed_only=args.seed_only, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
