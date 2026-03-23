#!/usr/bin/env python3
"""
Ingest youth demographic and employment data from the Wazimap / Youth Explorer API.

Base URL: https://wazimap.co.za/api/v1/
Endpoint: /profiles/{geo_code}/ — demographic profiles per municipality

Focuses on youth-specific indicators and upserts into
``unemployment_data`` and ``municipalities`` tables.
"""

from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from config import (
    DEFAULT_PAGE_SIZE,
    MAX_RETRIES,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF,
    SEED_DIR,
    WAZIMAP_API,
    get_supabase,
    setup_logging,
)

logger = setup_logging("ingest_youth_explorer")

# South African province geo codes used by Wazimap
PROVINCE_GEO_CODES = {
    "EC": "Eastern Cape",
    "FS": "Free State",
    "GT": "Gauteng",
    "KZN": "KwaZulu-Natal",
    "LIM": "Limpopo",
    "MP": "Mpumalanga",
    "NC": "Northern Cape",
    "NW": "North West",
    "WC": "Western Cape",
}

# Indicator table paths within the Wazimap profile JSON
YOUTH_INDICATORS = [
    "youth_unemployment",
    "youth_education_level",
    "youth_neet",
    "youth_living_conditions",
    "youth_internet_access",
    "demographics",
    "economics",
    "education",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_json(url: str, params: dict | None = None):
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


def _load_municipality_codes() -> list[str]:
    """Load municipality geo codes from the seed CSV."""
    csv_path = SEED_DIR / "municipalities.csv"
    if not csv_path.exists():
        logger.warning("municipalities.csv not found at %s", csv_path)
        return []
    df = pd.read_csv(csv_path)
    if "mun_code" in df.columns:
        return df["mun_code"].astype(str).str.strip().tolist()
    return []


# ---------------------------------------------------------------------------
# Fetch and parse profiles
# ---------------------------------------------------------------------------

def fetch_profile(geo_code: str) -> dict:
    """Fetch the full Wazimap profile for a given geography code."""
    url = f"{WAZIMAP_API}/profiles/{geo_code}/"
    logger.info("Fetching profile for %s", geo_code)
    try:
        return _get_json(url)
    except Exception as exc:
        logger.warning("Failed to fetch profile for %s: %s", geo_code, exc)
        return {}


def extract_youth_data(geo_code: str, profile: dict) -> dict:
    """
    Extract youth-relevant indicators from a Wazimap profile response.

    Returns a flat dict suitable for upserting.
    """
    result: dict = {
        "geo_code": geo_code,
        "source": "wazimap_youth_explorer",
    }

    # The profile is nested — walk known paths
    demographics = profile.get("demographics", {})
    economics = profile.get("economics", {})
    education = profile.get("education", {})

    # Youth unemployment
    youth_unemp = (
        economics.get("youth_unemployment", {})
        or economics.get("youth_unemployment_rate", {})
    )
    if isinstance(youth_unemp, dict):
        result["youth_unemployment_rate"] = _extract_rate(youth_unemp)

    # General unemployment
    unemp = economics.get("unemployment", {})
    if isinstance(unemp, dict):
        result["unemployment_rate"] = _extract_rate(unemp)

    # NEET
    neet = economics.get("youth_neet", {}) or economics.get("neet", {})
    if isinstance(neet, dict):
        result["neet_rate"] = _extract_rate(neet)

    # Education levels
    edu_level = education.get("education_level", {})
    if isinstance(edu_level, dict):
        dist = edu_level.get("distribution", edu_level)
        if isinstance(dist, dict):
            result["no_schooling_pct"] = _safe_float(dist.get("No schooling", dist.get("None")))
            result["matric_pct"] = _safe_float(dist.get("Matric", dist.get("Grade 12")))
            result["post_matric_pct"] = _safe_float(dist.get("Post-matric", dist.get("Higher education")))

    # Internet access
    internet = demographics.get("internet_access", {}) or education.get("internet_access", {})
    if isinstance(internet, dict):
        result["internet_access_pct"] = _extract_rate(internet)

    # Absorption rate
    absorption = economics.get("absorption_rate", {})
    if isinstance(absorption, dict):
        result["absorption_rate"] = _extract_rate(absorption)

    return result


def _extract_rate(data: dict) -> float | None:
    """Pull a percentage/rate from various Wazimap data shapes."""
    for key in ["values", "this", "rate", "percentage", "value"]:
        val = data.get(key)
        if isinstance(val, dict):
            val = val.get("this", val.get("values"))
        if val is not None:
            return _safe_float(val)
    return None


def _safe_float(val) -> float | None:
    if val is None:
        return None
    try:
        f = float(str(val).replace("%", "").strip())
        return f
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Supabase upsert
# ---------------------------------------------------------------------------

def upsert_youth_data(records: list[dict], dry_run: bool = False) -> int:
    if not records:
        return 0

    if dry_run:
        logger.info("[DRY RUN] Would upsert %d youth data rows", len(records))
        return len(records)

    sb = get_supabase()
    batch_size = 200
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        sb.table("unemployment_data").upsert(
            batch, on_conflict="geo_code,source"
        ).execute()
        total += len(batch)
        logger.info("Upserted youth data batch %d–%d", i, i + len(batch))
    return total


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(geo_codes: list[str] | None = None, dry_run: bool = False) -> dict[str, int]:
    summary: dict[str, int] = {}

    if not geo_codes:
        geo_codes = _load_municipality_codes()
    if not geo_codes:
        # Fallback: just use province-level codes
        geo_codes = list(PROVINCE_GEO_CODES.keys())

    logger.info("=== Youth Explorer ingestion: %d geographies ===", len(geo_codes))

    records: list[dict] = []
    errors = 0
    for i, code in enumerate(geo_codes):
        logger.info("[%d/%d] Processing %s", i + 1, len(geo_codes), code)
        try:
            profile = fetch_profile(code)
            if profile:
                data = extract_youth_data(code, profile)
                records.append(data)
        except Exception:
            logger.exception("Error processing geo_code %s", code)
            errors += 1

        # Polite rate limiting
        if (i + 1) % 10 == 0:
            time.sleep(1)

    summary["unemployment_data"] = upsert_youth_data(records, dry_run=dry_run)
    summary["errors"] = errors

    logger.info("=== Youth Explorer ingestion complete ===")
    for k, v in summary.items():
        logger.info("  %s: %d", k, v)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Wazimap Youth Explorer data into Supabase")
    parser.add_argument("--geo-codes", nargs="*", help="Specific geo codes to fetch")
    parser.add_argument("--provinces-only", action="store_true", help="Only fetch province-level data")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to Supabase")
    args = parser.parse_args()

    codes = args.geo_codes
    if args.provinces_only:
        codes = list(PROVINCE_GEO_CODES.keys())

    run(geo_codes=codes, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
