"""Where the money came from, where it went, and whether it was handled well.

Built from Treasury's raw cubes, not from the pre-computed Municipal Money
profiles, because the profiles are broken for recent mSCOA years (for example
Tshwane's 2024 "actual spending" there is R48.9bn against a R6bn budget).

Every municipality gets a plain score from 0 to 100 made of up to five parts.
Each part compares a number to a National Treasury norm (MFMA Circular 71) and
is only used if it passes a plausibility check.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

AUDIT_SCORE = {
    "unqualified": 100,  # clean audit
    "unqualified_emphasis_of_matter": 75,  # books fine, but compliance findings
    "qualified": 40,
    "adverse": 15,
    "disclaimer": 0,
    "outstanding": 0,  # did not even submit on time
}

AUDIT_PLAIN = {
    "unqualified": "Clean audit",
    "unqualified_emphasis_of_matter": "Books OK, rules broken",
    "qualified": "Some books wrong",
    "adverse": "Books badly wrong",
    "disclaimer": "Books could not be checked",
    "outstanding": "Did not hand in books",
}

REVENUE_TOTAL, SPEND_TOTAL = "2900", "4400"
OWN_INCOME = {"0300": "Electricity bills", "0400": "Water bills", "0500": "Sewerage bills",
              "0600": "Rubbish bills", "1800": "Property rates"}
GRANTS = {"2200": "Grants for running costs", "4600": "Grants for building"}
SPEND_ITEMS = {"3100": "Staff salaries", "3200": "Councillor pay", "3300": "Buying electricity (Eskom)",
               "3400": "Water and materials bought", "3500": "Unpaid bills written off",
               "3600": "Wear and tear", "3700": "Interest on debt", "3800": "Contractors",
               "4100": "Other running costs"}
BUILD_TYPES = ["New", "Renewal", "Upgrading"]


def anchor_year(inc: pd.DataFrame, cap: pd.DataFrame, min_share: float = 0.8) -> int:
    """Latest year where most municipalities have both a budget and audited actuals."""
    n = inc["demarcation_code"].nunique()
    best = None
    for y in sorted(inc["year"].unique()):
        have = [
            set(df[(df["year"] == y) & (df["amount_type_code"] == t)]["demarcation_code"])
            for df in (inc, cap) for t in ("ADJB", "AUDA")
        ]
        if len(set.intersection(*have)) >= min_share * n:
            best = int(y)
    if best is None:
        raise ValueError("no year has budget and actuals for most municipalities")
    return best


def _pivot(df: pd.DataFrame, year: int, key: str) -> pd.DataFrame:
    sub = df[df["year"] == year]
    return sub.pivot_table(index="demarcation_code", columns=["amount_type_code", key],
                           values="amount_sum", aggfunc="sum")


def _col(p: pd.DataFrame, amount_type: str, key: str) -> pd.Series:
    try:
        return p[(amount_type, key)]
    except KeyError:
        return pd.Series(np.nan, index=p.index)


def _ramp(x: pd.Series, bad: float, good: float) -> pd.Series:
    """0 at `bad`, 100 at `good`, linear between, clipped."""
    return ((x - bad) / (good - bad)).clip(0, 1) * 100


def money_table(inc: pd.DataFrame, cap: pd.DataFrame, uifw: pd.DataFrame, audits: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    year = anchor_year(inc, cap)
    pi = _pivot(inc, year, "item_code")
    pc = _pivot(cap, year, "capital_type_label")
    out = pd.DataFrame(index=pi.index.union(pc.index))
    out["year"] = year

    out["income_planned"] = _col(pi, "ADJB", REVENUE_TOTAL)
    out["income_actual"] = _col(pi, "AUDA", REVENUE_TOTAL)
    out["spend_planned"] = _col(pi, "ADJB", SPEND_TOTAL)
    out["spend_actual"] = _col(pi, "AUDA", SPEND_TOTAL)
    out["build_planned"] = sum(_col(pc, "ADJB", t).fillna(0) for t in BUILD_TYPES)
    out["build_actual"] = sum(_col(pc, "AUDA", t).fillna(0) for t in BUILD_TYPES)
    out["repairs_actual"] = _col(pc, "AUDA", "Repairs and maintenance")
    for code, name in {**OWN_INCOME, **GRANTS}.items():
        out[f"in:{name}"] = _col(pi, "AUDA", code)
    for code, name in SPEND_ITEMS.items():
        out[f"out:{name}"] = _col(pi, "AUDA", code)
    out = out.replace({"build_planned": {0: np.nan}, "build_actual": {0: np.nan}})

    u = uifw[uifw["financial_year_end_year"] == year].groupby("demarcation_code")["amount_sum"].sum()
    out["wasted"] = u.reindex(out.index)

    a = audits.sort_values("financial_year_end_year")
    latest = a[a["financial_year_end_year"] == year].set_index("demarcation_code")
    out["audit_code"] = latest["opinion_code"].reindex(out.index)
    out["audit_url"] = latest["opinion_report_url"].reindex(out.index)
    history = a.groupby("demarcation_code")["opinion_code"].apply(list)
    out["audit_history"] = history.reindex(out.index)

    # Ratios residents can picture.
    out["build_spent_share"] = out["build_actual"] / out["build_planned"]
    out["income_collected_share"] = out["income_actual"] / out["income_planned"]
    out["wasted_share"] = out["wasted"] / out["spend_actual"]
    bills = sum(out[f"in:{n}"].fillna(0) for n in OWN_INCOME.values())
    out["unpaid_share"] = out["out:Unpaid bills written off"] / bills.replace(0, np.nan)
    out["staff_share"] = out["out:Staff salaries"] / out["spend_actual"]

    out["warnings"] = [[] for _ in range(len(out))]
    _flag(out, "build_spent_share", 0.0, 3.0, "Treasury's building numbers look wrong")
    _flag(out, "income_collected_share", 0.3, 3.0, "Treasury's income numbers look wrong")
    _flag(out, "wasted_share", 0.0, 2.0, "Treasury's wasted-money number looks wrong")
    _flag(out, "unpaid_share", 0.0, 1.5, "Treasury's unpaid-bills number looks wrong")

    parts = pd.DataFrame(index=out.index)
    parts["audit"] = out["audit_code"].map(AUDIT_SCORE)
    parts["build"] = _ramp(out["build_spent_share"], 0.4, 0.95)
    parts["wasted"] = _ramp(out["wasted_share"], 0.20, 0.0)
    parts["unpaid"] = _ramp(out["unpaid_share"], 0.30, 0.05)
    parts["income"] = _ramp(out["income_collected_share"], 0.70, 0.95)
    enough = parts.notna().sum(axis=1) >= 3
    out["money_score"] = parts.mean(axis=1).where(enough).round(0)
    for c in parts:
        out[f"money_part:{c}"] = parts[c].round(0)
    return out.reset_index(names="code"), year


def _flag(out: pd.DataFrame, col: str, lo: float, hi: float, message: str) -> None:
    bad = out[col].notna() & ~out[col].between(lo, hi)
    for i in out.index[bad]:
        out.at[i, "warnings"] = out.at[i, "warnings"] + [message]
    out.loc[bad, col] = np.nan


def planned_by_service(inc_fn: pd.DataFrame, year: int) -> pd.DataFrame:
    """Planned (adjusted budget) operating spending grouped into services people know.

    Uses the budget, not the audited actuals, because Treasury's audited
    spending by function is internally inconsistent (negative water spending
    and similar) for most municipalities.
    """
    sub = inc_fn[(inc_fn["year"] == year) & (inc_fn["amount_type_code"] == "ADJB")].copy()
    sub["service"] = sub["function_label"].map(service_bucket)
    return (sub.groupby(["demarcation_code", "service"])["amount_sum"].sum()
            .clip(lower=0).reset_index().rename(columns={"demarcation_code": "code", "amount_sum": "amount"}))


def service_bucket(label: str) -> str:
    s = (label or "").lower()
    for bucket, words in [
        ("Toilets and sewage", ["sewerage", "waste water", "sanitation", "storm water"]),
        ("Water", ["water"]),
        ("Electricity", ["electric", "street lighting", "energy"]),
        ("Roads and transport", ["road", "transport", "traffic"]),
        ("Rubbish", ["solid waste", "refuse", "cleansing", "waste management"]),
        ("Houses", ["housing", "informal settlement"]),
        ("Safety and emergencies", ["police", "fire", "disaster", "ambulance", "security", "civil defence"]),
        ("Clinics, parks and community", ["health", "communit", "librar", "sport", "recreation", "park",
                                           "cemeter", "social", "child", "aged", "museum", "cultur", "beach"]),
        ("Jobs and local economy", ["economic", "tourism", "market", "agricult", "abattoir", "develop"]),
    ]:
        if any(w in s for w in words):
            return bucket
    return "Running the office"
