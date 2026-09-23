"""Wazimap NG (OpenUp), the API behind Youth Explorer.

Profile 8  = Youth Explorer (Census 2011, 2011 boundaries). Youth detail.
Profile 14 = Open Wazi (Census 2022, 2021 demarcation). Services today.

child_data returns one indicator for every child of a geography in one call,
so a province call gives its districts and metros, and a district call gives
its local municipalities.
"""

from __future__ import annotations

from ..http import Fetcher

API = "https://api.wazimap.com/api/v1"
YOUTH_PROFILE = 8
CENSUS22_PROFILE = 14
PROVINCES = ["EC", "FS", "GT", "KZN", "LIM", "MP", "NC", "NW", "WC"]


def child_data(f: Fetcher, profile: int, geo: str, indicator: int) -> dict[str, list[dict]]:
    return f.get(f"{API}/profile/{profile}/geography/{geo}/indicator/{indicator}/child_data/?format=json")


def geography_tree(f: Fetcher, profile: int = CENSUS22_PROFILE) -> tuple[list[dict], dict[str, dict]]:
    """Walk country -> province -> district/metro -> local municipality.

    Returns (geographies, boundaries) where boundaries maps code -> GeoJSON
    geometry for every district, metro and local municipality.
    """
    geos: list[dict] = []
    shapes: dict[str, dict] = {}
    for prov in PROVINCES:
        d = f.get(f"{API}/all_details/profile/{profile}/geography/{prov}/?format=json")
        for feat in d["children"].get("districts and metros", {}).get("features", []):
            p = feat["properties"]
            geos.append({"code": p["code"], "name": p["name"], "parent": prov, "level": "district_or_metro"})
            shapes[p["code"]] = feat["geometry"]
    for g in [g for g in geos if g["code"].startswith("DC")]:
        d = f.get(f"{API}/all_details/profile/{profile}/geography/{g['code']}/?format=json")
        for feat in d["children"].get("municipality", {}).get("features", []):
            p = feat["properties"]
            geos.append({"code": p["code"], "name": p["name"], "parent": g["code"], "level": "local"})
            shapes[p["code"]] = feat["geometry"]
    return geos, shapes


def indicator_for_all(f: Fetcher, profile: int, indicator: int, districts: list[str]) -> dict[str, list[dict]]:
    """Rows for every metro, district and local municipality."""
    out: dict[str, list[dict]] = {}
    for geo in PROVINCES + districts:
        try:
            out.update(child_data(f, profile, geo, indicator))
        except LookupError:
            continue
    return out


def share(rows: list[dict], group: str, yes: set[str], filters: dict | None = None) -> float | None:
    """Fraction of the count where rows[group] is in `yes`, after filters."""
    filters = filters or {}
    num = den = 0.0
    for r in rows:
        if any(r.get(k) != v for k, v in filters.items()):
            continue
        c = float(r.get("count") or 0)
        den += c
        if r.get(group) in yes:
            num += c
    return num / den if den else None


def total(rows: list[dict], filters: dict | None = None) -> float:
    filters = filters or {}
    return sum(float(r.get("count") or 0) for r in rows if all(r.get(k) == v for k, v in filters.items()))


def categories(rows: list[dict], group: str) -> list[str]:
    return sorted({r.get(group) for r in rows if r.get(group) is not None})
