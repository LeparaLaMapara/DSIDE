"""The live layer: what is happening now, refreshed every few hours.

Three things, each labelled with where it came from:
  * Tshwane's open electricity faults (the city's own outage map), with how
    long each has been open, remembered between runs in engine/state/.
  * News headlines that name a place in a municipality (headline, outlet,
    date and link only; never generated text).
  * Eskom's national loadshedding stage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .sources import fresh_stats as fs
from .sources import places_live as pl

STATE = Path(__file__).resolve().parent.parent / "state"
KEEP_CLEARED_DAYS = 60


def faults(wards_df: pd.DataFrame, now: datetime | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open faults now, and repair times per ward over the last 60 days."""
    now = now or datetime.now(timezone.utc)
    STATE.mkdir(exist_ok=True)
    snap, log = STATE / "tshwane_faults.csv", STATE / "tshwane_faults_cleared.csv"
    prev = pd.read_csv(snap, dtype={"ward_id": str}) if snap.exists() else None
    current, cleared = pl.tshwane_faults(wards_df, prev, now)
    current.to_csv(snap, index=False)

    history = pd.read_csv(log, dtype={"ward_id": str}) if log.exists() else pd.DataFrame()
    if len(cleared):
        history = pd.concat([history, cleared], ignore_index=True)
    if len(history):
        at = pd.to_datetime(history["cleared_at"], utc=True, format="mixed")
        history = history[at >= now - timedelta(days=KEEP_CLEARED_DAYS)]
        history.to_csv(log, index=False)

    per_ward = current.groupby(["code", "ward_id"]).agg(open_faults=("fault_key", "size"),
                                                       oldest_open_hours=("open_hours", "max")).reset_index()
    # Name the worst-hit suburbs: one failed substation can produce hundreds of reports.
    tops = (current.assign(suburb=current["suburb"].str.title().str.replace(r"\s+X\d+$", "", regex=True))
            .groupby(["ward_id", "suburb"]).size().rename("n").reset_index()
            .sort_values("n", ascending=False).groupby("ward_id").head(2)
            .groupby("ward_id")["suburb"].apply(", ".join))
    per_ward["suburbs"] = per_ward["ward_id"].map(tops)
    if len(history):
        fixed = history.groupby("ward_id").agg(fixed_60d=("fault_key", "size"),
                                                median_repair_hours=("open_hours", "median")).reset_index()
        per_ward = per_ward.merge(fixed, on="ward_id", how="outer")
    return current, per_ward


def news(wards_df: pd.DataFrame, munis_df: pd.DataFrame, schools: pd.DataFrame) -> pd.DataFrame:
    gaz = pl.gazetteer(munis_df, pl.townships_from_schools(schools), wards_df=wards_df)
    items = pl.news(gaz, wards_df, munis_df)
    # Ward matches are not reliable enough yet; publish at municipality level only.
    # Only civic news (services, safety, money, jobs); sport, business and
    # celebrity stories that merely name a place are dropped.
    items = items[(items["event"] != "other") & (items["title"].str.split().str.len() >= 4)]
    items = items.dropna(subset=["code"]).drop(columns=["ward_id"], errors="ignore")
    items["published"] = pd.to_datetime(items["published"], utc=True, errors="coerce")
    items = items.sort_values("published", ascending=False)
    return items.groupby("code").head(12).reset_index(drop=True)


def status() -> pd.DataFrame:
    e = fs.eskom_status()
    e["checked_at"] = datetime.now(timezone.utc).isoformat(timespec="minutes")
    return e
