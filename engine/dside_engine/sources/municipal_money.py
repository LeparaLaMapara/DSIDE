"""National Treasury Municipal Money.

Two endpoints:
  * municipaldata.treasury.gov.za/api/cubes/...  raw OLAP cubes (audit history)
  * municipalmoney.gov.za/api/municipality-profile/{code}/  Treasury's own
    computed indicators (cash coverage, collection rate, etc.) per municipality
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from ..http import Fetcher

CUBES = "https://municipaldata.treasury.gov.za/api/cubes"
PROFILE = "https://municipalmoney.gov.za/api/municipality-profile/{code}/"


def municipalities(f: Fetcher) -> list[dict]:
    """Every municipality Treasury knows, including disestablished ones."""
    rows, page = [], 1
    while True:
        data = f.get(f"{CUBES}/municipalities/facts?pagesize=500&page={page}")
        rows += data["data"]
        if len(rows) >= data["total_fact_count"] or not data["data"]:
            return rows
        page += 1


def audit_history(f: Fetcher) -> list[dict]:
    """One row per municipality per financial year with the Auditor-General opinion."""
    rows, page = [], 1
    while True:
        data = f.get(f"{CUBES}/audit_opinions/facts?pagesize=5000&page={page}")
        rows += data["data"]
        if len(rows) >= data["total_fact_count"] or not data["data"]:
            return rows
        page += 1


def cube_last_updated(f: Fetcher, cube: str) -> str | None:
    return f.get(f"{CUBES}/{cube}/model")["model"].get("last_updated")


def profiles(f: Fetcher, codes: list[str], workers: int = 6) -> dict[str, dict]:
    def one(code: str):
        try:
            return code, f.get(PROFILE.format(code=code))
        except LookupError:
            return code, None

    with ThreadPoolExecutor(workers) as pool:
        return {c: p for c, p in pool.map(one, codes) if p is not None}


def aggregate(f: Fetcher, cube: str, cut: str, drilldown: str, page_size: int = 10000) -> list[dict]:
    """All cells of a cube aggregate, following pagination."""
    cells, page = [], 1
    while True:
        data = f.get(
            f"{CUBES}/{cube}/aggregate?aggregates=amount.sum&cut={cut}"
            f"&drilldown={drilldown}&pagesize={page_size}&page={page}"
        )
        batch = data.get("cells", [])
        cells += batch
        if len(batch) < page_size or len(cells) >= data.get("total_cell_count", 0):
            return cells
        page += 1


def yearly(f: Fetcher, cube: str, years: list[int], drilldown: str, extra_cut: str = "") -> list[dict]:
    """Annual (not monthly) cells for every municipality, for each year."""
    out: list[dict] = []
    for y in years:
        cut = f"financial_year_end.year:{y}|period_length.length:year" + (f"|{extra_cut}" if extra_cut else "")
        for cell in aggregate(f, cube, cut, f"demarcation.code|{drilldown}"):
            cell["year"] = y
            out.append(cell)
    return out


def uifw(f: Fetcher) -> list[dict]:
    return aggregate(f, "uifwexp", "financial_year_end.year:2019;2020;2021;2022;2023;2024;2025",
                     "demarcation.code|financial_year_end.year|item.label")
