"""Join the newer public data onto each municipality and ward.

Everything here is a join or a simple ratio; no new models. Where a figure is
only published for a larger area (population for districts, water quality for
the water services authority), the municipality gets the larger area's value
and a note saying so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ROLE_ORDER = ["mayor", "speaker", "municipal_manager", "cfo"]


def _one(df: pd.DataFrame, cols: list[str], rename: dict[str, str] | None = None) -> pd.DataFrame:
    return df.drop_duplicates("code").set_index("code")[cols].rename(columns=rename or {})


def municipal(meta: pd.DataFrame, raw: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, dict[str, dict]]:
    """Flat columns per municipality, plus nested lists keyed by code."""
    out = pd.DataFrame(index=meta.index)

    y = raw["year_to_date"]
    out = out.join(_one(y, ["financial_year", "months_reported", "latest_month", "revenue_ytd", "revenue_budget",
                            "spending_ytd", "spending_budget", "capital_ytd", "capital_budget", "capital_ytd_share",
                            "expected_share"], {c: f"ytd_{c}" for c in y.columns}))
    d = raw["debtors"]
    out = out.join(_one(d, ["owed_total", "owed_households", "owed_business", "owed_government", "owed_over_1yr",
                            "owed_water", "owed_electricity", "owed_rates", "period"], {"period": "owed_period"}))
    c = raw["creditors"]
    out = out.join(_one(c, ["owes_total", "owes_eskom", "owes_water_boards", "period"], {"period": "owes_period"}))
    k = raw["cash"]
    out = out.join(_one(k, ["cash", "months_cover", "financial_year"], {"financial_year": "cash_year"}))
    out = out.join(_one(raw["census_extras"], ["rdp_household_share", "female_headed_share"]))

    j = raw["jobs_2025"]
    out = out.join(_one(j, ["formal_jobs", "youth_jobs", "median_income", "youth_median_income", "establishments",
                            "period"], {"period": "jobs_year"}))
    series = raw["jobs_series"].sort_values("period")
    prev = series.groupby("code").nth(-2).set_index("code")["formal_jobs"]
    out["formal_jobs_before"] = prev.reindex(out.index)

    # Population 2026 is published for districts and metros; locals get their district's.
    p = raw["population_2026"]
    p = p[p["period"].astype(str) == "2026"].drop_duplicates("code").set_index("code")
    area = pd.Series(np.where(meta["kind"] == "local", meta["parent"], meta.index), index=meta.index)
    out["pop_2026"] = area.map(p["population"])
    out["youth_2026"] = area.map(p["youth_15_34"])
    out["pop_2026_level"] = np.where(meta["kind"] == "local", "district", "this municipality")

    s = raw["srd_grants"]
    out = out.join(_one(s, ["srd_paid", "srd_approved", "period"], {"period": "srd_period"}))

    w = raw["water_quality"].drop_duplicates("code").set_index("code")
    for col in ["green_drop_score", "green_drop_risk", "blue_drop_risk", "blue_drop_risk_category", "report_year"]:
        own = meta.index.to_series().map(w[col])
        district = meta["parent"].map(w[col])
        out[col] = own.fillna(district)
    out["water_quality_level"] = np.where(meta.index.to_series().map(w["green_drop_score"]).notna(),
                                          "this municipality", np.where(out["green_drop_score"].notna(), "district", None))

    nested: dict[str, dict] = {code: {} for code in meta.index}
    o = raw["officials"]
    o = o[o["role_key"].isin(ROLE_ORDER)].assign(order=lambda x: x["role_key"].map(ROLE_ORDER.index))
    for code, g in o.sort_values("order").groupby("code"):
        if code in nested:
            nested[code]["officials"] = g[["role_key", "role", "name", "office_phone", "email"]].to_dict("records")
    gr = raw["grants"]
    # The equitable share is general income, not a project grant, and in-kind
    # grants are spent by national departments; neither has spending to track.
    gr = gr[(gr["budget"] > 0) & ~gr["grant"].str.contains("Equitable Share|in-kind", case=False, na=False)]
    gr = gr.sort_values("budget", ascending=False)
    for code, g in gr.groupby("code"):
        if code in nested:
            nested[code]["grants"] = g.head(6)[["grant", "budget", "spent", "spent_share", "financial_year"]].to_dict("records")
    q = raw["gcro"]
    for code, g in q.groupby("code"):
        if code in nested:
            nested[code]["residents_say"] = g[["question", "share", "year"]].to_dict("records")
    siu = raw["siu"].dropna(subset=["code"]).sort_values("date", ascending=False).assign(date=lambda x: x["date"].astype(str))
    for code, g in siu.groupby("code"):
        if code in nested:
            nested[code]["siu"] = g.head(5)[["proclamation", "date", "title", "link"]].to_dict("records")
    out["siu_cases"] = siu.groupby("code").size().reindex(out.index)
    recent = siu[pd.to_datetime(siu["date"], errors="coerce") >= pd.Timestamp.now() - pd.DateOffset(years=3)]
    out["siu_recent"] = recent.groupby("code").size().reindex(out.index)
    return out, nested


def schools_table(schools: pd.DataFrame, matric: pd.DataFrame) -> pd.DataFrame:
    latest = matric["year"].max()
    m = matric[matric["year"] == latest].drop_duplicates("emis").set_index("emis")
    s = schools.dropna(subset=["code"]).copy()
    s["matric_year"] = latest
    for col in ["wrote", "passed", "pass_rate"]:
        s[f"matric_{col}"] = s["emis"].map(m[col])
    keep = ["emis", "name", "phase", "sector", "no_fee", "quintile", "learners", "suburb", "lat", "lng", "code", "ward_id",
            "matric_year", "matric_wrote", "matric_passed", "matric_pass_rate"]
    return s[keep].reset_index(drop=True)


def schools_by_muni(schools: pd.DataFrame) -> pd.DataFrame:
    g = schools.groupby("code")
    out = pd.DataFrame({
        "schools": g.size(),
        "no_fee_share": g["no_fee"].mean(),
        "learners": g["learners"].sum(),
        "matric_wrote": g["matric_wrote"].sum(min_count=1),
        "matric_passed": g["matric_passed"].sum(min_count=1),
    })
    out["matric_pass_rate"] = out["matric_passed"] / out["matric_wrote"]
    return out


def wards(ward_df: pd.DataFrame, raw: dict[str, pd.DataFrame], schools: pd.DataFrame) -> pd.DataFrame:
    w = ward_df.copy()
    w["ward_id"] = w["ward_id"].astype(str)
    k = raw["ward_councillors_2021"].assign(ward_id=lambda x: x["ward_id"].astype(str)).set_index("ward_id")
    # A city's own list (pilot: Tshwane) is newer than the 2021 results, since it
    # includes by-elections, so it wins where it exists.
    for col, src in (("councillor", "councillor"), ("party", "party")):
        national = w["ward_id"].map(k[src])
        w[col] = w[col].fillna(national) if col in w else national
    if "phone" not in w:
        w["phone"] = None
    w["turnout_2021"] = w["ward_id"].map(k["turnout_share"])
    w["won_with"] = w["ward_id"].map(k["winning_share"])
    r = raw["ward_results_2024"].assign(ward_id=lambda x: x["ward_id"].astype(str)).set_index("ward_id")
    w["turnout_2024"] = w["ward_id"].map(r["turnout_share"])
    w["votes_2024"] = [
        [{"party": r.at[i, f"party_{n}"], "share": r.at[i, f"share_{n}"]} for n in (1, 2, 3)
         if i in r.index and pd.notna(r.at[i, f"party_{n}"])]
        for i in w["ward_id"]
    ]
    s = schools.dropna(subset=["ward_id"]).groupby("ward_id")
    w["schools"] = w["ward_id"].map(s.size())
    w["matric_pass_rate"] = w["ward_id"].map(s["matric_passed"].sum(min_count=1) / s["matric_wrote"].sum(min_count=1))
    return w
