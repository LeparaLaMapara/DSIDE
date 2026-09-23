"""Put every government building project inside the municipality it sits in.

Vulekamali publishes provincial and national projects (schools, clinics,
housing, roads) with a point location but no municipality. A point-in-polygon
join against the Census 2022 boundaries fixes that.
"""

from __future__ import annotations

import json

import pandas as pd
from shapely import STRtree, points
from shapely.geometry import shape

STUCK_WORDS = ("hold", "terminated", "cancel", "stopped", "suspend")
DONE_WORDS = ("final completion", "practical completion", "completed", "close", "retention")


def locate(projects: pd.DataFrame, geos: pd.DataFrame) -> pd.DataFrame:
    """Add `code` (local or metro municipality) to each project with a valid point."""
    munis = geos[geos["level"].isin(["local", "district_or_metro"]) & ~geos["code"].str.startswith("DC")]
    shapes = [shape(json.loads(g)) for g in munis["geometry"]]
    tree = STRtree(shapes)
    p = projects.dropna(subset=["latitude", "longitude"]).copy()
    # South Africa lies roughly within these bounds; anything else is a typo in the source.
    p = p[p["latitude"].between(-35.5, -21.5) & p["longitude"].between(16, 33.5)]
    pt_idx, poly_idx = tree.query(points(p["longitude"].to_numpy(), p["latitude"].to_numpy()), predicate="within")
    codes = pd.Series(munis["code"].to_numpy()[poly_idx], index=p.index[pt_idx])
    p["code"] = codes[~codes.index.duplicated()]
    p["stage"] = p["status"].map(stage)
    return p


def stage(status: str) -> str:
    s = (status or "").lower()
    if any(w in s for w in STUCK_WORDS):
        return "Stopped or on hold"
    if any(w in s for w in DONE_WORDS):
        return "Finished"
    if "construction" in s or "site handed" in s:
        return "Being built"
    return "Planned"


def summary(located: pd.DataFrame) -> pd.DataFrame:
    g = located.dropna(subset=["code"]).groupby("code")
    out = pd.DataFrame({
        "projects": g.size(),
        "projects_value": g["estimated_total_project_cost"].sum(min_count=1),
        "projects_stuck": g["stage"].apply(lambda s: int((s == "Stopped or on hold").sum())),
        "projects_building": g["stage"].apply(lambda s: int((s == "Being built").sum())),
    })
    return out
