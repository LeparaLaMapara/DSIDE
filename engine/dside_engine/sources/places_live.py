"""Place-level live sources: schools, matric results, Tshwane power faults, local news and SIU probes.

Every source here is free and needs no login. Each function returns a tidy
pandas DataFrame and, where a location is known, puts it inside OUR
boundaries with a point-in-polygon join: `code` is the Treasury demarcation
code of the local or metro municipality and `ward_id` is the 8-digit
Municipal Demarcation Board ward id (a string). Ids printed in the sources
themselves (EMIS ward ids, GeoNames admin codes) are never trusted, because
they are often stale.

No personal data is kept: school principal names, phone numbers and emails
are dropped on read, the fault map carries suburbs and streets only, and news
rows keep a headline and link, never the article body.

Each returned frame carries a short `attrs["report"]` dict with counts and
coverage, so a build can log what it got.

Run `python -m dside_engine.sources.places_live` for a full live run with a
report of counts, coverage, runtime and memory.
"""

from __future__ import annotations

import html as htmllib
import io
import json
import re
import unicodedata
import zipfile
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha1
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import numpy as np
import pandas as pd

from ..http import USER_AGENT, client
from .safety_jobs_wards import _download

EMIS_PAGE = "https://www.education.gov.za/Programmes/EMIS/EMISDownloads.aspx"
REPORTS_PAGE = "https://www.education.gov.za/Resources/Reports.aspx"
DBE_BASE = "https://www.education.gov.za"
FAULT_MAP = "https://powerfailure.tshwane.gov.za/Tshwanesms/Map.aspx"
GEONAMES_ZA = "https://download.geonames.org/export/dump/ZA.zip"
SIU_API = ("https://www.siu.org.za/wp-json/wp/v2/proclamation?categories={cat}&per_page=100&page={page}"
           "&_fields=id,date,link,title,categories")
SIU_LOCAL_GOV, SIU_ONGOING, SIU_COMPLETED = 28, 36, 31

REPO = Path(__file__).resolve().parents[3]
FALLBACK = Path(__file__).resolve().parents[2] / "fallback"

# Hosts whose certificate chain fails verification from some machines. Each is
# public data, so a failed strict handshake is retried without verification for
# these hosts only. Every other host is always verified.
#   education.gov.za: DBE serves an incomplete chain to some TLS stacks.
#   tshwane.gov.za:   the city's main site serves an incomplete chain.
#   siu.org.za:       the SIU site's intermediate certificate is not sent.
RELAXED_TLS_HOSTS = ("education.gov.za", "tshwane.gov.za", "siu.org.za")

FEEDS: dict[str, str] = {
    "News24": "https://feeds.capi24.com/v1/Search/articles/news24/TopStories/rss",
    "IOL": "https://www.iol.co.za/rss/iol/news/",
    "The Citizen": "https://www.citizen.co.za/feed/",
    "SABC News": "https://www.sabcnews.com/sabcnews/feed/",
    "eNCA": "https://www.enca.com/rss.xml",
    "SAnews": "https://www.sanews.gov.za/rss.xml",
    "gov.za": "https://www.gov.za/rss.xml",
    "Daily Maverick": "https://www.dailymaverick.co.za/dmrss/",
    "GroundUp": "https://groundup.org.za/sitenews/rss/",
    "Rekord": "https://www.citizen.co.za/rekord/feed/",
    "Lowvelder": "https://www.citizen.co.za/lowvelder/feed/",
    "Moneyweb": "https://www.moneyweb.co.za/feed/",
    "BusinessTech": "https://businesstech.co.za/news/feed/",
    "City of Tshwane": "https://www.tshwane.gov.za/?feed=rss2",
    "Johannesburg Water": "https://www.johannesburgwater.co.za/feed/",
    "Eskom": "https://www.eskom.co.za/feed/",
}


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------

def _relaxed(url: str) -> bool:
    host = urlsplit(url).hostname or ""
    return any(host == h or host.endswith("." + h) for h in RELAXED_TLS_HOSTS)


def _fetch(url: str, refresh: bool = False, cache: bool = True, timeout: float = 60.0) -> bytes:
    """Download a URL (cached on disk unless cache=False), verifying TLS except for RELAXED_TLS_HOSTS."""
    if cache:
        try:
            return _download(url, refresh)
        except httpx.ConnectError:
            if not _relaxed(url):
                raise
            return _download(url, refresh, verify=False)
    for verify in (True, False):
        try:
            with client(timeout, verify) as c:
                r = c.get(url)
                r.raise_for_status()
                return r.content
        except httpx.ConnectError:
            if not verify or not _relaxed(url):
                raise
    raise RuntimeError("unreachable")


def _page_text_with_links(page: str) -> str:
    """Flatten an HTML page to text, keeping each link target inline as [[url]]."""
    out = re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I)
    out = re.sub(r'<a [^>]*href="([^"]*)"[^>]*>', lambda m: " [[" + htmllib.unescape(m.group(1)) + "]] ", out)
    out = htmllib.unescape(re.sub(r"<[^>]+>", " ", out))
    return re.sub(r"\s+", " ", out.replace("\xa0", " "))


def load_wards(path: Path | None = None) -> pd.DataFrame:
    """Read web/data/wards.json as ward_id, ward_no, code, geometry (GeoJSON string)."""
    rows = json.loads(Path(path or REPO / "web" / "data" / "wards.json").read_text(encoding="utf-8"))
    df = pd.DataFrame([{k: r[k] for k in ("ward_id", "ward_no", "code", "geometry")} for r in rows])
    df["ward_id"] = df["ward_id"].astype(str).str.zfill(8)
    return df


def load_munis(path: Path | None = None) -> pd.DataFrame:
    """Read web/data/boundaries.json as code, name, level, parent, geometry."""
    rows = json.loads(Path(path or REPO / "web" / "data" / "boundaries.json").read_text(encoding="utf-8"))
    return pd.DataFrame(rows)


class WardLocator:
    """Point-in-polygon lookup from (lat, lng) to our municipality code and ward id.

    Ward shapes are simplified, so a point can fall in a sliver between two
    wards. Points that hit no ward take the nearest ward within `snap_km`.
    """

    def __init__(self, wards_df: pd.DataFrame, snap_km: float = 1.0):
        from shapely import STRtree
        from shapely.geometry import shape

        geoms = [shape(json.loads(g)) if isinstance(g, str) else shape(g) for g in wards_df["geometry"]]
        self.tree = STRtree(geoms)
        self.ward_id = wards_df["ward_id"].astype(str).str.zfill(8).to_numpy()
        self.code = wards_df["code"].astype(str).to_numpy()
        self.snap = snap_km / 111.0

    def locate(self, lat, lng) -> tuple[np.ndarray, np.ndarray]:
        """Return arrays (code, ward_id), None where a point is missing or outside every ward."""
        from shapely import points

        lat = np.asarray(lat, dtype=float)
        lng = np.asarray(lng, dtype=float)
        codes = np.full(lat.shape, None, dtype=object)
        wards = np.full(lat.shape, None, dtype=object)
        ok = np.flatnonzero(~(np.isnan(lat) | np.isnan(lng)))
        if not len(ok):
            return codes, wards
        pts = points(lng[ok], lat[ok])
        pi, gi = self.tree.query(pts, predicate="within")
        hit = np.full(len(ok), -1)
        first = ~pd.Series(pi).duplicated().to_numpy()
        hit[pi[first]] = gi[first]
        miss = np.flatnonzero(hit < 0)
        if len(miss):
            pi2, gi2 = self.tree.query_nearest(pts[miss], max_distance=self.snap)
            first = ~pd.Series(pi2).duplicated().to_numpy()
            hit[miss[pi2[first]]] = gi2[first]
        found = hit >= 0
        codes[ok[found]] = self.code[hit[found]]
        wards[ok[found]] = self.ward_id[hit[found]]
        return codes, wards


def _coverage(df: pd.DataFrame, col: str) -> float:
    return round(float(df[col].notna().mean()) if len(df) else 0.0, 4)


# --------------------------------------------------------------------------
# 1. Schools (DBE EMIS master list)
# --------------------------------------------------------------------------

def _undecimal(v: float) -> float:
    """Restore a coordinate whose decimal point was stripped: -287158 means -28.7158."""
    if pd.isna(v) or abs(v) <= 90:
        return v
    digits = str(int(abs(v)))
    return float(np.sign(v)) * float(digits[:2] + "." + digits[2:])


def fix_coords(lat: pd.Series, lng: pd.Series) -> tuple[pd.Series, pd.Series, dict]:
    """Clean school coordinates for South Africa (lat -35..-22, lng 16..33).

    Repairs stripped decimals, swapped columns and a missing minus sign on the
    latitude, then blanks anything still outside the country's box.
    """
    lat = pd.to_numeric(lat, errors="coerce").map(_undecimal).astype(float)
    lng = pd.to_numeric(lng, errors="coerce").map(_undecimal).astype(float)

    def in_lat(s):
        return s.between(-35, -22)

    def in_lng(s):
        return s.between(16, 33)

    swap = ~(in_lat(lat) & in_lng(lng)) & in_lat(lng) & in_lng(lat)
    lat, lng = lat.where(~swap, lng), lng.where(~swap, lat)
    sign = ~in_lat(lat) & (-lat).between(-35, -22) & in_lng(lng)
    lat = lat.where(~sign, -lat)
    bad = lat.notna() & ~(in_lat(lat) & in_lng(lng))
    lat, lng = lat.mask(bad), lng.mask(bad)
    return lat, lng, {"swapped": int(swap.sum()), "sign_fixed": int(sign.sum()), "out_of_country": int(bad.sum())}


def _emis_links(page: str) -> tuple[str, dict[str, str]]:
    """Find the latest 'Quarter N of YYYY' block on the EMIS page and its file link per region."""
    text = _page_text_with_links(page)
    heads = [(int(m.group(2)), int(m.group(1)), m.start(), m.end())
             for m in re.finditer(r"Quarter (\d) of (\d{4})", text)]
    if not heads:
        raise RuntimeError("no quarterly school master list on the EMIS page")
    year, q, _, end = max(heads)
    nxt = min([s for (_, _, s, _) in heads if s > end] or [len(text)])
    links: dict[str, str] = {}
    for m in re.finditer(r"\[\[(/LinkClick[^\]]+)\]\]\s*([A-Za-z][A-Za-z \-]*?)\s*(?=\[\[|\d|$)", text[end:nxt]):
        links.setdefault(m.group(2).strip(), DBE_BASE + m.group(1))
    return f"Q{q} {year}", links


SCHOOL_COLS = ["NatEmis", "DataYear", "Province", "Official_Institution_Name", "Status", "Sector", "Phase_PED",
               "GIS_Long", "GIS_Lat", "Ward_ID", "Suburb", "Township_Village", "Quintile", "NoFeeSchool"]


def _read_emis_xlsx(content: bytes) -> pd.DataFrame:
    """Stream an EMIS workbook, keeping only the columns we use (drops names, phones, emails)."""
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows)]
    wanted = SCHOOL_COLS + [h for h in header if re.fullmatch(r"(Learners|Educators)\d{4}", h)]
    idx = [header.index(c) for c in wanted if c in header]
    names = [header[i] for i in idx]
    data = [[r[i] for i in idx] for r in rows if r and r[idx[0]] is not None]
    wb.close()
    return pd.DataFrame(data, columns=names)


def schools(wards_df: pd.DataFrame, refresh: bool = False) -> pd.DataFrame:
    """Every school in the DBE EMIS master list, placed in our municipality and ward.

    Columns: emis, name, province, status, sector (public/independent), no_fee,
    quintile (1-5, NA if unknown), phase, learners, educators, suburb, lat, lng,
    code, ward_id, emis_ward_id (as printed by EMIS, for comparison only),
    data_quarter, source.
    """
    quarter, links = _emis_links(_fetch(EMIS_PAGE, refresh).decode("utf-8", "ignore"))
    nat_url, nc_url = links["National"], links.get("Northern Cape")
    df = _read_emis_xlsx(_fetch(nat_url, refresh))
    learners = next((c for c in df.columns if c.startswith("Learners")), None)
    educators = next((c for c in df.columns if c.startswith("Educators")), None)

    df["emis"] = df["NatEmis"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    lat, lng, fixes = fix_coords(df["GIS_Lat"], df["GIS_Long"])
    df["lat"], df["lng"] = lat, lng

    nc_filled = 0
    if nc_url:
        nc = _read_emis_xlsx(_fetch(nc_url, refresh))
        nlat, nlng, _ = fix_coords(nc["GIS_Lat"], nc["GIS_Long"])
        nc_pts = pd.DataFrame({"lat": nlat.to_numpy(), "lng": nlng.to_numpy()},
                              index=nc["NatEmis"].astype(str).str.replace(r"\.0$", "", regex=True).str.strip())
        nc_pts = nc_pts[~nc_pts.index.duplicated()].dropna()
        need = df["lat"].isna() & df["emis"].isin(nc_pts.index)
        df.loc[need, "lat"] = df.loc[need, "emis"].map(nc_pts["lat"])
        df.loc[need, "lng"] = df.loc[need, "emis"].map(nc_pts["lng"])
        nc_filled = int(need.sum())

    quint = pd.to_numeric(df["Quintile"].astype(str).str.extract(r"Q?([1-5])$")[0], errors="coerce").astype("Int64")
    sector = df["Sector"].astype(str).str.strip().str.lower()
    fee = df["NoFeeSchool"].astype(str).str.strip().str.lower()
    no_fee = (sector == "public") & (fee.isin(["no fee", "yes"]) | quint.isin([1, 2, 3]).fillna(False))

    out = pd.DataFrame({
        "emis": df["emis"],
        "name": df["Official_Institution_Name"].astype(str).str.strip(),
        "province": df["Province"],
        "status": df["Status"].astype(str).str.upper(),
        "sector": sector,
        "no_fee": no_fee.astype(bool),
        "quintile": quint,
        "phase": df["Phase_PED"].astype(str).str.lower().str.replace(" school", "", regex=False),
        "learners": pd.to_numeric(df[learners], errors="coerce").astype("Int64") if learners else pd.NA,
        "educators": pd.to_numeric(df[educators], errors="coerce").astype("Int64") if educators else pd.NA,
        "suburb": df["Suburb"].astype(str).str.strip().replace({"None": None, "nan": None, "99": None}),
        "lat": df["lat"].round(6),
        "lng": df["lng"].round(6),
        "emis_ward_id": df["Ward_ID"].astype(str).str.replace(r"\.0$", "", regex=True),
    })
    loc = WardLocator(wards_df)
    out["code"], out["ward_id"] = loc.locate(out["lat"], out["lng"])
    out["data_quarter"] = quarter
    out["source"] = nat_url
    out = out.reset_index(drop=True)
    has_pt = out["lat"].notna()
    out.attrs["report"] = {
        "schools": len(out), "data_quarter": quarter, "with_coords": int(has_pt.sum()),
        "placed_in_ward": int(out["ward_id"].notna().sum()), "ward_coverage": _coverage(out, "ward_id"),
        "nc_coords_filled_from_provincial_file": nc_filled, **fixes,
        # EMIS prints either an 8-digit ward id or a bare ward number; compare only the ids
        "emis_ward_agrees": round(float((out["emis_ward_id"] == out["ward_id"])[
            out["ward_id"].notna() & out["emis_ward_id"].str.fullmatch(r"\d{8}")].mean()), 4),
    }
    return out


# --------------------------------------------------------------------------
# 2. Matric results (NSC School Performance Report)
# --------------------------------------------------------------------------

def _report_link(page: str, year: int | None) -> tuple[int, str]:
    text = _page_text_with_links(page)
    found = [(int(m.group(2)), DBE_BASE + m.group(1)) for m in
             re.finditer(r"\[\[(/LinkClick[^\]]+?)\]\]\s*NSC Examinations (\d{4}): School Performance Report", text)]
    if year:
        found = [f for f in found if f[0] == year]
    if not found:
        raise RuntimeError("no NSC School Performance Report link found")
    y, url = max(found)
    return y, url + ("&forcedownload=true" if "forcedownload" not in url else "")


LABELS = {"dessergorP", "etorW", "deveihcA", "%"}  # rotated column headers read backwards


def _parse_performance_page(words: list[dict], cols: list[float] | None) -> tuple[list[dict], list[float] | None]:
    """Parse one page of the per-school table from pdfplumber words (with x/y positions)."""
    years = sorted((w for w in words if re.fullmatch(r"20\d\d", w["text"]) and w["top"] < 130 and w["x0"] > 250),
                   key=lambda w: w["x0"])
    if len(years) != 3:
        return [], cols
    xs = sorted({round((w["x0"] + w["x1"]) / 2) for w in words
                 if w["text"] in LABELS and w["x0"] > 290 and w["top"] < 130})
    merged: list[float] = []
    for x in xs:
        if not merged or x - merged[-1] > 4:
            merged.append(x)
    if len(merged) == 12:
        cols = merged
    if not cols:
        return [], cols
    yrs = [int(w["text"]) for w in years]
    anchors = [w for w in words if re.fullmatch(r"\d{8,9}", w["text"]) and w["x0"] < 95 and w["top"] > 100]
    rows = []
    for a in anchors:
        near = [w for w in words if abs(w["top"] - a["top"]) < 10 and w is not a]
        # The row that owns a word is the anchor closest to it vertically.
        near = [w for w in near if min(anchors, key=lambda b: abs(b["top"] - w["top"])) is a]
        centre = next((w["text"] for w in near if w["x0"] < 130 and re.fullmatch(r"\d{5,8}", w["text"])), None)
        name = " ".join(w["text"] for w in sorted(near, key=lambda w: (round(w["top"]), w["x0"]))
                        if 125 < w["x0"] < 292)
        quint = next((w["text"] for w in near if 290 < w["x0"] < cols[0] - 10), None)
        cells: dict[int, str] = {}
        for w in near:
            cx = (w["x0"] + w["x1"]) / 2
            if w["x0"] < cols[0] - 10:
                continue
            i = int(np.argmin([abs(cx - c) for c in cols]))
            if abs(cx - cols[i]) <= 9:
                cells[i] = w["text"]
        for b, yr in enumerate(yrs):
            vals = [cells.get(4 * b + k) for k in range(4)]
            if vals[1] is None:
                continue
            rows.append({"emis": a["text"], "centre_no": centre, "name": name,
                         "quintile": pd.to_numeric(quint, errors="coerce"), "year": yr,
                         "progressed": pd.to_numeric(vals[0], errors="coerce"),
                         "wrote": pd.to_numeric(vals[1], errors="coerce"),
                         "passed": pd.to_numeric(vals[2], errors="coerce"),
                         "pass_rate": pd.to_numeric(vals[3], errors="coerce")})
    return rows, cols


def matric_results(refresh: bool = False, year: int | None = None) -> pd.DataFrame:
    """Matric (NSC) results per school for the three years in the latest School Performance Report.

    Columns: emis, centre_no, name, quintile, year, progressed, wrote, passed,
    pass_rate (percent, as printed), report_year, source. Join to schools() on emis.
    """
    import pdfplumber

    y, url = _report_link(_fetch(REPORTS_PAGE, refresh).decode("utf-8", "ignore"), year)
    content = _fetch(url, refresh)
    rows: list[dict] = []
    cols = None
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            got, cols = _parse_performance_page(page.extract_words(), cols)
            rows += got
            page.flush_cache()
    out = pd.DataFrame(rows)
    out["emis"] = out["emis"].astype(str)
    for c in ("progressed", "wrote", "passed", "quintile"):
        out[c] = out[c].astype("Int64")
    out = out.drop_duplicates(["emis", "year"]).reset_index(drop=True)
    out["report_year"] = y
    out["source"] = url
    latest = out[out["year"] == y]
    out.attrs["report"] = {
        "rows": len(out), "schools": int(out["emis"].nunique()), "schools_in_report_year": len(latest),
        "report_year": y, "wrote_in_report_year": int(latest["wrote"].sum()),
        "passed_in_report_year": int(latest["passed"].sum()),
    }
    return out


# --------------------------------------------------------------------------
# 3. City of Tshwane power faults
# --------------------------------------------------------------------------

def parse_fault_markers(page: str) -> pd.DataFrame:
    """Read window.OUTAGE_MARKERS from the fault map page: lat, lng, suburb, street."""
    m = re.search(r"OUTAGE_MARKERS\s*=\s*(\[.*?\])\s*;", page, re.S)
    if not m:
        raise RuntimeError("OUTAGE_MARKERS not found on the Tshwane fault map")
    raw = json.loads(m.group(1))
    return pd.DataFrame({
        "lat": [float(r.get("latitude")) if r.get("latitude") is not None else np.nan for r in raw],
        "lng": [float(r.get("longitude")) if r.get("longitude") is not None else np.nan for r in raw],
        "suburb": [str(r.get("district") or "").strip() for r in raw],
        "street": [str(r.get("street") or "").strip() for r in raw],
    })


def _fault_keys(df: pd.DataFrame) -> pd.Series:
    """Stable id for a fault: rounded point plus suburb, numbered when several share one spot."""
    base = (df["lat"].round(4).map("{:.4f}".format) + "," + df["lng"].round(4).map("{:.4f}".format) + "|"
            + df["suburb"].str.upper().str.replace(r"\s+", " ", regex=True))
    return base + "#" + base.groupby(base).cumcount().astype(str)


def update_fault_snapshot(current: pd.DataFrame, previous: pd.DataFrame | None,
                          now: datetime) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Carry first_seen across runs and list faults that have disappeared.

    Returns (open_faults, cleared). open_faults has first_seen, last_seen and
    open_hours; cleared has the previous row plus cleared_at and open_hours.
    """
    stamp = pd.Timestamp(now).tz_convert("UTC") if pd.Timestamp(now).tzinfo else pd.Timestamp(now, tz="UTC")
    cur = current.copy()
    cur["fault_key"] = _fault_keys(cur)
    if previous is not None and len(previous):
        prev = previous.copy()
        prev["first_seen"] = pd.to_datetime(prev["first_seen"], utc=True)
        seen = prev.drop_duplicates("fault_key").set_index("fault_key")["first_seen"]
        cur["first_seen"] = cur["fault_key"].map(seen).fillna(stamp)
        cleared = prev[~prev["fault_key"].isin(cur["fault_key"])].copy()
    else:
        cur["first_seen"] = stamp
        cleared = pd.DataFrame(columns=list(cur.columns) + ["last_seen"])
    cur["first_seen"] = pd.to_datetime(cur["first_seen"], utc=True)
    cur["last_seen"] = stamp
    cur["open_hours"] = ((stamp - cur["first_seen"]).dt.total_seconds() / 3600).round(2)
    cleared["cleared_at"] = stamp
    if len(cleared):
        cleared["open_hours"] = ((stamp - pd.to_datetime(cleared["first_seen"], utc=True))
                                 .dt.total_seconds() / 3600).round(2)
    return cur.reset_index(drop=True), cleared.reset_index(drop=True)


def tshwane_faults(wards_df: pd.DataFrame, previous: pd.DataFrame | None = None,
                   now: datetime | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open electricity faults on the City of Tshwane map, placed in wards, with open time tracking.

    Pass the previous run's open_faults frame as `previous` so first_seen is
    carried over; a fault that is gone appears in the returned cleared frame.
    Open-fault columns: fault_key, lat, lng, suburb, street, code, ward_id,
    first_seen, last_seen, open_hours, source. The map holds places only, no
    personal data.
    """
    now = now or datetime.now(timezone.utc)
    page = _fetch(FAULT_MAP, cache=False).decode("utf-8", "ignore")
    markers = parse_fault_markers(page)
    markers["code"], markers["ward_id"] = WardLocator(wards_df).locate(markers["lat"], markers["lng"])
    markers["source"] = FAULT_MAP
    cur, cleared = update_fault_snapshot(markers, previous, now)
    sosh = cur["suburb"].str.upper().str.contains("SOSHANGUVE")
    cur.attrs["report"] = {
        "open_faults": len(cur), "in_tshwane_ward": int((cur["code"] == "TSH").sum()),
        "ward_coverage": _coverage(cur, "ward_id"), "soshanguve": int(sosh.sum()),
        "carried_over": int((cur["first_seen"] < cur["last_seen"]).sum()), "cleared": len(cleared),
    }
    return cur, cleared


# --------------------------------------------------------------------------
# 4. Gazetteer and local news
# --------------------------------------------------------------------------

MUNI_WORDS = r"\b(city of|local municipality of|metropolitan|metro|municipality|local|district|the)\b"
MUNI_ALIASES = {
    "tshwane": "TSH", "joburg": "JHB", "johannesburg": "JHB", "nelson mandela bay": "NMA", "cape town": "CPT",
    "ethekwini": "ETH", "ekurhuleni": "EKU", "mangaung": "MAN", "buffalo city": "BUF", "mahikeng": "NW383",
    "mafikeng": "NW383", "madibeng": "NW372", "jb marks": "NW405", "tlokwe": "NW405", "msunduzi": "KZN225",
    "or tambo": "DC15", "o r tambo": "DC15", "maluti a phofung": "FS194", "kagisano molopo": "NW397",
    "modimolle mookgophong": "LIM368", "hibiscus coast": "KZN216", "khai ma": "NC067",
    # spellings and old names seen in SIU proclamation titles
    "great kokstad": "KZN433", "kwaduza": "KZN292", "ekhuruleni": "EKU", "lepelle nkumpi": "LIM355",
    "nelson mandela metropolitan": "NMA", "o r district tambo": "DC15", "swelledam": "WC034",
    "lejeweleputswa": "DC18", "uthungulu": "DC28", "qaukeni": "EC153",
}
# Municipality names that are also ordinary words or first names: only used
# when the text says "municipality", "council" or "metro" near them.
RISKY_MUNI_NAMES = {"george", "ubuntu", "richmond", "naledi", "nala", "makana", "lekwa", "emalahleni", "hantam",
                    "bitou", "mandeni", "impendle", "kannaland", "prince albert", "blouberg", "musina", "polokwane"}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def muni_names(munis_df: pd.DataFrame) -> dict[str, list[str]]:
    """Plain municipality name (no 'Metro', 'District', 'City of') to demarcation codes."""
    names: dict[str, list[str]] = {}
    for code, name in zip(munis_df["code"], munis_df["name"]):
        key = re.sub(r"\s+", " ", re.sub(MUNI_WORDS, " ", _plain(name))).strip()
        names.setdefault(key, []).append(code)
        names.setdefault(_plain(name), []).append(code)
    for k, v in MUNI_ALIASES.items():
        names.setdefault(k, [v])
    return {k: sorted(set(v)) for k, v in names.items() if len(k) >= 4}


PROVINCE_WORDS = {"eastern cape": "EC", "free state": "FS", "gauteng": "GT", "kwazulu natal": "KZN", "limpopo": "LIM",
                  "mpumalanga": "MP", "northern cape": "NC", "north west": "NW", "western cape": "WC"}


def match_municipality(text: str, names: dict[str, list[str]], munis_df: pd.DataFrame | None = None,
                       careful: bool = False) -> tuple[str | None, str | None]:
    """Find the municipality named in a piece of text. Returns (matched name, code).

    The longest name wins. A name shared by two municipalities (Emalahleni) is
    settled by the province in the text, else left unresolved. With
    careful=True, names in RISKY_MUNI_NAMES need 'municipality', 'council' or
    'metro' in the text.
    """
    t = " " + _plain(text) + " "
    govt = bool(re.search(r"\b(municipality|municipal|council|metro)\b", t))
    for key in sorted(names, key=len, reverse=True):
        if f" {key} " not in t:
            continue
        if careful and key in RISKY_MUNI_NAMES and not govt:
            continue
        codes = names[key]
        if len(codes) > 1 and munis_df is not None:
            prov = {p for w, p in PROVINCE_WORDS.items() if f" {w} " in t}
            parent = munis_df.set_index("code")["parent"].to_dict()

            def province(c: str) -> str | None:
                p = parent.get(c)
                while p is not None and p not in PROVINCE_WORDS.values():
                    p = parent.get(p)
                return p

            codes = [c for c in codes if province(c) in prov] or codes
        return key, (codes[0] if len(codes) == 1 else None)
    return None, None


# Words that are GeoNames places somewhere in SA but, in news, almost always mean something else.
PLACE_STOPLIST = {
    "parliament", "jacaranda", "union", "eskom", "sasol", "premier", "president", "national", "cape", "south",
    "north", "east", "west", "central", "africa", "african", "constitution", "hospital", "police", "court",
    "freedom", "unity", "welcome", "victory", "justice", "democracy", "mandela", "zuma", "ramaphosa", "malema",
    "chiefs", "pirates", "sundowns", "stormers", "bulls", "sharks", "lions", "proteas", "springboks", "bafana",
    "banyana", "amazon", "google", "apple", "israel", "gaza", "russia", "china", "america", "london", "paris",
    "hope", "grace", "content", "paradise", "success", "rest", "mission", "station", "bethel", "canaan",
    "goodwill", "harmony", "liberty", "trust", "providence", "mercy", "kruger", "table", "market", "school",
    "farm", "park", "garden", "gardens", "village", "city", "town", "valley", "river", "bridge", "hill",
    "hills", "mountain", "view", "bay", "port", "church", "store", "mine", "spring", "junction", "post",
    "golden", "silver", "diamond", "crystal", "royal", "queen", "king", "prince", "princess", "lady",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "january", "february",
    "march", "april", "june", "july", "august", "september", "october", "november", "december", "may",
    "news", "sabc", "moneyweb", "citizen", "rekord", "maverick", "daily", "times", "star", "sun", "mail",
    "home", "house", "state", "minister", "mayor", "council", "government", "budget", "report", "trump",
    "new", "old", "big", "little", "long", "high", "low", "top", "good", "best", "first", "last", "main",
    "morning", "evening", "christmas", "easter", "heritage", "women", "youth", "workers", "people",
    "england", "scotland", "wales", "ireland", "holland", "germany", "india", "japan", "berlin", "moscow",
    "washington", "boston", "lincoln", "jackson", "franklin", "adams", "mbeki", "zille", "steenhuisen",
    "mashatile", "motsoaledi", "lesufi", "kunene", "brink", "hill-lewis", "morero", "moroka", "tambo",
    "south africa", "southern africa", "springbok", "rugby", "milton", "miller", "wallaby", "sichuan",
    "sisulu", "biko", "hani", "luthuli", "tutu", "winnie", "nelson", "thabo", "cyril", "jacob", "helen",
    "john", "george", "james", "william", "charles", "henry", "david", "peter", "paul", "mary", "elizabeth",
    "victoria", "alice", "rose", "lily", "daisy", "ruby", "stella", "maria", "anna", "sarah", "grace",
}
NOT_BEFORE = {"fm", "radio", "stars", "chiefs", "city fc", "united", "fc", "tv", "university", "college",
              "hotel", "mall", "stadium", "airport", "prison", "correctional", "magistrate", "street", "road"}
PREPOSITIONS = {"in", "at", "near", "from", "outside", "around", "of", "to", "into", "across"}
NEEDS_PREPOSITION = {"george", "richmond", "wellington", "bethlehem", "alexandra", "springs", "welkom",
                     "vryheid", "hammanskraal", "orange farm", "sun city", "jordan"}


def townships_from_schools(schools_df: pd.DataFrame, min_schools: int = 3) -> pd.DataFrame:
    """Township and suburb points from school suburbs: the median school location per suburb and municipality."""
    s = schools_df.dropna(subset=["suburb", "lat", "code"]).copy()
    s["name"] = s["suburb"].astype(str).str.title().str.strip()
    s = s[~s["name"].str.contains(r"\d|\bExt\b|\bUnknown\b|\bFarm\b|\bPlot", regex=True)
          & s["name"].str.len().between(5, 30) & (s["name"].str.split().str.len() <= 3)]
    g = s.groupby(["name", "code"]).agg(lat=("lat", "median"), lng=("lng", "median"), weight=("emis", "size"))
    g = g[g["weight"] >= min_schools].reset_index()
    g["population"] = np.nan
    g["kind"] = "township"
    return g[["name", "lat", "lng", "population", "kind", "code", "weight"]]


def gazetteer(munis_df: pd.DataFrame | None = None, townships: pd.DataFrame | None = None,
              refresh: bool = False, wards_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """South African place names with a point each.

    Sources: GeoNames ZA populated places (CC BY 4.0, cached ZA.zip), our 257
    municipality names (a point inside each boundary), and optional township
    points (see townships_from_schools). Columns: name, lat, lng, population,
    kind (city, place, township, municipality), code, weight. `code` comes from
    our own boundaries when wards_df is given, never from GeoNames admin codes.
    """
    rows = []
    content = _fetch(GEONAMES_ZA, refresh)
    with zipfile.ZipFile(io.BytesIO(content)) as z, z.open("ZA.txt") as f:
        for line in io.TextIOWrapper(f, encoding="utf-8"):
            p = line.split("\t")
            if p[6] != "P":
                continue
            kind = "city" if p[7] in ("PPLC", "PPLA", "PPLA2") else "place"
            rows.append((p[1], float(p[4]), float(p[5]), float(p[14] or 0), kind))
    gz = pd.DataFrame(rows, columns=["name", "lat", "lng", "population", "kind"])
    gz["code"] = None
    gz["weight"] = gz["population"]
    if wards_df is not None:
        gz["code"], _ = WardLocator(wards_df, snap_km=3).locate(gz["lat"], gz["lng"])
    parts = [gz]
    if munis_df is not None:
        m = munis_df[munis_df["level"].isin(["local", "district_or_metro"])]
        from shapely.geometry import shape

        pts = [shape(json.loads(g)).representative_point() for g in m["geometry"]]
        mm = pd.DataFrame({"name": m["name"].str.replace(r"\s+(Metro|District)$", "", regex=True)
                           .str.replace(r"^(City of|Local Municipality of)\s+", "", regex=True),
                           "lat": [p.y for p in pts], "lng": [p.x for p in pts], "population": np.nan,
                           "kind": "municipality", "code": m["code"].to_numpy(), "weight": np.nan})
        parts.append(mm)
    if townships is not None and len(townships):
        parts.append(townships)
    out = pd.concat(parts, ignore_index=True)
    out.attrs["report"] = {"names": len(out), **out["kind"].value_counts().to_dict()}
    return out


MIN_NAME_LEN = 5  # shorter names (Bela, Hope, Rust) are too often ordinary words
_TOKEN = re.compile(r"[A-Za-z][A-Za-z'\-]*")


def _index_gazetteer(gaz: pd.DataFrame) -> tuple[dict[str, pd.DataFrame], int]:
    g = gaz.copy()
    g["key"] = g["name"].map(lambda s: " ".join(t.lower() for t in _TOKEN.findall(
        unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode())))
    g = g[(g["key"].str.len() >= MIN_NAME_LEN) & ~g["key"].isin(PLACE_STOPLIST)]
    maxlen = int(g["key"].str.count(" ").max()) + 1
    return {k: v for k, v in g.groupby("key")}, maxlen


def find_places(text: str, index: dict[str, pd.DataFrame], maxlen: int = 4) -> list[tuple[int, str]]:
    """Place names in text, as (position, key). Names must be capitalised and not in the stoplist."""
    toks = [(m.start(), re.sub(r"'s$", "", m.group(0))) for m in _TOKEN.finditer(text)]
    found, i = [], 0
    while i < len(toks):
        hit = None
        for n in range(min(maxlen, len(toks) - i), 0, -1):
            words = [t for _, t in toks[i:i + n]]
            if not all(w[0].isupper() for w in words):
                continue
            key = " ".join(w.lower() for w in words)
            if key in index:
                hit = (n, key)
                break
        if hit:
            n, key = hit
            after = " ".join(t.lower() for _, t in toks[i + n:i + n + 2])
            before = toks[i - 1][1].lower() if i else ""
            blocked = any(after == b or after.startswith(b + " ") for b in NOT_BEFORE)
            if key in NEEDS_PREPOSITION and before not in PREPOSITIONS:
                blocked = True
            if not blocked:
                found.append((toks[i][0], key))
            i += n
        else:
            i += 1
    return found


KIND_RANK = {"township": 3, "place": 2, "city": 1, "municipality": 0}


def resolve_place(keys: list[str], index: dict[str, pd.DataFrame], context_code: str | None) -> pd.Series | None:
    """Pick one gazetteer row for the text.

    The most specific name wins (township or place before city or
    municipality, earliest mention first). Among entries sharing that name,
    prefer one inside the municipality the text names, then school-derived
    townships, then the largest population.
    """
    if not keys:
        return None
    ctx = context_code
    if ctx is None:  # a city or municipality mentioned alongside acts as context
        for k in keys:
            c = index[k]
            big = c[c["kind"].isin(["city", "municipality"])].dropna(subset=["code"])
            if len(big):
                ctx = big.sort_values("weight", ascending=False)["code"].iloc[0]
                break
    best = None
    for k in keys:
        c = index[k].copy()
        c["in_ctx"] = (c["code"] == ctx) if ctx else False
        c["rank"] = c["kind"].map(KIND_RANK)
        c = c.sort_values(["in_ctx", "rank", "weight"], ascending=False, na_position="last")
        top = c.iloc[0]
        if best is None or (top["rank"], top["in_ctx"]) > (best["rank"], best["in_ctx"]):
            best = top
    return best


EVENT_RULES: list[tuple[str, str]] = [
    ("gbv", r"gender[- ]based violence|\bgbv\b|femicide|domestic violence|\brape[ds]?\b|\braping\b|sexual assault"),
    ("sewage", r"sewage|sewer|wastewater|waste water|sanitation|\bspillage\b|pit latrine|\btoilets?\b"),
    ("water", r"\bwater\b|dry taps|\btaps\b|reservoir|burst pipe|water outage|rand water|\bdrought\b"),
    ("electricity", r"electricity|power outage|power cut|outages?\b|load[- ]?shedding|load reduction|\beskom\b"
                    r"|substation|blackout|cable theft|transformer|\bprepaid\b|\bpower\b"),
    ("roads", r"pothole|road closure|road ?works|\bbridge\b|traffic lights?|\bcrash\b|\baccident\b|\broads?\b"),
    ("protest", r"protest|shutdown|\bmarch(ed|es)?\b|\bstrike\b|picket|unrest|\briot|service delivery"),
    ("corruption", r"corruption|\bfraud|tender (fraud|irregularit|rigging)|\bsiu\b|special investigating unit|maladministration|looting"
                   r"|brib|irregular expenditure|state capture|money laundering"),
    ("crime", r"murder|\bkill(ed|ing|s)?\b|shot|shooting|robbery|robbed|hijack|arrest|\bpolice\b|\bsaps\b"
              r"|stabb|kidnap|cash[- ]in[- ]transit|suspects?|gunm[ae]n|\bcrime\b|\btheft\b"),
    ("jobs", r"\bjobs?\b|unemploy|employment|retrench|job cuts|hiring|vacanc|learnership|internship"),
    ("housing", r"housing|\brdp\b|informal settlement|evict|land invasion|land grab|shacks?\b|title deeds"),
    ("health", r"clinic|hospital|\bhealth|outbreak|cholera|measles|\btb\b|\bhiv\b|doctors?|nurses?|mpox|listeria"),
    ("education", r"\bschools?\b|learners?|matric|teachers?|universit|students?|nsfas|\btvet\b|\bexams?\b"),
]


def classify_event(text: str) -> str:
    """Event type from keywords only, first matching rule wins."""
    t = str(text).lower()
    for label, pat in EVENT_RULES:
        if re.search(pat, t):
            return label
    return "other"


def normalise_url(url: str) -> str:
    """Host without www, path without trailing slash; query and fragment dropped."""
    p = urlsplit(str(url).strip())
    host = (p.hostname or "").lower().removeprefix("www.")
    return host + (p.path.rstrip("/") or "/")


def _norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(t).lower())).strip()


def dedupe_news(items: pd.DataFrame, window_hours: float = 48, threshold: float = 0.85) -> pd.DataFrame:
    """Drop repeated URLs, then fold near-identical headlines within the window into one row.

    The earliest item in a cluster is kept; other outlets go in also_reported_by.
    """
    df = items.copy()
    df["url_norm"] = df["url"].map(normalise_url)
    df = df.sort_values("published", na_position="last").drop_duplicates("url_norm").reset_index(drop=True)
    titles = df["title"].map(_norm_title).tolist()
    tsets = [set(t.split()) for t in titles]
    pub = pd.to_datetime(df["published"], utc=True)
    reps: list[int] = []
    cluster = [0] * len(df)
    for i in range(len(df)):
        for r in reps:
            close = pd.isna(pub[i]) or pd.isna(pub[r]) or abs(pub[i] - pub[r]) <= pd.Timedelta(hours=window_hours)
            if not close:
                continue
            jac = len(tsets[i] & tsets[r]) / max(1, len(tsets[i] | tsets[r]))
            if jac >= 0.75 or SequenceMatcher(None, titles[i], titles[r]).ratio() >= threshold:
                cluster[i] = r
                break
        else:
            cluster[i] = i
            reps.append(i)
    df["cluster"] = cluster
    df["cluster_id"] = df["cluster"].map(lambda r: sha1(df.at[r, "url_norm"].encode()).hexdigest()[:10])
    others = df.groupby("cluster")["outlet"].agg(list)
    keep = df[df.index == df["cluster"]].copy()
    keep["also_reported_by"] = [", ".join(sorted(set(o for o in others[i] if o != keep.at[i, "outlet"])))
                                for i in keep.index]
    return keep.drop(columns=["url_norm", "cluster"]).reset_index(drop=True)


def fetch_feeds(feeds: dict[str, str] | None = None, timeout: float = 30.0) -> tuple[pd.DataFrame, dict]:
    """Read RSS feeds: title, url, outlet, published (UTC) and the short summary. Bodies are ignored."""
    import feedparser

    rows, status = [], {}
    for outlet, url in (feeds or FEEDS).items():
        try:
            parsed = feedparser.parse(_fetch(url, cache=False, timeout=timeout))
        except Exception as exc:  # one broken feed must not stop the rest
            status[outlet] = f"failed: {type(exc).__name__}"
            continue
        status[outlet] = len(parsed.entries)
        for e in parsed.entries:
            when = e.get("published_parsed") or e.get("updated_parsed")
            summary = re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", e.get("summary", "") or "")))
            rows.append({"title": htmllib.unescape(str(e.get("title", ""))).strip(), "url": e.get("link"),
                         "outlet": outlet,
                         "published": datetime(*when[:6], tzinfo=timezone.utc) if when else pd.NaT,
                         "summary": summary.strip()[:400]})
    df = pd.DataFrame(rows, columns=["title", "url", "outlet", "published", "summary"])
    df["published"] = pd.to_datetime(df["published"], utc=True)
    return df[(df["title"].str.len() > 0) & df["url"].notna()].reset_index(drop=True), status


def geolocate_news(items: pd.DataFrame, gaz: pd.DataFrame, wards_df: pd.DataFrame,
                   munis_df: pd.DataFrame) -> pd.DataFrame:
    """Add place, code, ward_id and event to news items (title plus summary are read).

    ward_id is only given when the place is small enough to sit in one ward
    (under 30,000 people, or a suburb with at most 5 schools); for a city or a
    big township the municipality code alone is reported.
    """
    index, maxlen = _index_gazetteer(gaz)
    names = muni_names(munis_df)
    loc = WardLocator(wards_df, snap_km=3)
    out = []
    for r in items.itertuples(index=False):
        text = f"{r.title}. {r.summary}"
        _, ctx = match_municipality(text, names, munis_df, careful=True)
        keys = [k for _, k in find_places(r.title, index, maxlen)] + \
               [k for _, k in find_places(str(r.summary), index, maxlen)]
        best = resolve_place(list(dict.fromkeys(keys)), index, ctx)
        place, code, ward = None, ctx, None
        if best is not None:
            place = best["name"]
            c, w = loc.locate([best["lat"]], [best["lng"]])
            code = c[0] or best.get("code") or ctx
            is_muni = (index[best["key"]]["kind"] == "municipality").any()  # e.g. the GeoNames point 'Tshwane'
            small_place = best["kind"] == "place" and (pd.isna(best["population"]) or best["population"] < 30000)
            small_suburb = best["kind"] == "township" and best["weight"] <= 5
            small = not is_muni and (small_place or small_suburb)
            ward = w[0] if small else None
        out.append({"place": place, "code": code, "ward_id": ward, "event": classify_event(text)})
    res = items.reset_index(drop=True).join(pd.DataFrame(out))
    for c in ("place", "code", "ward_id"):
        res[c] = res[c].astype(object).where(res[c].notna(), None)
    return res


def news(gaz: pd.DataFrame, wards_df: pd.DataFrame, munis_df: pd.DataFrame,
         feeds: dict[str, str] | None = None) -> pd.DataFrame:
    """Local news headlines from SA RSS feeds, placed and classified, one row per story.

    Columns: title, url, outlet, published, place, code, ward_id (nullable),
    event, cluster_id, also_reported_by. Summaries are used for matching and
    then dropped; article bodies are never read.
    """
    raw, status = fetch_feeds(feeds)
    placed = geolocate_news(dedupe_news(raw), gaz, wards_df, munis_df)
    out = placed[["title", "url", "outlet", "published", "place", "code", "ward_id", "event", "cluster_id",
                  "also_reported_by"]]
    out.attrs["report"] = {
        "fetched": len(raw), "stories": len(out), "with_code": int(out["code"].notna().sum()),
        "with_ward": int(out["ward_id"].notna().sum()), "code_coverage": _coverage(out, "code"),
        "events": out["event"].value_counts().to_dict(), "feeds": status,
    }
    return out


# --------------------------------------------------------------------------
# 5. SIU local government proclamations
# --------------------------------------------------------------------------

def siu_investigations(munis_df: pd.DataFrame, refresh: bool = True) -> pd.DataFrame:
    """Presidential proclamations sending the SIU into a municipality.

    Columns: proclamation (e.g. R350), year, date, title, municipality (name as
    matched), code, status (ongoing, completed or unknown), link, source.
    """
    items, page = [], 1
    while True:
        url = SIU_API.format(cat=SIU_LOCAL_GOV, page=page)
        try:
            batch = json.loads(_fetch(url, cache=False))
        except httpx.HTTPStatusError:
            break
        items += batch
        if len(batch) < 100:
            break
        page += 1
    names = muni_names(munis_df)
    rows = []
    for it in items:
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", it["title"]["rendered"])).strip()
        m = re.search(r"\b(R\s?\.?\s?\d+)\s+of\s+(\d{4})", title, re.I)
        muni, code = match_municipality(title, names, munis_df)
        cats = set(it.get("categories", []))
        rows.append({
            "proclamation": re.sub(r"[\s.]", "", m.group(1)).upper() if m else None,
            "year": int(m.group(2)) if m else pd.NA,
            "date": pd.Timestamp(it["date"]).date(), "title": title, "municipality": muni, "code": code,
            "status": "ongoing" if SIU_ONGOING in cats else "completed" if SIU_COMPLETED in cats else "unknown",
            "link": it["link"], "source": SIU_API.format(cat=SIU_LOCAL_GOV, page=1),
        })
    out = pd.DataFrame(rows).sort_values("date", ascending=False).reset_index(drop=True)
    out["year"] = out["year"].astype("Int64")
    out.attrs["report"] = {"proclamations": len(out), "with_code": int(out["code"].notna().sum()),
                           "latest": out.iloc[0][["proclamation", "year", "date", "code"]].to_dict() if len(out) else None}
    return out


# --------------------------------------------------------------------------
# Live run
# --------------------------------------------------------------------------

def _run() -> None:  # pragma: no cover - live network run
    import time

    import psutil

    proc = psutil.Process()
    t0 = time.time()
    timings: dict[str, float] = {}

    def mark(name: str, since: float) -> float:
        timings[name] = round(time.time() - since, 1)
        print(f"[{name}] {timings[name]}s rss={proc.memory_info().rss / 2**20:.0f}MB", flush=True)
        return time.time()

    t = time.time()
    wards_df, munis_df = load_wards(), load_munis()
    t = mark("load", t)

    sch = schools(wards_df)
    print("schools", sch.attrs["report"])
    t = mark("schools", t)

    mat = matric_results()
    print("matric", mat.attrs["report"])
    reit = mat[mat["emis"] == "700241174"]
    print(reit.to_string())
    t = mark("matric", t)

    snap = FALLBACK / "tshwane_faults.csv"
    prev = pd.read_csv(snap, dtype={"ward_id": str}) if snap.exists() else None
    cur, cleared = tshwane_faults(wards_df, prev)
    print("faults", cur.attrs["report"])
    FALLBACK.mkdir(exist_ok=True)
    cur.to_csv(snap, index=False)
    if len(cleared):
        log = FALLBACK / "tshwane_faults_cleared.csv"
        cleared.to_csv(log, mode="a", header=not log.exists(), index=False)
    sosh = cur[cur["suburb"].str.upper().str.contains("SOSHANGUVE")]
    print(sosh.groupby("ward_id").size().sort_values(ascending=False).head(10).to_string())
    t = mark("faults", t)

    gz = gazetteer(munis_df, townships_from_schools(sch), wards_df=wards_df)
    print("gazetteer", gz.attrs["report"])
    t = mark("gazetteer", t)

    nw = news(gz, wards_df, munis_df)
    print("news", nw.attrs["report"])
    print(nw[nw["code"] == "TSH"][["outlet", "title", "place", "ward_id", "event", "also_reported_by"]]
          .to_string(max_colwidth=70))
    print(nw.dropna(subset=["place"]).sample(min(25, nw["place"].notna().sum()), random_state=1)
          [["title", "place", "code", "event"]].to_string(max_colwidth=80))
    t = mark("news", t)

    siu = siu_investigations(munis_df)
    print("siu", siu.attrs["report"])
    print(siu.head(8).to_string(max_colwidth=60))
    print("siu unmatched:", siu[siu["code"].isna()]["title"].tolist())
    t = mark("siu", t)

    w90 = wards_df[(wards_df["code"] == "TSH") & (wards_df["ward_no"].astype(int) == 90)]["ward_id"].tolist()
    s90 = sch[sch["ward_id"].isin(w90)].merge(mat[mat["year"] == 2024][["emis", "wrote", "passed", "pass_rate"]],
                                               on="emis", how="left")
    print("TSH ward 90", w90)
    print(s90[["emis", "name", "sector", "no_fee", "quintile", "phase", "learners", "wrote", "passed", "pass_rate"]]
          .to_string())
    joined = mat[mat["year"] == mat["report_year"]]["emis"].isin(sch["emis"]).mean()
    print("matric rows joining to schools:", round(float(joined), 4))
    mem = proc.memory_info()
    peak = getattr(mem, "peak_wset", mem.rss)
    print(f"total {time.time() - t0:.0f}s, peak memory {peak / 2**20:.0f}MB", timings)


if __name__ == "__main__":  # pragma: no cover
    _run()
