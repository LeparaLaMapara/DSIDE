#!/usr/bin/env python3
"""
Ingest municipal financial data from the National Treasury Municipal Money API.

Endpoints consumed
------------------
- /cubes/financial_position/facts   — balance sheet
- /cubes/incexp/facts               — income & expenditure
- /cubes/capital/facts              — capital expenditure
- /cubes/aged_creditor/facts        — aged creditors
- /cubes/audit_opinions/facts       — audit outcomes
- /cubes/municipalities/members     — municipality metadata

Data is upserted into the ``municipal_finances`` and ``municipalities``
Supabase tables.  The script is fully idempotent.
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

import pandas as pd
import requests

from config import (
    DEFAULT_PAGE_SIZE,
    MAX_RETRIES,
    MM_AGED_CREDITOR,
    MM_AUDIT_OPINIONS,
    MM_CAPITAL,
    MM_FINANCIAL_POSITION,
    MM_INCOME_EXPENDITURE,
    MM_MUNICIPALITIES,
    MUNICIPAL_MONEY_API,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    SEED_DIR,
    get_supabase,
    setup_logging,
)

logger = setup_logging("ingest_municipal_money")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict | None = None) -> dict:
    """GET with retries and back-off."""
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
    return {}  # unreachable but keeps type-checkers happy


def paginate_facts(url: str, cut: dict | None = None, page_size: int = DEFAULT_PAGE_SIZE) -> list[dict]:
    """
    Paginate through a Municipal Money ``/facts`` endpoint.

    The API supports ``pagesize`` and ``page`` query parameters.
    ``cut`` is a dict of dimension filters, e.g. ``{"financial_year.year": "2023"}``.
    """
    all_rows: list[dict] = []
    page = 0
    while True:
        params: dict[str, Any] = {"pagesize": page_size, "page": page}
        if cut:
            # Municipal Money expects cuts as ``dim:value|dim:value``
            cut_str = "|".join(f"{k}:{v}" for k, v in cut.items())
            params["cut"] = cut_str

        logger.info("Fetching %s  page=%d  pagesize=%d", url, page, page_size)
        data = _get_json(url, params)

        rows = data.get("data", data.get("facts", []))
        if not rows:
            break

        all_rows.extend(rows)
        logger.info("  … received %d rows (total so far: %d)", len(rows), len(all_rows))

        # If we got fewer rows than page_size we've reached the end
        if len(rows) < page_size:
            break
        page += 1

    return all_rows


# ---------------------------------------------------------------------------
# Municipality metadata
# ---------------------------------------------------------------------------

def fetch_municipalities() -> pd.DataFrame:
    """
    Fetch municipality metadata from the API and from the local seed CSV.

    Returns a DataFrame with columns matching the ``municipalities`` table.
    """
    # Try API first
    try:
        data = _get_json(f"{MUNICIPAL_MONEY_API}/cubes/municipalities/members")
        members = data.get("data", data.get("members", []))
        if members:
            df = pd.json_normalize(members)
            logger.info("Fetched %d municipalities from API", len(df))
            return _normalise_municipalities(df)
    except Exception as exc:
        logger.warning("API municipality fetch failed (%s); falling back to seed CSV", exc)

    # Fallback: local seed file
    csv_path = SEED_DIR / "municipalities.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        logger.info("Loaded %d municipalities from %s", len(df), csv_path)
        return df

    logger.error("No municipality data available")
    return pd.DataFrame()


def _normalise_municipalities(df: pd.DataFrame) -> pd.DataFrame:
    """Map raw API columns to the ``municipalities`` table schema."""
    col_map = {
        "demarcation.code": "mun_code",
        "demarcation_code": "mun_code",
        "municipality.code": "mun_code",
        "code": "mun_code",
        "name": "name",
        "municipality.name": "name",
        "province.name": "province",
        "province": "province",
        "district.name": "district",
        "district_code": "district_code",
        "category": "category",
        "latitude": "lat",
        "longitude": "lng",
    }
    renamed = {}
    for src, dst in col_map.items():
        if src in df.columns and dst not in renamed:
            renamed[dst] = df[src]
    out = pd.DataFrame(renamed)

    # Ensure mun_code exists
    if "mun_code" not in out.columns:
        logger.error("Could not determine mun_code column from API response")
        return pd.DataFrame()

    out["mun_code"] = out["mun_code"].astype(str).str.strip()
    out.drop_duplicates(subset=["mun_code"], inplace=True)
    return out


# ---------------------------------------------------------------------------
# Financial data
# ---------------------------------------------------------------------------

CUBE_ENDPOINTS = {
    "financial_position": MM_FINANCIAL_POSITION,
    "incexp": MM_INCOME_EXPENDITURE,
    "capital": MM_CAPITAL,
    "aged_creditor": MM_AGED_CREDITOR,
    "audit_opinions": MM_AUDIT_OPINIONS,
}


def fetch_financial_data(cube: str, url: str, year: str | None = None) -> pd.DataFrame:
    """Fetch facts for a given cube and return a cleaned DataFrame."""
    cut = {}
    if year:
        cut["financial_year.year"] = year

    rows = paginate_facts(url, cut=cut)
    if not rows:
        logger.warning("No data returned for cube=%s year=%s", cube, year)
        return pd.DataFrame()

    df = pd.json_normalize(rows)
    logger.info("Cube %s: %d raw rows", cube, len(df))
    return _clean_financial(df, cube)


def _clean_financial(df: pd.DataFrame, cube: str) -> pd.DataFrame:
    """Normalise financial fact rows into the ``municipal_finances`` schema."""
    # Identify the mun_code column
    mun_col = None
    for candidate in ["demarcation.code", "municipality.demarcation_code", "demarcation_code"]:
        if candidate in df.columns:
            mun_col = candidate
            break
    if mun_col is None:
        logger.error("Cannot find municipality code column in cube %s", cube)
        return pd.DataFrame()

    # Identify the financial year column
    year_col = None
    for candidate in ["financial_year.year", "financial_year", "year"]:
        if candidate in df.columns:
            year_col = candidate
            break
    if year_col is None:
        logger.error("Cannot find financial year column in cube %s", cube)
        return pd.DataFrame()

    # Identify amount column
    amount_col = None
    for candidate in ["amount.sum", "amount", "total_amount", "value"]:
        if candidate in df.columns:
            amount_col = candidate
            break

    out = pd.DataFrame()
    out["mun_code"] = df[mun_col].astype(str).str.strip()
    out["financial_year"] = pd.to_numeric(df[year_col], errors="coerce")
    out["cube"] = cube

    if amount_col:
        out["amount"] = pd.to_numeric(df[amount_col], errors="coerce")
    else:
        out["amount"] = None

    # Carry through any item/label columns for context
    for label_candidate in ["item.label", "item.code", "item_label", "label"]:
        if label_candidate in df.columns:
            out["item_label"] = df[label_candidate].astype(str)
            break

    for code_candidate in ["item.code", "item_code"]:
        if code_candidate in df.columns:
            out["item_code"] = df[code_candidate].astype(str)
            break

    # Drop rows with missing key fields
    out.dropna(subset=["mun_code", "financial_year"], inplace=True)
    out["financial_year"] = out["financial_year"].astype(int)

    return out


# ---------------------------------------------------------------------------
# Supabase upsert helpers
# ---------------------------------------------------------------------------

def upsert_municipalities(df: pd.DataFrame, dry_run: bool = False) -> int:
    """Upsert municipality rows. Returns count of rows sent."""
    if df.empty:
        return 0
    records = df.where(df.notna(), None).to_dict(orient="records")
    if dry_run:
        logger.info("[DRY RUN] Would upsert %d municipality rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("municipalities").upsert(batch, on_conflict="mun_code").execute()
        total += len(batch)
        logger.info("Upserted municipalities batch %d–%d", i, i + len(batch))
    return total


def upsert_finances(df: pd.DataFrame, dry_run: bool = False) -> int:
    """Upsert financial rows. Returns count of rows sent."""
    if df.empty:
        return 0
    records = df.where(df.notna(), None).to_dict(orient="records")
    if dry_run:
        logger.info("[DRY RUN] Would upsert %d municipal_finances rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("municipal_finances").upsert(
            batch, on_conflict="mun_code,financial_year,cube,item_code"
        ).execute()
        total += len(batch)
        logger.info("Upserted municipal_finances batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(year: str | None = None, all_years: bool = False, dry_run: bool = False) -> dict:
    """
    Execute the full Municipal Money ingestion pipeline.

    Returns a summary dict with row counts.
    """
    summary: dict[str, int] = {}

    # 1. Municipalities
    logger.info("=== Ingesting municipality metadata ===")
    mun_df = fetch_municipalities()
    summary["municipalities"] = upsert_municipalities(mun_df, dry_run=dry_run)

    # 2. Financial cubes
    target_year = None if all_years else (year or None)
    for cube, url in CUBE_ENDPOINTS.items():
        logger.info("=== Ingesting cube: %s (year=%s) ===", cube, target_year or "all")
        try:
            fin_df = fetch_financial_data(cube, url, year=target_year)
            count = upsert_finances(fin_df, dry_run=dry_run)
            summary[f"municipal_finances.{cube}"] = count
        except Exception:
            logger.exception("Failed to ingest cube %s", cube)
            summary[f"municipal_finances.{cube}"] = 0

    logger.info("=== Municipal Money ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d rows", k, v)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Municipal Money data into Supabase")
    parser.add_argument("--year", type=str, help="Financial year to ingest (e.g. 2023)")
    parser.add_argument("--all", action="store_true", dest="all_years", help="Ingest all available years")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and clean data but do not write to Supabase")
    args = parser.parse_args()

    run(year=args.year, all_years=args.all_years, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
