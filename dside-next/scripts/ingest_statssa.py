#!/usr/bin/env python3
"""
Ingest StatsSA Quarterly Labour Force Survey (QLFS) data.

StatsSA does not provide a clean REST API.  This script:
1. Attempts to discover and download the latest QLFS publication from the
   StatsSA website (Excel/CSV).
2. Falls back to reading pre-downloaded files from ``dside-next/data/statssa/``.

The parsed data is upserted into the ``unemployment_data`` Supabase table.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

from config import (
    MAX_RETRIES,
    RAW_DIR,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    STATSSA_DIR,
    STATSSA_QLFS_BASE,
    get_supabase,
    setup_logging,
)

logger = setup_logging("ingest_statssa")

# Province name normalisation
PROVINCE_MAP = {
    "EC": "Eastern Cape",
    "FS": "Free State",
    "GT": "Gauteng",
    "KZN": "KwaZulu-Natal",
    "LP": "Limpopo",
    "MP": "Mpumalanga",
    "NC": "Northern Cape",
    "NW": "North West",
    "WC": "Western Cape",
}

# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _discover_latest_qlfs_url() -> str | None:
    """
    Scrape the StatsSA P0211 publications page to find the latest QLFS
    Excel or CSV download link.
    """
    logger.info("Discovering latest QLFS publication from %s", STATSSA_QLFS_BASE)
    try:
        resp = requests.get(STATSSA_QLFS_BASE, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Could not reach StatsSA publications page: %s", exc)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Look for links to Excel/CSV files
    for link in soup.find_all("a", href=True):
        href: str = link["href"]
        if re.search(r"\.(xlsx?|csv|zip)$", href, re.IGNORECASE):
            if "P0211" in href.upper() or "qlfs" in href.lower():
                full_url = href if href.startswith("http") else f"https://www.statssa.gov.za{href}"
                logger.info("Found QLFS file: %s", full_url)
                return full_url

    logger.warning("No QLFS download link found on publications page")
    return None


def _download_file(url: str, dest: Path) -> Path | None:
    """Download a file to ``dest`` directory, returning the local path."""
    dest.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0]
    local = dest / filename

    if local.exists():
        logger.info("File already downloaded: %s", local)
        return local

    logger.info("Downloading %s → %s", url, local)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            with open(local, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
            logger.info("Downloaded %s (%d bytes)", local, local.stat().st_size)
            return local
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                logger.error("Download failed after %d attempts: %s", MAX_RETRIES, exc)
                return None
            import time
            time.sleep(RETRY_BACKOFF * attempt)
    return None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _read_tabular(path: Path) -> pd.DataFrame:
    """Read a CSV or Excel file into a DataFrame."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    elif suffix in (".xls", ".xlsx"):
        return pd.read_excel(path, sheet_name=0)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def parse_qlfs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Parse a QLFS-shaped DataFrame into the ``unemployment_data`` schema.

    The exact column names vary between releases, so this function uses
    heuristic matching.
    """
    cols_lower = {c: c.lower().strip() for c in df.columns}
    df = df.rename(columns=cols_lower)

    # Try to identify key columns
    geo_col = _find_col(df, ["municipality", "district", "province", "metro", "geography", "geo"])
    rate_col = _find_col(df, ["unemployment_rate", "unemployment rate", "rate", "unemp_rate"])
    youth_col = _find_col(df, ["youth_unemployment", "youth unemployment", "youth_unemp", "youth_rate"])
    neet_col = _find_col(df, ["neet_rate", "neet rate", "neet"])
    absorption_col = _find_col(df, ["absorption_rate", "absorption rate", "absorption"])
    year_col = _find_col(df, ["year", "financial_year", "period", "quarter"])
    quarter_col = _find_col(df, ["quarter", "qtr", "q"])

    records = []
    for _, row in df.iterrows():
        record: dict = {}
        if geo_col:
            record["geography"] = str(row[geo_col]).strip()
        if rate_col:
            record["unemployment_rate"] = _safe_float(row[rate_col])
        if youth_col:
            record["youth_unemployment_rate"] = _safe_float(row[youth_col])
        if neet_col:
            record["neet_rate"] = _safe_float(row[neet_col])
        if absorption_col:
            record["absorption_rate"] = _safe_float(row[absorption_col])
        if year_col:
            record["year"] = _safe_int(row[year_col])
        if quarter_col and quarter_col != year_col:
            record["quarter"] = _safe_int(row[quarter_col])

        record["source"] = "statssa_qlfs"
        records.append(record)

    out = pd.DataFrame(records)
    out.dropna(subset=["geography"], inplace=True)

    # Try to split geography into province / district / municipality
    if "geography" in out.columns:
        out["province"] = out["geography"].map(PROVINCE_MAP).fillna(out["geography"])

    logger.info("Parsed %d QLFS rows", len(out))
    return out


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_float(val) -> float | None:
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Fallback: read local files
# ---------------------------------------------------------------------------

def load_local_qlfs() -> pd.DataFrame:
    """Read all CSV/Excel files in the statssa data directory."""
    frames = []
    if not STATSSA_DIR.exists():
        logger.warning("StatsSA data directory does not exist: %s", STATSSA_DIR)
        return pd.DataFrame()

    for f in sorted(STATSSA_DIR.iterdir()):
        if f.suffix.lower() in (".csv", ".xls", ".xlsx"):
            logger.info("Reading local file: %s", f)
            try:
                raw = _read_tabular(f)
                parsed = parse_qlfs(raw)
                frames.append(parsed)
            except Exception:
                logger.exception("Failed to parse %s", f)

    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_unemployment(df: pd.DataFrame, dry_run: bool = False) -> int:
    if df.empty:
        return 0

    keep = [
        "geography", "province", "mun_code", "district",
        "unemployment_rate", "youth_unemployment_rate",
        "neet_rate", "absorption_rate",
        "year", "quarter", "source",
    ]
    cols = [c for c in keep if c in df.columns]
    records = df[cols].where(df[cols].notna(), None).to_dict(orient="records")

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d unemployment rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 500
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("unemployment_data").upsert(
            batch, on_conflict="geography,year,quarter,source"
        ).execute()
        total += len(batch)
        logger.info("Upserted unemployment batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(dry_run: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}

    # Attempt online download
    df = pd.DataFrame()
    try:
        url = _discover_latest_qlfs_url()
        if url:
            local = _download_file(url, RAW_DIR)
            if local:
                raw = _read_tabular(local)
                df = parse_qlfs(raw)
    except Exception:
        logger.exception("Online QLFS fetch failed — falling back to local files")

    # Fallback to local
    if df.empty:
        logger.info("Attempting to load local QLFS data from %s", STATSSA_DIR)
        df = load_local_qlfs()

    if df.empty:
        logger.warning(
            "No QLFS data available. Place CSV/Excel files in %s "
            "or ensure internet access for StatsSA scraping.",
            STATSSA_DIR,
        )

    summary["unemployment_data"] = upsert_unemployment(df, dry_run=dry_run)

    logger.info("=== StatsSA ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d rows", k, v)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest StatsSA QLFS data into Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    args = parser.parse_args()

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
