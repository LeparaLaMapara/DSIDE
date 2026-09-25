"""Fresh public statistics per municipality: jobs, people, grants, water and power.

Five free sources that need no login:

  * spatial_tax()      Spatial Tax Panel (SARS and National Treasury tax data,
                       run by the HSRC). Open dashboard API, no account needed.
  * population_2026()  Stats SA P0302 district short-term estimates 2026 to 2030.
  * srd_grants()       SASSA monthly Social Relief of Distress (R370) report.
  * water_quality()    DWS Green Drop 2025 (wastewater) and Blue Drop 2025 PAT
                       (drinking water) reports per water services authority.
  * eskom_status()     Eskom's national loadshedding stage right now.

Every function returns a tidy DataFrame keyed by the Treasury demarcation
`code` (TSH, EC157, DC48 and so on) with `period` and `source` columns.
Place names in the PDFs and spreadsheets are matched to codes with a small
registry built from the Spatial Tax municipality list (the 213 local and
metro councils) and Treasury's district list (the 44 districts).
"""

from __future__ import annotations

import difflib
import io
import re
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

from ..http import CACHE_DIR, USER_AGENT, Fetcher, client

FALLBACK = Path(__file__).resolve().parents[2] / "fallback"
BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " + USER_AGENT

# ---------------------------------------------------------------- downloads


def _cache_path(url: str) -> Path:
    return CACHE_DIR / re.sub(r"[^A-Za-z0-9._-]", "_", url.split("//", 1)[1])[-150:]


def _fetch(url: str, refresh: bool = False, timeout: float = 120.0, verify: bool = True,
           cache: bool = True) -> bytes:
    """Download a file once and keep it in the engine cache."""
    path = _cache_path(url)
    if cache and path.exists() and not refresh:
        return path.read_bytes()
    with client(timeout, verify, BROWSER_UA) as c:
        r = c.get(url)
        r.raise_for_status()
    if cache:
        CACHE_DIR.mkdir(exist_ok=True)
        path.write_bytes(r.content)
    return r.content


# ---------------------------------------------------------------- name to code

PROVINCES = {
    "EC": "EC", "EASTERN CAPE": "EC", "FS": "FS", "FREE STATE": "FS", "GP": "GT", "GT": "GT", "GAUTENG": "GT",
    "KZN": "KZN", "KZ": "KZN", "KWAZULU NATAL": "KZN", "KWAZULU-NATAL": "KZN", "LP": "LIM", "LIM": "LIM", "LIMPOPO": "LIM",
    "MP": "MP", "MPUMALANGA": "MP", "NC": "NC", "NORTHERN CAPE": "NC", "NW": "NW", "NORTH WEST": "NW",
    "WC": "WC", "WESTERN CAPE": "WC",
}

# Names used in the reports that neither the fuzzy match nor the registry can resolve.
ALIASES = {
    "nelsonmandela": "NMA", "amatole": "DC12", "greatersekhukhune": "DC47", "mookgophong": "LIM368",
    "modimollemookgophong": "LIM368", "drruthsmompati": "DC39", "drruthsegomotsimompati": "DC39",
    "thembisile": "MP315", "solplaatjie": "NC091", "ortambo": "DC15", "mbombela": "MP326",
    "joburg": "JHB", "johannesburg": "JHB", "capetown": "CPT", "lepellenkumpi": "LIM355",
    "drbeyersnaude": "EC101", "sundaysrivervalley": "EC106", "kaigarib": "NC082",
    "umhlathuze": "KZN282", "ekurhuleni": "EKU", "tshwane": "TSH", "ethekwini": "ETH",
    "buffalocity": "BUF", "mangaung": "MAN", "matlosana": "NW403", "raymondmhlaba": "EC129",
    "zfmgcawu": "DC8", "pixleykasemenc": "DC7", "engcobo": "EC137", "fetakgomogreatertubatse": "LIM476",
}

_DROP = re.compile(
    r"\b(local|metropolitan|metro|district|municipality|municipal|municipa|lm|dm|mm|the)\b")


def _key(name: str) -> str:
    """Reduce a place name to a comparable key: 'City of Tshwane Metropolitan Municipality' -> 'tshwane'."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"^\s*city of\s+", " ", s)
    s = _DROP.sub(" ", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _kind(name: str) -> str | None:
    """Guess the council category from its label: A metro, B local, C district."""
    n = f" {str(name).lower()} "
    if re.search(r"\b(metropolitan|metro|mm)\b", n):
        return "A"
    if re.search(r"\b(district|dm)\b", n):
        return "C"
    if re.search(r"\b(local|lm)\b", n):
        return "B"
    return None


def registry(f: Fetcher | None = None) -> pd.DataFrame:
    """The 257 current councils: code, name, province, category (A, B or C), district and a match key.

    Local and metro councils come from the Spatial Tax municipality list, which
    follows the current (2016) boundaries; districts come from Treasury. Both
    are open. Treasury's list alone also holds 35 disestablished councils,
    which would attract false matches such as 'Mookgophong'.
    """
    from .municipal_money import municipalities

    f = f or Fetcher()
    rows = []
    for m in f.get("https://api.spatialtaxdata.org.za/api/municipality-list/"):
        rows.append({"code": m["cat_b"], "name": m["municname"], "category": m["category"],
                     "province": PROVINCES.get(m["province"], m["province"]), "district": m["district"]})
    current = {r["code"] for r in rows}
    for m in municipalities(f):
        code = m["municipality.demarcation_code"]
        cat = m["municipality.category"]
        if cat == "C" or code in current:
            rows.append({"code": code, "name": m["municipality.name"], "category": cat,
                         "province": PROVINCES.get(m["municipality.province_code"], m["municipality.province_code"]),
                         "district": code if cat != "B" else None})
    reg = pd.DataFrame(rows)
    reg["district"] = reg["district"].fillna(reg["code"].map(reg.dropna(subset=["district"])
                                                            .drop_duplicates("code").set_index("code")["district"]))
    reg["key"] = reg["name"].map(_key)
    return reg.drop_duplicates(["code", "key"]).reset_index(drop=True)


def match_code(name: str, reg: pd.DataFrame, province: str | None = None) -> str | None:
    """Map a council name from a report to its demarcation code, or None.

    Order: manual alias, exact key within the province (preferring the
    category the label implies), then a close fuzzy match (ratio >= 0.85).
    """
    key = _key(name)
    if not key:
        return None
    pool = reg if province is None else reg[reg["province"] == province]
    kind = _kind(name)
    for cands in ([pool[pool["category"] == kind]] if kind else []) + [pool]:
        hit = cands[cands["key"] == key]
        if len(hit):
            return str(hit["code"].iloc[0])
    if key in ALIASES:
        return ALIASES[key]
    for cands in ([pool[pool["category"] == kind]] if kind else []) + [pool]:
        close = difflib.get_close_matches(key, cands["key"].tolist(), n=1, cutoff=0.85)
        if close:
            return str(cands.loc[cands["key"] == close[0], "code"].iloc[0])
    return None


# ---------------------------------------------------------------- 1. Spatial Tax Panel

STP = "https://api.spatialtaxdata.org.za/api/"
# The map explorer endpoint returns every municipality in one call. The youth
# bands follow the panel's range edges 15, 25, 35: lower 15 and upper 35 means
# ages 15 to 34.
STP_QUERIES = {
    "formal_jobs": "taxdata_modelname=metro_fte&output=fte",
    "establishments": "taxdata_modelname=metro_firms&output=firms",
    "median_income": "taxdata_modelname=metro_medianincome&output=medianincome",
    "youth_jobs": "taxdata_modelname=metro_fte_youth&output=fte&youthlower=15&youthupper=35",
    "youth_median_income": "taxdata_modelname=metro_medianincome_youth&output=medianincome&youthlower=15&youthupper=35",
}


def _stp_url(query: str, year: int) -> str:
    return f"{STP}map-explorer/?{query}&year={year}&viewas=Absolute&spatial=metro"


def _stp_values(rows: list[dict], codes: set[str]) -> dict[str, float]:
    """Keep real councils only; the panel also reports 'Missing Location Data' and head office rows."""
    return {r["cat_b"]: float(r["display"]) for r in rows
            if r.get("cat_b") in codes and isinstance(r.get("display"), (int, float))}


def _stp_latest_year(f: Fetcher) -> int:
    return max(int(r["taxyear"]) for r in f.get(f"{STP}metro-year/"))


def spatial_tax(refresh: bool = False) -> pd.DataFrame:
    """Formal jobs, youth jobs, pay and firms per local and metro council, latest tax year.

    Columns: code, period (tax year), formal_jobs (full time equivalents),
    youth_jobs (FTE aged 15 to 34), median_income and youth_median_income
    (rand per month), establishments, source.

    youth_median_income is the panel's own figure for the 15 to 34 range,
    which it builds as the job-weighted mean of the 15 to 24 and 25 to 34
    medians, not a true pooled median. Jobs the panel could not place
    (head office anomalies, missing location) are left out, so council
    totals add up to less than the national total. Districts are not
    covered by this panel.
    """
    f = Fetcher(refresh=refresh)
    codes = set(registry(f).query("category != 'C'")["code"])
    year = _stp_latest_year(f)
    out = pd.DataFrame({"code": sorted(codes)})
    for col, q in STP_QUERIES.items():
        out[col] = out["code"].map(_stp_values(f.get(_stp_url(q, year)), codes))
    out = out.dropna(subset=["formal_jobs"])
    out.insert(1, "period", year)
    out["source"] = f"Spatial Tax Panel (HSRC, SARS, National Treasury), {STP}map-explorer/, tax year {year}"
    return out.reset_index(drop=True)


def spatial_tax_jobs_series(refresh: bool = False, years: int = 5) -> pd.DataFrame:
    """Formal jobs (FTE) per council for the last `years` tax years, long format.

    Columns: code, period (tax year), formal_jobs, source.
    """
    f = Fetcher(refresh=refresh)
    codes = set(registry(f).query("category != 'C'")["code"])
    last = _stp_latest_year(f)
    rows = []
    for y in range(last - years + 1, last + 1):
        for code, v in _stp_values(f.get(_stp_url(STP_QUERIES["formal_jobs"], y)), codes).items():
            rows.append({"code": code, "period": y, "formal_jobs": v})
    out = pd.DataFrame(rows).sort_values(["code", "period"]).reset_index(drop=True)
    out["source"] = f"Spatial Tax Panel map explorer (metro_fte), tax years {last - years + 1} to {last}"
    return out


# ---------------------------------------------------------------- 2. Stats SA P0302

P0302_FILE = "Short_term_estimates_2026_2030_district_level.xlsx"
P0302_LIVE = f"https://www.statssa.gov.za/publications/P0302/{P0302_FILE}"
# Exact Wayback capture found through the CDX index (status 200, 174,925 bytes).
P0302_ARCHIVE = f"https://web.archive.org/web/20251229153257id_/{P0302_LIVE}"
P0302_METROS = {"cape town": "CPT", "buffalo city": "BUF", "nelson mandela": "NMA", "mangaung": "MAN",
                "ethekwini": "ETH", "ekurhuleni": "EKU", "johannesburg": "JHB", "tshwane": "TSH"}


def p0302_code(name: str) -> str | None:
    """'GT - West Rand DM (DC48)' -> 'DC48'; 'GT - City of Tshwane Metropolitan Municipality' -> 'TSH'."""
    m = re.search(r"\((DC\d+)\)", str(name))
    if m:
        return m.group(1)
    low = str(name).lower()
    return next((c for k, c in P0302_METROS.items() if k in low), None)


def parse_p0302(content: bytes) -> pd.DataFrame:
    """Tidy the P0302 district sheet into one row per district or metro per year."""
    raw = pd.read_excel(io.BytesIO(content), header=None)
    header = raw.index[raw[0].astype(str).str.strip().eq("Name")][0]
    t = raw.iloc[header + 1:].copy()
    t.columns = ["name", "sex", "age"] + [int(float(c)) for c in raw.iloc[header, 3:]]
    t = t.dropna(subset=["name", "age"])
    t["code"] = t["name"].map(p0302_code)
    if t["code"].isna().any():
        raise ValueError(f"unmapped P0302 areas: {sorted(t.loc[t['code'].isna(), 'name'].unique())}")
    long = t.melt(id_vars=["code", "sex", "age"], value_vars=[c for c in t.columns if isinstance(c, int)],
                  var_name="period", value_name="people")
    long["people"] = pd.to_numeric(long["people"])
    low = long["age"].astype(str).str.extract(r"^(\d+)")[0].astype(int)
    groups = {
        "population": low >= 0,
        "children_0_14": low < 15,
        "youth_15_34": (low >= 15) & (low < 35),
        "working_age_15_64": (low >= 15) & (low < 65),
        "elderly_65_plus": low >= 65,
    }
    out = pd.concat({k: long[m].groupby(["code", "period"])["people"].sum() for k, m in groups.items()}, axis=1)
    out = out.round().astype(int).reset_index()
    return out


def population_2026(refresh: bool = False) -> pd.DataFrame:
    """Stats SA mid-year district estimates for 2026 to 2030 (44 districts and 8 metros).

    Columns: code, period (year), population, children_0_14, youth_15_34,
    working_age_15_64, elderly_65_plus, source.

    Tries the Stats SA site first (it usually refuses scripts), then the
    Wayback Machine copy, then the parsed copy saved in fallback/.
    """
    for url, timeout in ((P0302_LIVE, 30.0), (P0302_ARCHIVE, 180.0)):
        try:
            content = _fetch(url, refresh, timeout=timeout)
        except httpx.HTTPError:
            continue
        if not content.startswith(b"PK"):  # an HTML block page instead of the workbook
            _cache_path(url).unlink(missing_ok=True)
            continue
        out = parse_p0302(content)
        out["source"] = f"Stats SA P0302 {P0302_FILE}" + ("" if url == P0302_LIVE else " (Wayback Machine copy)")
        FALLBACK.mkdir(exist_ok=True)
        out.to_csv(FALLBACK / "p0302_districts.csv", index=False)
        return out
    saved = pd.read_csv(FALLBACK / "p0302_districts.csv")
    saved["source"] = saved["source"].astype(str) + " (last saved copy; source unreachable)"
    return saved


# ---------------------------------------------------------------- 3. SASSA SRD

SASSA_PAGE = "https://www.sassa.gov.za/publications/statistical-reports"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                        "september", "october", "november", "december"], 1)}
_SRD_ROW = re.compile(r"^(?P<name>.*?[A-Za-z].*?)\s+(?P<paid>\d[\d,]*)\s+(?P<unpaid>\d[\d,]*)\s+"
                      r"(?P<approved>\d[\d,]*)\s+(?P<pct>\d+)%")


def latest_srd_report(html: str) -> tuple[str, str]:
    """Pick the newest 'unemployment trends' (SRD) report link; returns (url, 'YYYY-MM')."""
    best = None
    for url in set(re.findall(r'href="([^"]+\.pdf)"', html)):
        m = re.search(r"unemployment_trends_report_end_of_([A-Za-z]+)_(\d{4})", url)
        if m and m.group(1).lower() in MONTHS:
            period = f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
            if best is None or period > best[1]:
                best = (url, period)
    if best is None:
        raise RuntimeError("no SRD report link found on the SASSA page")
    return best


def srd_table_lines(text: str) -> list[str]:
    """Lines of the per-municipality table: from its title (not the contents page entry) to the next table."""
    for m in re.finditer(r"APPLICATIONS BY (?:DISTRICT )?MUNICIPALITY[^\n]*\n", text, re.I):
        if re.match(r"(?:[^\n]*\n){0,2}\s*Region\b", text[m.end():]):  # the header sits right below the title
            seg = text[m.end():]
            stop = re.search(r"\n(?:TABLE \d+|KRA \d+)", seg, re.I)
            return (seg[:stop.start()] if stop else seg).split("\n")
    raise RuntimeError("SRD per-municipality table not found in the report")


def parse_srd_lines(lines: list[str]) -> pd.DataFrame:
    """Read the 'paid, unpaid and approved applications by municipality' table.

    The table holds three months side by side; the first block is the report
    month. Names that wrap onto two lines are joined, province subtotal rows
    set the province, and unnamed rows (applicants with no municipality) are
    skipped.
    """
    rows, province, pending = [], None, ""
    for line in lines:
        line = line.strip()
        m = _SRD_ROW.match(line)
        if not m:
            pending = line if line and not re.search(r"\d", line) else ""
            continue
        name = m.group("name").strip()
        if name.lower() in {"total", "grand total"}:
            continue
        if name.upper() in PROVINCES:
            province, pending = PROVINCES[name.upper()], ""
            continue
        if pending and not _key(name):  # 'Municipality 282120 ...' continues 'City of Tshwane Metropolitan'
            name = f"{pending} {name}"
        pending = ""
        paid, unpaid, approved = (int(m.group(k).replace(",", "")) for k in ("paid", "unpaid", "approved"))
        rows.append({"province": province, "name": name, "srd_paid": paid, "srd_unpaid": unpaid,
                     "srd_approved": approved, "srd_pct_paid": int(m.group("pct")),
                     "consistent": paid + unpaid == approved})
    return pd.DataFrame(rows, columns=["province", "name", "srd_paid", "srd_unpaid", "srd_approved",
                                       "srd_pct_paid", "consistent"])


def _srd_report_link() -> tuple[str, str]:
    """Newest SRD report from the SASSA page (with or without www); else the newest one already cached."""
    for page in (SASSA_PAGE, SASSA_PAGE.replace("www.", "")):
        try:
            return latest_srd_report(_fetch(page, cache=False, timeout=60).decode("utf-8", "ignore"))
        except (httpx.HTTPError, RuntimeError):
            continue
    cached = [p.name for p in CACHE_DIR.glob("*unemployment_trends_report_end_of_*.pdf")]
    links = "".join(f'<a href="https://sassa.gov.za/documents/uploads/{n.split("uploads_", 1)[-1]}">' for n in cached)
    return latest_srd_report(links)


def srd_grants(refresh: bool = False) -> pd.DataFrame:
    """SASSA Social Relief of Distress applications per local and metro council, latest month.

    Columns: code, period ('YYYY-MM'), srd_paid, srd_unpaid, srd_approved,
    srd_pct_paid, source. SASSA titles the table 'by district municipality'
    but it lists local and metro councils. Rows whose paid plus unpaid do not
    add up to approved are dropped as misread.
    """
    import pdfplumber

    url, period = _srd_report_link()
    pdf = pdfplumber.open(io.BytesIO(_fetch(url, refresh)))
    text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    table = parse_srd_lines(srd_table_lines(text))
    table = table[table["consistent"]]
    reg = registry(Fetcher(refresh=refresh))
    local = reg[reg["category"] != "C"]
    table["code"] = [match_code(n, local, p) for n, p in zip(table["name"], table["province"])]
    table = table.dropna(subset=["code"]).drop_duplicates("code")
    out = table[["code", "srd_paid", "srd_unpaid", "srd_approved", "srd_pct_paid"]].copy()
    out.insert(1, "period", period)
    out["source"] = f"SASSA SRD statistical report, end of {period}: {url}"
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- 4. DWS Green Drop and Blue Drop

IRIS = "https://ws.dws.gov.za/IRIS/"
IRIS_PAGE = IRIS + "latestresults.aspx"
GD_PROVINCES = ["Eastern Cape", "Free State", "Gauteng", "KwaZulu Natal", "Limpopo", "Mpumalanga",
                "North West", "Northern Cape", "Western Cape"]
BD_PROVINCES = {"EC": "EC", "FS": "FS", "GP": "GT", "KZN": "KZN", "LP": "LIM", "MP": "MP", "NC": "NC",
                "NW": "NW", "WC": "WC"}
_ARROW = "↑↓→←↔="
_GD_ROW = re.compile(r"^(?P<name>[^\d%]+?)\s+(?P<pcts>(?:\d+(?:\.\d+)?%\s*)*)(?P<gd>\d+(?:\.\d+)?)%\s*"
                     r"(?P<arrow>[" + _ARROW + r"])?")
_CRR_ROW = re.compile(r"^(?P<name>[^\d%]*?)\s*(?P<crr>\d+(?:\.\d+)?)%")


def _pdf_text(content: bytes) -> str:
    import pypdf

    return "\n".join((p.extract_text() or "") for p in pypdf.PdfReader(io.BytesIO(content)).pages)


def _table_block(text: str, title: str, size: int = 9000) -> list[str]:
    """Lines after a table title up to the next table or section heading."""
    hit = re.search(re.escape(title).replace(r"\ ", r"\s*") + r"[^\n]*\n", text)
    if not hit:
        return []
    seg = text[hit.end():hit.end() + size]
    stop = re.search(r"\nTable \d+|\n\s*\d+\.\d+\s+[A-Z]", seg)
    return (seg[:stop.start()] if stop else seg).split("\n")


def parse_gd_summary(lines: list[str]) -> dict[str, float]:
    """WSA -> 2024 Green Drop score from a provincial 'Audit Results Summary' table.

    A row counts only when the 2024 score carries a trend arrow or follows two
    earlier scores; rows with a single old score belong to councils that no
    longer exist (for example Randfontein LM, 2013 only).
    """
    out, prev = {}, ""
    for line in (l.strip() for l in lines):
        m = _GD_ROW.match(line)
        if m and not m.group("name").strip().startswith(("Page", "WSA", "Provincial", "National")):
            earlier = len(re.findall(r"%", m.group("pcts") or ""))
            if m.group("arrow") or earlier >= 2:
                name = m.group("name").strip().rstrip("*").strip()
                if not _key(name) or name in {"LM", "DM", "MM"}:
                    name = f"{prev} {name}"
                out[name] = float(m.group("gd"))
        prev = line
    return out


def parse_crr(lines: list[str]) -> dict[str, float]:
    """WSA -> 2024 average %CRR/CRRmax (wastewater risk; higher is worse), current block only.

    DWS lists only WSAs that have at least one works in the high or critical
    band, so a WSA missing here has all its works at low or medium risk.
    """
    out, prev = {}, ""
    for line in (l.strip() for l in lines):
        if re.match(r"WSA Name 20(?!24)\d\d", line):  # the previous cycle's block starts here
            break
        m = _CRR_ROW.match(line)
        if m and not line.startswith(("Provincial", "WSA", "Critical")):
            name = m.group("name").strip()
            if not _key(name) or name in {"LM", "DM", "MM"}:
                name = f"{prev} {name}".strip()
            if _key(name):
                out[name] = float(m.group("crr"))
        prev = line
    return out


def parse_bdrr(text: str) -> dict[str, float]:
    """WSA -> municipal Blue Drop Risk Rating % from the per-WSA 'Institutional Scores' boxes."""
    lines = text.split("\n")
    head = re.compile(r"^\s*\d+\.\d+\.?\s+(.+?)\s*$")
    out = {}
    for i, line in enumerate(lines):
        if not line.strip().startswith("Institutional Scores"):
            continue
        name = next((head.match(lines[j]).group(1) for j in range(i - 1, max(0, i - 15), -1)
                     if head.match(lines[j]) and "..." not in lines[j]), None)
        for j in range(i + 1, min(len(lines), i + 8)):
            m = re.search(r"20\d\d\s*BDRR\s*([\d.]+)\s*%", lines[j])
            if m and name:
                out[name] = float(m.group(1))
                break
    return out


def bdrr_category(x: float | None) -> str | None:
    """DWS Blue Drop risk bands: low <50, medium 50 to <70, high 70 to <90, critical 90 to 100."""
    if x is None or pd.isna(x):
        return None
    return "low" if x < 50 else "medium" if x < 70 else "high" if x < 90 else "critical"


def water_quality(refresh: bool = False) -> tuple[pd.DataFrame, dict]:
    """Green Drop 2025 and Blue Drop 2025 results per water services authority (WSA).

    Returns (table, report). Table columns: code, wsa_name, green_drop_score
    (%, 2024 audit, higher is better), green_drop_risk (average %CRR/CRRmax,
    higher is worse), blue_drop_risk (municipal BDRR %, higher is worse),
    blue_drop_risk_category, report_year, period, source.

    green_drop_risk is empty when DWS lists no works of that WSA in the high
    or critical band. Only WSAs are scored. Where a district is the WSA (for
    example OR Tambo DC15), its local councils (EC157 and others) have no row
    of their own; callers can fall back to the parent district via
    registry()["district"]. The report dict gives coverage (direct, and
    including councils served by a district WSA) and unmatched names.
    """
    html = _fetch(IRIS_PAGE, refresh=True, verify=False, cache=False).decode("utf-8", "ignore")
    links = list(dict.fromkeys(re.findall(r"href='(releases/[^']+\.pdf)", html)))
    reg = registry(Fetcher(refresh=refresh))
    gd, crr, bd, unmatched, used = {}, {}, {}, [], []

    def get(link: str) -> str:
        url = IRIS + urllib.parse.quote(link)
        used.append(url)
        return _pdf_text(_fetch(url, refresh, timeout=600, verify=False))

    for prov in GD_PROVINCES:
        code_p = PROVINCES[prov.upper()]
        link = next((l for l in links if re.search(rf"GD\d\d Report_{prov}_", l, re.I)), None)
        if link is None:
            continue
        text = get(link)
        for name, v in parse_gd_summary(_table_block(text, f"{prov} 2024 Green Drop Audit Results Summary")).items():
            c = match_code(name, reg, code_p)
            if c:
                gd.setdefault(c, (name, v))
            else:
                unmatched.append(f"GD {prov}: {name}")
        for name, v in parse_crr(_table_block(text, "%CRR/CRRmax scores and WWTWs in critical")).items():
            c = match_code(name, reg, code_p)
            if c:
                crr.setdefault(c, v)
    for link in links:
        m = re.search(r"/(?:FIN|fin)_([A-Z]{2,3})_20\d\d BD PAT", link)
        if not m:
            continue
        code_p = BD_PROVINCES[m.group(1)]
        for name, v in parse_bdrr(get(link)).items():
            c = match_code(name, reg, code_p)
            if c:
                bd.setdefault(c, (name, v))
            else:
                unmatched.append(f"BD {m.group(1)}: {name}")
    codes = sorted(set(gd) | set(bd))
    out = pd.DataFrame({
        "code": codes,
        "wsa_name": [(gd.get(c) or bd.get(c))[0] for c in codes],
        "green_drop_score": [gd[c][1] if c in gd else None for c in codes],
        "green_drop_risk": [crr.get(c) for c in codes],
        "blue_drop_risk": [bd[c][1] if c in bd else None for c in codes],
    })
    out["blue_drop_risk_category"] = out["blue_drop_risk"].map(bdrr_category)
    out["report_year"] = 2025
    out["period"] = "Green Drop 2025 (2024 audit); Blue Drop 2025 PAT (2024 data)"
    out["source"] = f"DWS IRIS {IRIS_PAGE}: GD25 provincial reports and 2025 BD PAT provincial reports"
    councils = reg.drop_duplicates("code")
    covered = councils["code"].isin(out["code"]) | councils["district"].isin(out["code"])
    report = {"wsas": len(out), "with_green_drop": int(out["green_drop_score"].notna().sum()),
              "with_blue_drop": int(out["blue_drop_risk"].notna().sum()), "municipalities": len(councils),
              "covered_directly": int(councils["code"].isin(out["code"]).sum()),
              "covered_incl_district_wsa": int(covered.sum()), "unmatched": unmatched, "files": used}
    return out, report


# ---------------------------------------------------------------- 5. Eskom

ESKOM = "https://loadshedding.eskom.co.za/LoadShedding/GetStatus"


def parse_eskom(text: str) -> int | None:
    """Eskom returns the stage plus one (1 means no loadshedding); -1 or junk means unknown."""
    try:
        n = int(str(text).strip().strip('"'))
    except ValueError:
        return None
    return n - 1 if n >= 1 else None


def eskom_status() -> pd.DataFrame:
    """Current national loadshedding stage. Never cached.

    Columns: code ('ZA'), period (UTC timestamp of the check), stage (0 means
    none, None if Eskom's answer was not a number), raw, source.
    """
    last: Exception | None = None
    for attempt in range(3):
        try:
            raw = _fetch(ESKOM, cache=False, timeout=30).decode("utf-8", "ignore").strip()
            break
        except httpx.HTTPError as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"Eskom status unavailable: {last}")
    return pd.DataFrame([{"code": "ZA", "period": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                          "stage": parse_eskom(raw), "raw": raw, "source": ESKOM}])


__all__ = ["spatial_tax", "spatial_tax_jobs_series", "population_2026", "srd_grants", "water_quality",
           "eskom_status", "registry", "match_code"]
