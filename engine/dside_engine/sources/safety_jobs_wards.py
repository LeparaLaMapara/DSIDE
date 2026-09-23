"""Crime (SAPS), jobs (Stats SA QLFS) and wards (Municipal Demarcation Board).

SAPS publishes one spreadsheet per quarter; each holds the same quarter for
the last five years, per police station. Stations are linked to
municipalities with Adrian Frith's cleaned precinct table (Census 2022
population per precinct, precinct to municipality code), which is built from
Stats SA's police district boundaries.
"""

from __future__ import annotations

import io
import re
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from ..http import CACHE_DIR, USER_AGENT

SAPS_PAGE = "https://www.saps.gov.za/services/crimestats.php"
SAPS_BASE = "https://www.saps.gov.za/services/"
PRECINCTS = "https://raw.githubusercontent.com/afrith/crime-stats/main/police_stations.csv"
QLFS = "https://www.statssa.gov.za/publications/P0211/QLFS%20Trends%202008-{year}Q{q}.xlsx"
WARDS = ("https://services7.arcgis.com/oeoyTUJC8HEeYsRB/arcgis/rest/services/"
         "WardProfile2021_gdb/FeatureServer/0/query")

CRIMES = {
    "Murder": "murders",
    "Sexual offences": "sexual_offences",
    "Rape": "rapes",
    "Drug-related crime": "drug_crimes",
    "Burglary at residential premises": "house_burglaries",
    "Contact crime (Crimes against the person)": "contact_crimes",
    "Robbery at residential premises": "house_robberies",
}

METROS = {"City of cape Town": "CPT", "Buffalo City": "BUF", "Nelson mandela Bay": "NMA", "Mangaung": "MAN",
          "eThekwini": "ETH", "City of Johannesburg": "JHB", "City of Tshwane": "TSH", "Ekurhuleni": "EKU"}
PROVINCE_CODES = {"Western Cape": "WC", "Eastern Cape": "EC", "Northern Cape": "NC", "Free State": "FS",
                  "KwaZulu Natal": "KZN", "KwaZulu-Natal": "KZN", "North West": "NW", "Gauteng": "GT",
                  "Mpumalanga": "MP", "Limpopo": "LIM", "South Africa": "ZA"}


def _download(url: str, refresh: bool, verify: bool = True) -> bytes:
    path = CACHE_DIR / re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[1])[-150:]
    if path.exists() and not refresh:
        return path.read_bytes()
    with httpx.Client(timeout=300, follow_redirects=True, verify=verify, headers={"User-Agent": USER_AGENT}) as c:
        r = c.get(url)
        r.raise_for_status()
    CACHE_DIR.mkdir(exist_ok=True)
    path.write_bytes(r.content)
    return r.content


def latest_saps_file(refresh: bool) -> str:
    # SAPS serves an incomplete certificate chain, so verification is relaxed
    # for this one government host only; the file is public statistics.
    html = _download(SAPS_PAGE, refresh=True, verify=False).decode("utf-8", "ignore")
    links = re.findall(r'href="(downloads/\d{4}/\d{4}-\d{4}_-_\w+_Quarter_WEB\.xls[xm]?)"', html)
    if not links:
        raise RuntimeError("no quarterly crime file found on the SAPS page")
    order = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4}
    return SAPS_BASE + max(links, key=lambda l: (re.search(r"(\d{4})-\d{4}", l).group(1),
                                                    order[re.search(r"_(\w+)_Quarter", l).group(1)]))


def crime_by_station(refresh: bool = False) -> tuple[pd.DataFrame, str]:
    url = latest_saps_file(refresh)
    sheet = pd.read_excel(io.BytesIO(_download(url, refresh, verify=False)), sheet_name="RAW Data",
                          engine="openpyxl", header=None)
    header = sheet.index[sheet.eq("Comp level").any(axis=1)][0]  # a few title rows sit above it
    raw = sheet.iloc[header + 1:].set_axis([str(c).strip() for c in sheet.iloc[header]], axis=1)
    raw = raw[(raw["Comp level"] == "Station") & raw["Crime_Category"].isin(CRIMES)]
    quarters = [c for c in raw.columns if isinstance(c, str) and " to " in c]
    long = raw.melt(id_vars=["Station", "Crime_Category"], value_vars=quarters, var_name="period", value_name="count")
    long["crime"] = long["Crime_Category"].map(CRIMES)
    long["year"] = long["period"].str.extract(r"(\d{4})\s*$").astype(int)
    long["period"] = long["period"].str.replace(r"\s+", " ", regex=True).str.strip()
    long = long.rename(columns={"Station": "station"})[["station", "crime", "year", "period", "count"]]
    long["count"] = pd.to_numeric(long["count"], errors="coerce").fillna(0)
    return long, url


# SAPS spreadsheet name -> name in the precinct table, where they differ.
STATION_ALIASES = {
    "Balfour": "Balfour EC", "Balfour TVL": "Balfour MP", "Heidelberg (Gp)": "Heidelberg GP",
    "Heidelberg(C)": "Heidelberg WC", "Middelburg Mpumalang": "Middelburg MP", "Middelburg(EC)": "Middelburg EC",
    "OR Tambo Intern Airp": "OR Tambo Intl Airport", "Richmond(C)": "Richmond NC", "Richmond-Kzn": "Richmond KZN",
    "JHB Central": "Johannesburg Central", "Hilton-Kzn": "Hilton", "Mayville-Kzn": "Mayville",
    "Morgenzon Transvaal": "Morgenzon",
}


def _norm(name: str) -> str:
    name = STATION_ALIASES.get(str(name).strip(), str(name).strip())
    return re.sub(r"[^a-z0-9]", "", name.lower())


def precincts(refresh: bool = False) -> pd.DataFrame:
    p = pd.read_csv(io.BytesIO(_download(PRECINCTS, refresh)))
    p["key"] = p["name"].map(_norm)
    return p.rename(columns={"code": "precinct_code", "name": "station"})


def link_stations(crime: pd.DataFrame, prec: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    crime = crime.copy()
    crime["key"] = crime["station"].map(_norm)
    lookup = prec.drop_duplicates("key").set_index("key")
    crime["muni_code"] = crime["key"].map(lookup["muni_code"])
    crime["precinct_code"] = crime["key"].map(lookup["precinct_code"])
    crime["precinct_population"] = crime["key"].map(lookup["population"])
    unmatched = sorted(crime.loc[crime["muni_code"].isna(), "station"].unique())
    return crime.drop(columns="key"), unmatched


FALLBACK = Path(__file__).resolve().parents[2] / "fallback"


def qlfs(refresh: bool = False) -> tuple[pd.DataFrame, str]:
    """Latest Stats SA labour force trends: unemployment by province and metro, and by age.

    Stats SA's server is often slow or blocks automated requests. When no
    file can be fetched, the last successfully parsed copy in fallback/ is
    used and the returned source says so, so the site can show its date.
    """
    today = date.today()
    for year in range(today.year, today.year - 2, -1):
        for q in (4, 3, 2, 1):
            url = QLFS.format(year=year, q=q)
            try:
                content = _download(url, refresh)
            except httpx.HTTPError:
                continue
            if not content.startswith(b"PK"):  # Stats SA answers missing files with an HTML page
                (CACHE_DIR / re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[1])[-150:]).unlink(missing_ok=True)
                continue
            table = _parse_qlfs(content)
            FALLBACK.mkdir(exist_ok=True)
            table.assign(source=url).to_csv(FALLBACK / "qlfs.csv", index=False)
            return table, url
    saved = pd.read_csv(FALLBACK / "qlfs.csv")
    return saved.drop(columns="source"), f"{saved['source'].iloc[0]} (last saved copy; Stats SA was unreachable)"


def _parse_qlfs(content: bytes) -> pd.DataFrame:
    rows: list[dict] = []
    t = pd.read_excel(io.BytesIO(content), sheet_name="Table 2.3", header=None)
    periods = list(t.iloc[1, 1:])
    area = None
    for _, r in t.iterrows():
        label = str(r[0]).strip() if pd.notna(r[0]) else ""
        if label in PROVINCE_CODES:
            area = PROVINCE_CODES[label]
        elif " - " in label:
            place = label.split(" - ", 1)[1]
            area = METROS.get(place)  # non-metro remainders are skipped
        elif area and label.startswith(("LU1", "LU3")):
            key = "unemployment" if label.startswith("LU1") else "unemployment_expanded"
            for p, v in zip(periods, r[1:]):
                if isinstance(p, str) and pd.notna(pd.to_numeric(v, errors="coerce")):
                    rows.append({"area": area, "measure": key, "period": p, "value": float(v)})
    t = pd.read_excel(io.BytesIO(content), sheet_name="Table2.2", header=None)
    periods = list(t.iloc[1, 1:])
    group = None
    for _, r in t.iterrows():
        label = str(r[0]).strip() if pd.notna(r[0]) else ""
        m = re.match(r"^(\d\d-\d\d) years$", label)
        if m:
            group = m.group(1)
        elif group and label.startswith(("Labour Force", "Unemployed")):
            key = "labour_force" if label.startswith("Labour") else "unemployed"
            for p, v in zip(periods, r[1:]):
                if isinstance(p, str) and pd.notna(pd.to_numeric(v, errors="coerce")):
                    rows.append({"area": f"ZA:{group}", "measure": key, "period": p, "value": float(v)})
    return pd.DataFrame(rows)


def wards(codes: list[str], refresh: bool = False, offset: float = 0.0004) -> pd.DataFrame:
    """Every ward with its Census 2011 profile (re-mapped by the MDB to 2021 wards) and a simplified shape."""
    import json

    from ..http import Fetcher

    f = Fetcher(refresh=refresh)
    rows: list[dict] = []
    for code in codes:
        url = (f"{WARDS}?where=CAT_B%3D%27{code}%27&outFields=*&returnGeometry=true&outSR=4326"
               f"&maxAllowableOffset={offset}&geometryPrecision=4&f=geojson")
        try:
            data = f.get(url)
        except (LookupError, RuntimeError):
            continue
        for feat in data.get("features", []):
            props = dict(feat["properties"])
            props["geometry"] = json.dumps(feat["geometry"])
            rows.append(props)
    return pd.DataFrame(rows)


def tshwane_councillors(refresh: bool = False) -> pd.DataFrame:
    """Ward councillors for the pilot city, from the City of Tshwane's own page."""
    # Like SAPS, the city serves an incomplete certificate chain; this is its public councillor list.
    html = _download("https://www.tshwane.gov.za/?page_id=17228", refresh, verify=False).decode("utf-8", "ignore")
    tables = pd.read_html(io.StringIO(html))
    t = max(tables, key=len)
    t.columns = [str(c).strip() for c in t.columns]
    t = t[t["Designation"].astype(str).str.contains("Ward", case=False)]
    return pd.DataFrame({
        "muni_code": "TSH",
        "ward_no": pd.to_numeric(t["Ward / PR"], errors="coerce"),
        "councillor": (t["Name"].astype(str).str.title() + " " + t["Surname"].astype(str).str.title()),
        "party": t["Party"].astype(str).str.title(),
        "phone": t["Contact no."].astype(str),
    }).dropna(subset=["ward_no"])


__all__ = ["crime_by_station", "precincts", "link_stations", "qlfs", "wards", "tshwane_councillors", "Path"]
