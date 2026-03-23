#!/usr/bin/env python3
"""
Ingest national and provincial expenditure data from the Vulekamali API.

Endpoints
---------
- /v2/provincial-expenditure/  — provincial budget allocations
- /v2/national-expenditure/    — national department spending

Focuses on education, skills development, and community development spending.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

import pandas as pd
import requests

from config import (
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    VK_NATIONAL_EXPENDITURE,
    VK_PROVINCIAL_EXPENDITURE,
    get_supabase,
    setup_logging,
)

logger = setup_logging("ingest_vulekamali")

# Departments / programmes we care about
FOCUS_DEPARTMENTS = {
    "Basic Education",
    "Higher Education and Training",
    "Higher Education, Science and Innovation",
    "Labour",
    "Employment and Labour",
    "Social Development",
    "Cooperative Governance and Traditional Affairs",
    "Small Business Development",
    "Trade, Industry and Competition",
    "Public Works and Infrastructure",
}

FOCUS_KEYWORDS = [
    "education",
    "skills",
    "training",
    "youth",
    "learnership",
    "community development",
    "employment",
    "labour",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict | None = None) -> Any:
    params = params or {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = RETRY_BACKOFF * attempt
            logger.warning("Attempt %d failed (%s) — retrying in %ds", attempt, exc, wait)
            time.sleep(wait)
    return {}


def _paginate(url: str, params: dict | None = None) -> list[dict]:
    """Follow ``next`` links to paginate through Vulekamali list endpoints."""
    params = params or {}
    results: list[dict] = []
    next_url: str | None = url

    while next_url:
        data = _get_json(next_url, params if next_url == url else None)
        if isinstance(data, dict):
            items = data.get("results", data.get("data", []))
            results.extend(items if isinstance(items, list) else [])
            next_url = data.get("next")
        elif isinstance(data, list):
            results.extend(data)
            next_url = None
        else:
            break

        logger.info("  … %d results so far", len(results))

    return results


# ---------------------------------------------------------------------------
# Provincial expenditure
# ---------------------------------------------------------------------------

def fetch_provincial_expenditure(financial_year: str | None = None) -> pd.DataFrame:
    """Fetch provincial expenditure items, optionally filtering by year."""
    logger.info("Fetching provincial expenditure (year=%s)", financial_year or "all")
    params: dict[str, str] = {}
    if financial_year:
        params["financial_year"] = financial_year

    rows = _paginate(VK_PROVINCIAL_EXPENDITURE, params)
    if not rows:
        logger.warning("No provincial expenditure data returned")
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    logger.info("Provincial expenditure: %d raw rows", len(df))
    return _clean_provincial(df)


def _clean_provincial(df: pd.DataFrame) -> pd.DataFrame:
    """Filter and reshape provincial expenditure into a standard schema."""
    # Try to identify relevant columns
    col_map: dict[str, str] = {}
    for candidate, target in [
        ("department.name", "department"),
        ("department_name", "department"),
        ("department", "department"),
        ("programme.name", "programme"),
        ("programme_name", "programme"),
        ("programme", "programme"),
        ("government.name", "province"),
        ("province", "province"),
        ("geographic_region.name", "province"),
        ("financial_year.slug", "financial_year"),
        ("financial_year", "financial_year"),
        ("budget_phase.name", "budget_phase"),
        ("budget_phase", "budget_phase"),
        ("amount", "amount"),
        ("total_budget", "amount"),
    ]:
        if candidate in df.columns and target not in col_map.values():
            col_map[candidate] = target

    out = df.rename(columns=col_map)

    # Filter to focus areas
    mask = pd.Series(False, index=out.index)
    if "department" in out.columns:
        mask |= out["department"].isin(FOCUS_DEPARTMENTS)
    if "programme" in out.columns:
        for kw in FOCUS_KEYWORDS:
            mask |= out["programme"].str.contains(kw, case=False, na=False)
    if "department" in out.columns:
        for kw in FOCUS_KEYWORDS:
            mask |= out["department"].str.contains(kw, case=False, na=False)

    filtered = out.loc[mask].copy()
    logger.info("Provincial expenditure after focus filter: %d rows", len(filtered))

    # Normalise amount
    if "amount" in filtered.columns:
        filtered["amount"] = pd.to_numeric(filtered["amount"], errors="coerce")

    filtered["source"] = "vulekamali_provincial"
    return filtered


# ---------------------------------------------------------------------------
# National expenditure
# ---------------------------------------------------------------------------

def fetch_national_expenditure(financial_year: str | None = None) -> pd.DataFrame:
    """Fetch national expenditure items."""
    logger.info("Fetching national expenditure (year=%s)", financial_year or "all")
    params: dict[str, str] = {}
    if financial_year:
        params["financial_year"] = financial_year

    rows = _paginate(VK_NATIONAL_EXPENDITURE, params)
    if not rows:
        logger.warning("No national expenditure data returned")
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    logger.info("National expenditure: %d raw rows", len(df))
    return _clean_national(df)


def _clean_national(df: pd.DataFrame) -> pd.DataFrame:
    """Filter and reshape national expenditure."""
    col_map: dict[str, str] = {}
    for candidate, target in [
        ("department.name", "department"),
        ("department_name", "department"),
        ("department", "department"),
        ("programme.name", "programme"),
        ("programme_name", "programme"),
        ("programme", "programme"),
        ("financial_year.slug", "financial_year"),
        ("financial_year", "financial_year"),
        ("budget_phase.name", "budget_phase"),
        ("budget_phase", "budget_phase"),
        ("amount", "amount"),
        ("total_budget", "amount"),
    ]:
        if candidate in df.columns and target not in col_map.values():
            col_map[candidate] = target

    out = df.rename(columns=col_map)

    mask = pd.Series(False, index=out.index)
    if "department" in out.columns:
        mask |= out["department"].isin(FOCUS_DEPARTMENTS)
    if "programme" in out.columns:
        for kw in FOCUS_KEYWORDS:
            mask |= out["programme"].str.contains(kw, case=False, na=False)
    if "department" in out.columns:
        for kw in FOCUS_KEYWORDS:
            mask |= out["department"].str.contains(kw, case=False, na=False)

    filtered = out.loc[mask].copy()
    logger.info("National expenditure after focus filter: %d rows", len(filtered))

    if "amount" in filtered.columns:
        filtered["amount"] = pd.to_numeric(filtered["amount"], errors="coerce")

    filtered["source"] = "vulekamali_national"
    return filtered


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_budget_data(df: pd.DataFrame, dry_run: bool = False) -> int:
    """Upsert rows into the ``budget_expenditure`` table."""
    if df.empty:
        return 0

    # Keep only columns that would reasonably be in the table
    keep = [
        "department", "programme", "province", "financial_year",
        "budget_phase", "amount", "source",
    ]
    cols = [c for c in keep if c in df.columns]
    records = df[cols].where(df[cols].notna(), None).to_dict(orient="records")

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d budget rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("budget_expenditure").upsert(
            batch, on_conflict="department,programme,financial_year,source"
        ).execute()
        total += len(batch)
        logger.info("Upserted budget batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(year: str | None = None, dry_run: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}

    logger.info("=== Vulekamali Provincial Expenditure ===")
    try:
        prov_df = fetch_provincial_expenditure(financial_year=year)
        summary["provincial_expenditure"] = upsert_budget_data(prov_df, dry_run=dry_run)
    except Exception:
        logger.exception("Failed to ingest provincial expenditure")
        summary["provincial_expenditure"] = 0

    logger.info("=== Vulekamali National Expenditure ===")
    try:
        nat_df = fetch_national_expenditure(financial_year=year)
        summary["national_expenditure"] = upsert_budget_data(nat_df, dry_run=dry_run)
    except Exception:
        logger.exception("Failed to ingest national expenditure")
        summary["national_expenditure"] = 0

    logger.info("=== Vulekamali ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d rows", k, v)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Vulekamali budget data into Supabase")
    parser.add_argument("--year", type=str, help="Financial year slug (e.g. 2023-24)")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    args = parser.parse_args()

    run(year=args.year, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
