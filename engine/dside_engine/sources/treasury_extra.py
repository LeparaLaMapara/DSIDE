"""More from National Treasury Municipal Money: debts, grants, spending so far, leaders, cash.

All figures come from the raw OLAP cubes at municipaldata.treasury.gov.za.
Things worth knowing before reading the numbers:

* Treasury labels a financial year by the year it ends. Year 2026 is the
  2025/26 financial year (1 July 2025 to 30 June 2026).
* Monthly rows have period_length.length = month and financial_period.period
  1..12, where 1 is July and 12 is June.
* Monthly income, spending, capital and grant rows are amounts for that one
  month, not running totals. Year to date is the sum of the months. Revenue
  and expenditure are both positive numbers; corrections show up as negative
  months.
* Aged debtor and creditor rows are balances at the end of the month, so only
  the latest month is used (never summed).
* The API refuses a cut on a text field with more than one value, and reads a
  bare code like 0120 as a number. Text values are therefore quoted and one
  item is fetched per call; anything else is filtered here.

Each public function takes a Fetcher and returns a tidy DataFrame keyed by
`code` (the Treasury demarcation code, for example TSH). The pure helpers
under them do the reshaping and are tested offline.
"""

from __future__ import annotations

import re

import pandas as pd

from ..http import Fetcher
from .municipal_money import CUBES, aggregate

MONTHS = ["July", "August", "September", "October", "November", "December",
          "January", "February", "March", "April", "May", "June"]

DEBTOR_AGES = ["l30_amount", "l60_amount", "l90_amount", "l120_amount", "l150_amount",
               "l180_amount", "l1_amount", "g1_amount", "total_amount"]
# aged_debtor_v2 item codes. The customer group block (2200 to 2600) only has
# the municipality total row; the income source block (1200 to 2000) also has
# one row per detailed customer_group code, so only the blank group is used.
DEBTOR_ITEMS = {
    "2000": "total", "2600": "total_by_group",
    "2400": "households", "2300": "business", "2200": "government", "2500": "other_customers",
    "1200": "water", "1300": "electricity", "1400": "rates", "1500": "sewage", "1600": "refuse",
    "1700": "rent", "1810": "interest", "1820": "recoverable_wasteful", "1900": "other_services",
}
CREDITOR_ITEMS = {"1000": "total", "0100": "eskom", "0200": "water_boards", "0700": "trade",
                  "0300": "paye", "0500": "pensions", "0800": "auditor_general"}
OFFICIAL_ROLES = {"Mayor/Executive Mayor": "mayor", "Municipal Manager": "municipal_manager",
                  "Chief Financial Officer": "cfo", "Speaker": "speaker"}
PERSONAL_MAIL = re.compile(r"@(gmail|yahoo|ymail|hotmail|outlook|live|icloud|me|aol|webmail|telkomsa|vodamail|"
                           r"mweb|iafrica|lantic|absamail|protonmail)\.", re.I)
MOBILE = re.compile(r"^(\+?27|0)\s*(6|7|8[1-4])")


# ---------------------------------------------------------------- helpers

def period_label(year: int, period: int) -> str:
    """Treasury (financial year end, month 1..12) to a calendar label, e.g. (2026, 9) -> 'March 2026'."""
    month = MONTHS[period - 1]
    return f"{month} {year - 1 if period <= 6 else year}"


def financial_year(year: int) -> str:
    """2026 -> '2025/26'."""
    return f"{year - 1}/{str(year)[-2:]}"


def _q(value: str) -> str:
    """Quote a text cut value so codes with leading zeros stay text."""
    return f'"{value}"'


def _cells(f: Fetcher, cube: str, aggregates: str, cut: str, drilldown: str, page_size: int = 10000) -> list[dict]:
    """Like municipal_money.aggregate but for any measure list (debtor cubes have no `amount`)."""
    cells, page = [], 1
    while True:
        data = f.get(f"{CUBES}/{cube}/aggregate?aggregates={aggregates}&cut={cut}"
                     f"&drilldown={drilldown}&pagesize={page_size}&page={page}")
        batch = data.get("cells", [])
        cells += batch
        if len(batch) < page_size or len(cells) >= data.get("total_cell_count", 0):
            return cells
        page += 1


def _tidy(cells: list[dict]) -> pd.DataFrame:
    """Cells to a frame with dots in the API names replaced by underscores."""
    df = pd.DataFrame(cells)
    return df.rename(columns=lambda c: c.replace(".", "_"))


def latest_year(f: Fetcher, cube: str) -> int:
    return max(m["financial_year_end.year"] for m in f.get(f"{CUBES}/{cube}/members/financial_year_end")["data"])


def latest_month(cells: list[dict] | pd.DataFrame, value: str) -> pd.DataFrame:
    """Per municipality, the latest (year, period) whose `value` is non zero.

    Expects columns demarcation_code, financial_year_end_year, financial_period_period.
    """
    df = cells if isinstance(cells, pd.DataFrame) else _tidy(cells)
    df = df[pd.to_numeric(df[value], errors="coerce").fillna(0) != 0]
    df = df.sort_values(["demarcation_code", "financial_year_end_year", "financial_period_period"])
    last = df.groupby("demarcation_code").tail(1)
    return last[["demarcation_code", "financial_year_end_year", "financial_period_period"]].rename(
        columns={"demarcation_code": "code", "financial_year_end_year": "year", "financial_period_period": "month"}
    ).reset_index(drop=True)


def _balances_at(f: Fetcher, cube: str, aggregates: str, drill: str, latest: pd.DataFrame) -> pd.DataFrame:
    """Balance cells for each municipality at its own latest month (one query per distinct month)."""
    frames = []
    for (y, p), group in latest.groupby(["year", "month"]):
        cut = f"financial_year_end.year:{y}|financial_period.period:{p}|period_length.length:month|amount_type.code:ACT"
        cells = _tidy(_cells(f, cube, aggregates, cut, f"demarcation.code|{drill}"))
        if cells.empty:
            continue
        cells = cells[cells["demarcation_code"].isin(set(group["code"]))]
        frames.append(cells.assign(year=y, month=p))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


# ---------------------------------------------------------------- debtors

def debtors_table(cells: pd.DataFrame) -> pd.DataFrame:
    """Aged debtor cells (one latest month per code) to one row per municipality.

    `cells` has demarcation_code, item_code, customer_group_code, year, month
    and the *_amount_sum age columns. Only the blank customer group is used,
    because that row already holds the municipality total for every item.
    """
    c = cells[cells["customer_group_code"].fillna("") == ""].copy()
    c = c[c["item_code"].isin(DEBTOR_ITEMS)]
    for col in [a + "_sum" for a in DEBTOR_AGES]:
        c[col] = pd.to_numeric(c[col], errors="coerce").fillna(0.0) if col in c else 0.0
    c["over_90d"] = c[[a + "_sum" for a in ["l120_amount", "l150_amount", "l180_amount", "l1_amount", "g1_amount"]]].sum(axis=1)
    rows = []
    for (code, y, p), g in c.groupby(["demarcation_code", "year", "month"]):
        by = g.set_index("item_code")
        val = lambda item, col="total_amount_sum": float(by[col].get(item, 0.0)) if item in by.index else None
        total = val("2000") or val("2600")
        rows.append({
            "code": code, "year": int(y), "month": int(p), "period": period_label(int(y), int(p)),
            "owed_total": total,
            "owed_households": val("2400"), "owed_business": val("2300"),
            "owed_government": val("2200"), "owed_other_customers": val("2500"),
            "owed_current_30d": val("2000", "l30_amount_sum"),
            "owed_over_90d": val("2000", "over_90d"),
            "owed_over_1yr": val("2000", "g1_amount_sum"),
            "owed_water": val("1200"), "owed_electricity": val("1300"), "owed_rates": val("1400"),
            "owed_sewage": val("1500"), "owed_refuse": val("1600"), "owed_interest": val("1810"),
            "owed_other_services": sum(v or 0.0 for v in (val("1700"), val("1820"), val("1900"))),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out["share_over_1yr"] = out["owed_over_1yr"] / out["owed_total"].where(out["owed_total"] > 0)
    return out


def debtors(f: Fetcher) -> pd.DataFrame:
    """Who owes each municipality, at that municipality's latest reported month.

    Columns: code, year, month, period ('March 2026'), owed_total,
    owed_households, owed_business, owed_government, owed_other_customers,
    owed_current_30d, owed_over_90d, owed_over_1yr, share_over_1yr,
    owed_water, owed_electricity, owed_rates, owed_sewage, owed_refuse,
    owed_interest, owed_other_services, source. Rand amounts.
    """
    cube = "aged_debtor_v2"
    y = latest_year(f, cube)
    months = _cells(f, cube, "total_amount.sum",
                    f"period_length.length:month|amount_type.code:ACT|financial_year_end.year:{y - 1};{y}",
                    "demarcation.code|financial_year_end.year|financial_period.period")
    latest = latest_month(months, "total_amount_sum")
    aggs = "|".join(a + ".sum" for a in DEBTOR_AGES)
    cells = _balances_at(f, cube, aggs, "item.code|customer_group.code", latest)
    out = debtors_table(cells)
    out["source"] = f"{CUBES}/{cube} (monthly Section 71 aged debtors, amount_type ACT)"
    return out


# ---------------------------------------------------------------- creditors

def creditors_table(cells: pd.DataFrame) -> pd.DataFrame:
    """Aged creditor cells (one latest month per code) to one row per municipality."""
    c = cells[cells["item_code"].isin(CREDITOR_ITEMS)].copy()
    for col in ["total_amount_sum", "l30_amount_sum", "l60_amount_sum", "l90_amount_sum"]:
        c[col] = pd.to_numeric(c[col], errors="coerce").fillna(0.0) if col in c else 0.0
    c["over_90d"] = c["total_amount_sum"] - c["l30_amount_sum"] - c["l60_amount_sum"] - c["l90_amount_sum"]
    rows = []
    for (code, y, p), g in c.groupby(["demarcation_code", "year", "month"]):
        by = g.set_index("item_code")
        val = lambda item, col="total_amount_sum": float(by[col][item]) if item in by.index else None
        rows.append({
            "code": code, "year": int(y), "month": int(p), "period": period_label(int(y), int(p)),
            "owes_total": val("1000"), "owes_over_90d": val("1000", "over_90d"),
            "owes_eskom": val("0100"), "owes_eskom_over_90d": val("0100", "over_90d"),
            "owes_water_boards": val("0200"), "owes_water_boards_over_90d": val("0200", "over_90d"),
            "owes_trade": val("0700"), "owes_auditor_general": val("0800"),
            "owes_staff_deductions": sum(v or 0.0 for v in (val("0300"), val("0500"))),
        })
    return pd.DataFrame(rows)


def creditors(f: Fetcher) -> pd.DataFrame:
    """What each municipality owes its suppliers at its latest reported month.

    Columns: code, year, month, period, owes_total, owes_over_90d,
    owes_eskom (bulk electricity), owes_eskom_over_90d, owes_water_boards
    (bulk water), owes_water_boards_over_90d, owes_trade,
    owes_auditor_general, owes_staff_deductions (PAYE and pensions), source.
    """
    cube = "aged_creditor_v2"
    y = latest_year(f, cube)
    months = _cells(f, cube, "total_amount.sum",
                    f"period_length.length:month|amount_type.code:ACT|financial_year_end.year:{y - 1};{y}"
                    f"|item.code:{_q('1000')}",
                    "demarcation.code|financial_year_end.year|financial_period.period")
    latest = latest_month(months, "total_amount_sum")
    cells = _balances_at(f, cube, "total_amount.sum|l30_amount.sum|l60_amount.sum|l90_amount.sum",
                         "item.code", latest)
    out = creditors_table(cells)
    out["source"] = f"{CUBES}/{cube} (monthly Section 71 aged creditors, amount_type ACT)"
    return out


# ---------------------------------------------------------------- grants

def grants_table(cells: pd.DataFrame, labels: dict[str, str], year: int) -> pd.DataFrame:
    """grants_v2 cells for one year to one row per municipality per grant."""
    c = cells.copy()
    c["amount_sum"] = pd.to_numeric(c["amount_sum"], errors="coerce")
    annual = c[c["period_length_length"] == "year"].pivot_table(
        index=["demarcation_code", "grant_code"], columns="amount_type_code", values="amount_sum", aggfunc="sum")
    monthly = c[(c["period_length_length"] == "month") & (c["amount_type_code"] == "ACT")]
    spent = monthly.groupby(["demarcation_code", "grant_code"])["amount_sum"].sum(min_count=1)
    reported = monthly[monthly["amount_sum"].fillna(0) != 0]
    months = reported.groupby("demarcation_code")["financial_period_period"].max()
    out = pd.DataFrame(index=annual.index.union(spent.index))
    get = lambda t: annual[t].reindex(out.index) if t in annual else pd.Series(float("nan"), index=out.index)
    adj, org = get("ADJB"), get("ORGB")
    out["budget"] = adj.where(adj.notna() & (adj != 0), org)
    out["budget_type"] = pd.Series("ADJB", index=out.index).where(adj.notna() & (adj != 0), "ORGB").where(out["budget"].notna())
    out["transferred"] = get("TRFR")
    out["scheduled"] = get("SCHD")
    out["spent"] = spent.reindex(out.index)
    out = out.reset_index().rename(columns={"demarcation_code": "code", "grant_code": "grant_code"})
    out = out[out[["budget", "transferred", "scheduled", "spent"]].fillna(0).ne(0).any(axis=1)]
    out["grant"] = out["grant_code"].map(labels).replace("", None).fillna(out["grant_code"])
    out["year"] = year
    out["financial_year"] = financial_year(year)
    out["months_reported"] = out["code"].map(months).fillna(0).astype(int)
    out["spent_share"] = out["spent"] / out["budget"].where(out["budget"] > 0)
    return out[["code", "year", "financial_year", "grant_code", "grant", "budget", "budget_type", "scheduled",
                "transferred", "spent", "spent_share", "months_reported"]].reset_index(drop=True)


def grants(f: Fetcher, year: int | None = None) -> pd.DataFrame:
    """Per municipality per grant for the latest year: budget, transferred, spent so far.

    Columns: code, year, financial_year, grant_code, grant, budget (adjusted,
    or original when no adjusted budget), budget_type, scheduled (national
    payment schedule), transferred (TRFR), spent (sum of monthly actuals so
    far), spent_share, months_reported, source. Monthly spending can have
    negative correction months; the sum is what the municipality reported.
    """
    cube = "grants_v2"
    y = year or latest_year(f, cube)
    labels = {m["grant.code"]: m["grant.label"] for m in f.get(f"{CUBES}/{cube}/members/grant")["data"]}
    cells = _tidy(aggregate(f, cube, f"financial_year_end.year:{y}",
                            "demarcation.code|grant.code|period_length.length|amount_type.code|financial_period.period"))
    out = grants_table(cells, labels, y)
    out["source"] = f"{CUBES}/{cube}"
    return out


# ---------------------------------------------------------------- year to date

def _budget(annual: pd.DataFrame, col: str) -> tuple[pd.Series, pd.Series]:
    """Adjusted budget where there is one, else original. Returns (amount, type)."""
    adj = annual.get(("ADJB", col)) if ("ADJB", col) in annual else pd.Series(dtype=float)
    org = annual.get(("ORGB", col)) if ("ORGB", col) in annual else pd.Series(dtype=float)
    idx = adj.index.union(org.index)
    adj, org = adj.reindex(idx), org.reindex(idx)
    use_adj = adj.notna() & (adj != 0)
    return adj.where(use_adj, org), pd.Series("ADJB", index=idx).where(use_adj, "ORGB")


def year_to_date_table(incexp: pd.DataFrame, capital: pd.DataFrame, year: int) -> pd.DataFrame:
    """Monthly income, spending and capital cells for one year to one row per municipality.

    `incexp` needs demarcation_code, measure ('revenue' or 'spending'),
    period_length_length, amount_type_code, financial_period_period, amount_sum.
    `capital` the same with capital_type_label instead of measure.
    """
    inc = incexp.copy()
    cap = capital[capital["capital_type_label"].isin(["New", "Renewal", "Upgrading"])].copy()
    cap["measure"] = "capital"
    both = pd.concat([inc, cap], ignore_index=True)
    both["amount_sum"] = pd.to_numeric(both["amount_sum"], errors="coerce").fillna(0.0)
    month = both[(both["period_length_length"] == "month") & (both["amount_type_code"] == "ACT")]
    per_month = month.groupby(["demarcation_code", "measure", "financial_period_period"])["amount_sum"].sum()
    ytd = per_month.groupby(level=[0, 1]).sum().unstack("measure")
    annual = both[both["period_length_length"] == "year"].groupby(
        ["demarcation_code", "amount_type_code", "measure"])["amount_sum"].sum().unstack(["amount_type_code", "measure"])

    rev = per_month.xs("revenue", level="measure") if "revenue" in per_month.index.get_level_values(1) else pd.Series(dtype=float)
    spend = per_month.xs("spending", level="measure") if "spending" in per_month.index.get_level_values(1) else pd.Series(dtype=float)
    reported = rev[rev != 0].reset_index().groupby("demarcation_code")["financial_period_period"]
    codes = sorted(set(ytd.index) | set(annual.index))
    out = pd.DataFrame(index=pd.Index(codes, name="code"))
    out["year"] = year
    out["financial_year"] = financial_year(year)
    out["months_reported"] = reported.nunique().reindex(out.index).fillna(0).astype(int)
    last = reported.max().reindex(out.index)
    out["latest_month"] = [period_label(year, int(p)) if pd.notna(p) else None for p in last]
    # Months whose revenue and spending repeat the month before are a
    # known reporting artefact (a copy submitted twice); they are counted, not dropped.
    pair = pd.concat({"r": rev, "s": spend}, axis=1).dropna()
    rep = {}
    for code, g in pair.groupby(level=0):
        g = g.droplevel(0).sort_index()
        close = lambda s: (s - s.shift()).abs() <= s.abs() * 1e-6 + 1  # copies can differ by a rand of rounding
        same = close(g["r"]) & close(g["s"]) & (g["r"] != 0)
        rep[code] = int(same.sum())
    out["repeated_months"] = pd.Series(rep).reindex(out.index).fillna(0).astype(int)
    for measure in ["revenue", "spending", "capital"]:
        out[f"{measure}_ytd"] = ytd[measure].reindex(out.index) if measure in ytd else float("nan")
        budget, kind = _budget(annual, measure) if len(annual) else (pd.Series(dtype=float), pd.Series(dtype=object))
        out[f"{measure}_budget"] = budget.reindex(out.index)
        out[f"{measure}_budget_type"] = kind.reindex(out.index).where(out[f"{measure}_budget"].notna())
        out[f"{measure}_ytd_share"] = out[f"{measure}_ytd"] / out[f"{measure}_budget"].where(out[f"{measure}_budget"] > 0)
    out["expected_share"] = out["months_reported"] / 12
    return out.reset_index()


def year_to_date(f: Fetcher, year: int | None = None) -> pd.DataFrame:
    """Operating income, operating spending and capital spent so far this financial year vs budget.

    Uses monthly actuals (ACT) from incexp_v2 items 2900 (total revenue
    excluding capital transfers) and 4400 (total expenditure), and capital_v2
    New + Renewal + Upgrading. Monthly rows are single-month amounts, so year
    to date is their sum. Budget is the full-year adjusted budget, or the
    original when no adjustments budget was filed.

    Columns: code, year, financial_year, months_reported, latest_month,
    repeated_months, revenue_ytd, revenue_budget, revenue_budget_type,
    revenue_ytd_share, spending_* (same four), capital_* (same four),
    expected_share (months_reported / 12), source.
    """
    y = year or latest_year(f, "incexp_v2")
    frames = []
    for item, measure in [("2900", "revenue"), ("4400", "spending")]:
        cells = _tidy(aggregate(f, "incexp_v2", f"financial_year_end.year:{y}|item.code:{_q(item)}",
                                "demarcation.code|period_length.length|amount_type.code|financial_period.period"))
        frames.append(cells.assign(measure=measure))
    capital = _tidy(aggregate(f, "capital_v2", f"financial_year_end.year:{y}",
                              "demarcation.code|capital_type.label|period_length.length|amount_type.code|financial_period.period"))
    out = year_to_date_table(pd.concat(frames, ignore_index=True), capital, y)
    out["source"] = f"{CUBES}/incexp_v2 and {CUBES}/capital_v2 (monthly ACT, annual ADJB/ORGB)"
    return out


# ---------------------------------------------------------------- officials

def officials_table(facts: list[dict]) -> pd.DataFrame:
    """officials facts to one row per municipality per leadership role, work contacts only.

    Secretaries and deputy mayors are left out. An email on a personal mail
    service and a mobile number are blanked, so only office contacts remain.
    """
    rows = []
    for r in facts:
        role = r.get("role.role")
        if role not in OFFICIAL_ROLES:
            continue
        email = (r.get("contact_details.email_address") or "").strip()
        phone = re.sub(r"\s+", " ", (r.get("contact_details.phone_number") or "").strip())
        name = re.sub(r"\s+", " ", (r.get("contact_details.name") or "").strip())
        rows.append({
            "code": r.get("municipality.demarcation_code"),
            "role_key": OFFICIAL_ROLES[role], "role": role,
            "title": (r.get("contact_details.title") or "").strip() or None,
            "name": name or None,
            "office_phone": phone if phone and not MOBILE.match(phone) else None,
            "email": email.lower() if email and "@" in email and not PERSONAL_MAIL.search(email) else None,
        })
    return pd.DataFrame(rows).drop_duplicates(["code", "role_key"]).sort_values(["code", "role_key"]).reset_index(drop=True)


def officials(f: Fetcher) -> pd.DataFrame:
    """Mayor, municipal manager, CFO and speaker per municipality, with office phone and work email.

    Columns: code, role_key (mayor, municipal_manager, cfo, speaker), role,
    title, name, office_phone, email, source. Treasury refreshes this list
    from municipal submissions; a name can lag a recent change.
    """
    facts, page = [], 1
    while True:
        data = f.get(f"{CUBES}/officials/facts?pagesize=5000&page={page}")
        facts += data["data"]
        if len(facts) >= data["total_fact_count"] or not data["data"]:
            break
        page += 1
    out = officials_table(facts)
    out["source"] = f"{CUBES}/officials"
    return out


# ---------------------------------------------------------------- cash

def cash_table(cash: pd.Series, cash_cflow: pd.Series, spending: pd.Series, depreciation: pd.Series,
               impairment: pd.Series, year: int) -> pd.DataFrame:
    """Audited cash at year end over monthly cash operating spending."""
    idx = cash.index.union(spending.index)
    out = pd.DataFrame(index=pd.Index(idx, name="code"))
    out["year"] = year
    out["financial_year"] = financial_year(year)
    out["cash"] = cash.reindex(idx)
    out["cash_cflow"] = cash_cflow.reindex(idx)
    out["spending"] = spending.reindex(idx)
    non_cash = depreciation.reindex(idx).fillna(0) + impairment.reindex(idx).fillna(0)
    out["monthly_cash_spending"] = (out["spending"] - non_cash) / 12
    out["months_cover"] = out["cash"] / out["monthly_cash_spending"].where(out["monthly_cash_spending"] > 0)
    out["cash_negative"] = out["cash"] < 0
    ratio = out["cash"] / out["cash_cflow"]
    out["statements_agree"] = ((ratio - 1).abs() <= 0.1).where(out["cash"].notna() & out["cash_cflow"].notna())
    return out.reset_index()


def cash(f: Fetcher, year: int | None = None) -> pd.DataFrame:
    """Audited cash and cash equivalents at year end and months of cash cover.

    Cash is financial_position_v2 item 0120 (AUDA). Monthly cash spending is
    incexp_v2 total expenditure (4400) less depreciation (3600) and debt
    impairment (3500), which move no cash, divided by 12. months_cover =
    cash / monthly cash spending. National Treasury's norm is 1 to 3 months.

    The cash flow statement's closing balance (cflow_v2 0430) is kept as
    cash_cflow for comparison only: for most municipalities it does not match
    the balance sheet (for many it is several times larger), while the next
    year's opening balance in cflow_v2 does match the balance sheet, so the
    balance sheet figure is the one used. A negative cash figure means an
    overdrawn bank position as reported.

    Columns: code, year, financial_year, cash, cash_cflow, spending,
    monthly_cash_spending, months_cover, cash_negative, statements_agree, source.
    """
    y = year or max(c["financial_year_end.year"] for c in aggregate(
        f, "financial_position_v2", f"period_length.length:year|amount_type.code:AUDA|item.code:{_q('0120')}",
        "financial_year_end.year") if c.get("amount.sum"))

    def one(cube: str, item: str) -> pd.Series:
        cells = aggregate(f, cube, f"financial_year_end.year:{y}|period_length.length:year|amount_type.code:AUDA"
                                   f"|item.code:{_q(item)}", "demarcation.code")
        return pd.Series({c["demarcation.code"]: c["amount.sum"] for c in cells if c.get("amount.sum") is not None},
                         dtype=float)

    out = cash_table(one("financial_position_v2", "0120"), one("cflow_v2", "0430"), one("incexp_v2", "4400"),
                     one("incexp_v2", "3600"), one("incexp_v2", "3500"), y)
    out["source"] = f"{CUBES}/financial_position_v2 (0120 AUDA) and {CUBES}/incexp_v2 (4400, 3600, 3500 AUDA)"
    return out


__all__ = ["debtors", "creditors", "grants", "year_to_date", "officials", "cash",
           "debtors_table", "creditors_table", "grants_table", "year_to_date_table", "officials_table",
           "cash_table", "latest_month", "period_label", "financial_year"]
