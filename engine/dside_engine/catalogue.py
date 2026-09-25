"""Every extra public source, by name, for the generic `dside_source` reader.

A pipeline task asks for one of these with:

    inputs:
      debtors: {format: dside_source, name: debtors}

Each entry takes `refresh` and returns a DataFrame. Sources that need the
ward shapes read them from the site data the main pipeline already wrote.
"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from .http import Fetcher
from .snapshots import guarded
from .sources import fresh_stats as fs
from .sources import places_live as pl
from .sources import treasury_extra as te
from .sources import wazimap_extra as wz


def _water(refresh: bool) -> pd.DataFrame:
    table, _report = fs.water_quality(refresh)
    return table


def _schools(refresh: bool) -> pd.DataFrame:
    return pl.schools(pl.load_wards(), refresh)


def _siu(refresh: bool) -> pd.DataFrame:
    return pl.siu_investigations(pl.load_munis(), refresh)


SOURCES: dict[str, Callable[[bool], pd.DataFrame]] = {
    # National Treasury, beyond the yearly totals
    "debtors": lambda r: te.debtors(Fetcher(r)),
    "creditors": lambda r: te.creditors(Fetcher(r)),
    "grants": lambda r: te.grants(Fetcher(r)),
    "year_to_date": lambda r: te.year_to_date(Fetcher(r)),
    "officials": lambda r: te.officials(Fetcher(r)),
    "cash": lambda r: te.cash(Fetcher(r)),
    # Elections and extra Census 2022 (Wazimap)
    "ward_councillors_2021": lambda r: wz.ward_councillors_2021(Fetcher(r)),
    "ward_results_2024": lambda r: wz.ward_results_2024(Fetcher(r)),
    "census_extras": lambda r: wz.census_extras(Fetcher(r)),
    "gcro": lambda r: wz.gcro_quality_of_life(Fetcher(r)),
    # Fresh statistics
    "jobs_2025": fs.spatial_tax,
    "jobs_series": fs.spatial_tax_jobs_series,
    "population_2026": fs.population_2026,
    "srd_grants": fs.srd_grants,
    "water_quality": _water,
    # Places
    "schools": _schools,
    "matric": pl.matric_results,
    "siu": _siu,
}


def load(name: str, refresh: bool = False) -> pd.DataFrame:
    """Fetch a named source; if its website fails, use its last good copy (see snapshots.py)."""
    if name not in SOURCES:
        raise KeyError(f"unknown source '{name}'; known: {sorted(SOURCES)}")
    return guarded(name, lambda: SOURCES[name](refresh), label=name)
