"""
Management command to pull municipal financial data from the National Treasury
Municipal Data API and store it locally as CSV and in the Django database.

Usage:
    python manage.py pull_data
    python manage.py pull_data --year 2023
    python manage.py pull_data --dry-run
"""

import logging
import os
import time
from datetime import datetime

import pandas as pd
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from balancesheet.models import BalSheet

logger = logging.getLogger(__name__)

API_BASE_URL = "https://municipaldata.treasury.gov.za/api"

# Endpoints for different cubes
ENDPOINTS = {
    "financial_position": "/cubes/financial_position/facts",
    "incexp": "/cubes/incexp/facts",
}

# Required fields that must be present in balance sheet data
REQUIRED_FIELDS_FINANCIAL = [
    "amount.sum",
    "financial_year_end.year",
    "demarcation.code",
    "demarcation.label",
]

MINIMUM_ROW_COUNT = 10


class Command(BaseCommand):
    """Pull municipal financial data from the National Treasury API."""

    help = (
        "Fetch municipal financial data from the National Treasury Municipal "
        "Data API and save to CSV and database."
    )

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Pull data for a specific financial year (e.g. 2023).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Validate data without saving to database or filesystem.",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximum number of retry attempts for failed API calls.",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=10000,
            help="Number of records to fetch per API page.",
        )

    def handle(self, *args, **options):
        """Execute the data pull pipeline."""
        year = options["year"]
        dry_run = options["dry_run"]
        max_retries = options["max_retries"]
        page_size = options["page_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN mode -- no data will be saved."))

        logger.info(
            "Starting data pull. year=%s dry_run=%s",
            year,
            dry_run,
        )

        # Ensure output directories exist
        raw_dir = self._ensure_data_dirs()

        # Pull balance sheet (financial position) data
        self.stdout.write("Pulling financial position data...")
        fin_df = self._fetch_cube(
            "financial_position",
            year=year,
            max_retries=max_retries,
            page_size=page_size,
        )

        if fin_df is not None:
            self._validate_dataframe(fin_df, REQUIRED_FIELDS_FINANCIAL, "financial_position")
            if not dry_run:
                self._save_csv(fin_df, raw_dir, "financial_position", year)
                self._save_to_database(fin_df)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Financial position: {len(fin_df)} rows fetched."
                )
            )
        else:
            self.stdout.write(self.style.ERROR("Financial position data pull failed."))

        # Pull income/expenditure data
        self.stdout.write("Pulling income/expenditure data...")
        incexp_df = self._fetch_cube(
            "incexp",
            year=year,
            max_retries=max_retries,
            page_size=page_size,
        )

        if incexp_df is not None:
            if not dry_run:
                self._save_csv(incexp_df, raw_dir, "incexp", year)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Income/expenditure: {len(incexp_df)} rows fetched."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("Income/expenditure data pull returned no data.")
            )

        logger.info("Data pull complete.")
        self.stdout.write(self.style.SUCCESS("Data pull complete."))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_data_dirs(self):
        """Create data directories if they do not exist and return raw path."""
        base = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )))
        # Go up to the repo root (above munimoneyfinal/)
        repo_root = os.path.dirname(os.path.dirname(base))
        raw_dir = os.path.join(repo_root, "data", "raw")
        processed_dir = os.path.join(repo_root, "data", "processed")

        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        logger.debug("Data directories ensured at %s", raw_dir)
        return raw_dir

    def _fetch_cube(self, cube_name, year=None, max_retries=3, page_size=10000):
        """
        Fetch all pages from a Municipal Data API cube.

        Returns a pandas DataFrame or None on total failure.
        """
        endpoint = ENDPOINTS.get(cube_name)
        if endpoint is None:
            logger.error("Unknown cube: %s", cube_name)
            return None

        url = f"{API_BASE_URL}{endpoint}"
        params = {"pagesize": page_size, "page": 0}

        if year is not None:
            params["cut"] = f"financial_year_end.year:{year}"

        all_records = []
        page = 0

        while True:
            params["page"] = page
            data = self._api_get(url, params, max_retries)
            if data is None:
                # Total failure after retries
                if page == 0:
                    return None
                break

            records = data if isinstance(data, list) else data.get("data", data.get("facts", []))
            if not records:
                break

            all_records.extend(records)
            logger.info(
                "Cube %s page %d: fetched %d records (total so far: %d)",
                cube_name,
                page,
                len(records),
                len(all_records),
            )

            # If we got fewer records than page size, we reached the end
            if len(records) < page_size:
                break

            page += 1

        if not all_records:
            return None

        df = pd.json_normalize(all_records)
        logger.info("Cube %s: total %d rows, %d columns", cube_name, len(df), len(df.columns))
        return df

    def _api_get(self, url, params, max_retries):
        """
        Make a GET request with retry logic.

        Returns parsed JSON or None.
        """
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug("GET %s params=%s attempt=%d", url, params, attempt)
                response = requests.get(url, params=params, timeout=120)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as exc:
                logger.warning(
                    "HTTP error on attempt %d/%d: %s", attempt, max_retries, exc
                )
            except requests.exceptions.ConnectionError as exc:
                logger.warning(
                    "Connection error on attempt %d/%d: %s", attempt, max_retries, exc
                )
            except requests.exceptions.Timeout as exc:
                logger.warning(
                    "Timeout on attempt %d/%d: %s", attempt, max_retries, exc
                )
            except requests.exceptions.RequestException as exc:
                logger.error("Unexpected request error: %s", exc)
                return None

            if attempt < max_retries:
                wait = 2 ** attempt
                logger.info("Retrying in %d seconds...", wait)
                time.sleep(wait)

        logger.error("All %d attempts failed for %s", max_retries, url)
        return None

    def _validate_dataframe(self, df, required_fields, cube_name):
        """
        Validate that a DataFrame has the expected columns and minimum rows.

        Raises CommandError on critical validation failures.
        """
        missing = [f for f in required_fields if f not in df.columns]
        if missing:
            msg = f"Cube {cube_name}: missing required fields: {missing}"
            logger.warning(msg)
            self.stdout.write(self.style.WARNING(msg))

        if len(df) < MINIMUM_ROW_COUNT:
            msg = (
                f"Cube {cube_name}: only {len(df)} rows returned "
                f"(minimum expected: {MINIMUM_ROW_COUNT})"
            )
            logger.warning(msg)
            self.stdout.write(self.style.WARNING(msg))

        # Report nulls
        null_counts = df.isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        if not cols_with_nulls.empty:
            logger.info(
                "Cube %s null counts:\n%s", cube_name, cols_with_nulls.to_string()
            )

    def _save_csv(self, df, raw_dir, cube_name, year):
        """Save DataFrame to a timestamped CSV in the raw data directory."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        year_suffix = f"_{year}" if year else ""
        filename = f"{cube_name}{year_suffix}_{timestamp}.csv"
        filepath = os.path.join(raw_dir, filename)

        df.to_csv(filepath, index=False)
        logger.info("Saved %d rows to %s", len(df), filepath)
        self.stdout.write(f"  Saved CSV: {filepath}")

    def _save_to_database(self, df):
        """
        Persist financial position data into the BalSheet Django model.

        This method is idempotent: it uses update_or_create keyed on
        mun_code + fin_year + label to avoid duplicates.
        """
        saved = 0
        skipped = 0

        # Map API column names to model fields (best-effort mapping)
        for _, row in df.iterrows():
            try:
                mun_code = str(
                    row.get("demarcation.code", row.get("municipality.demarcation_code", ""))
                )
                mun_name = str(
                    row.get("demarcation.label", row.get("municipality.name", ""))
                )
                amount = row.get("amount.sum", row.get("amount", 0))
                fin_year_raw = row.get(
                    "financial_year_end.year",
                    row.get("financial_year", None),
                )
                label = str(row.get("item.label", row.get("item", "")))
                account_type = str(
                    row.get("item.position_in_return_label", row.get("item_code", ""))
                )

                if not mun_code or fin_year_raw is None:
                    skipped += 1
                    continue

                # Convert year integer to a datetime
                try:
                    fin_year_int = int(float(fin_year_raw))
                    fin_year_dt = datetime(fin_year_int, 6, 30)
                except (ValueError, TypeError):
                    skipped += 1
                    continue

                BalSheet.objects.update_or_create(
                    mun_code=mun_code[:5],
                    fin_year=fin_year_dt,
                    label=label,
                    defaults={
                        "total_amount": float(amount) if amount else 0,
                        "account_type": account_type,
                        "mun_name": mun_name,
                        "province": str(row.get("demarcation.province_code", "")),
                        "latitude": str(row.get("municipality.latitude", "")),
                        "longitude": str(row.get("municipality.longitude", "")),
                    },
                )
                saved += 1
            except Exception as exc:
                logger.warning("Failed to save row: %s", exc)
                skipped += 1

        logger.info("Database save complete: %d saved, %d skipped", saved, skipped)
        self.stdout.write(f"  Database: {saved} saved, {skipped} skipped")
