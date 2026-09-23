"""How people live: a wellbeing index with its parts always visible.

Dimensions follow Stats SA's multidimensional poverty index (SAMPI) and the
Youth MPI used by Youth Explorer, limited to what is published per
municipality:

  Home and services (Census 2022): water, toilet, electricity, rubbish, a
      proper house, clean cooking fuel.
  Learning (Census 2022): adults with matric or more, small children in
      early learning.
  Work (SARS tax data, latest tax year): formal jobs per working-age adult
      and the median formal monthly income.
  Safety (SAPS, when available): added by the safety module.

These are shares of people, not a household poverty count, because only
aggregates are published per municipality. The score is the equal-weight mean
of the dimensions; `robustness` then re-weights them thousands of times to
show whether a municipality's rank depends on our choice of weights.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

UNKNOWN = {"Unspecified", "Do not know", "Other", "Not applicable"}

SERVICE_RULES: dict[str, tuple[str, str, set[str]]] = {
    # indicator -> (column, plain label, categories that count as "has it")
    "water": ("access_to_piped_water", "Tap water at home or within 200 m", {
        "Piped (tap) water inside the dwelling", "Piped (tap) water inside the yard",
        "Piped (tap) water on community stand: distance less than 200m from dwelling"}),
    "toilet": ("toilet_facilities", "A proper toilet", {
        "Flush toilet connected to a public sewerage system", "Flush toilet connected to a septic tank or conservancy tank",
        "Pit latrine/toilet with ventilation pipe (VIP)", "Ecological toilet (e.g. urine diversion, enviroloo, etc)"}),
    "lighting": ("energy_or_fuel_for_lighting", "Electricity for lights", {"Electricity from mains"}),
    "refuse": ("refuse_or_rubbish", "Rubbish collected every week", {
        "Removed by local authority/private company/community members at least once a week"}),
    "dwelling": ("type_of_main_dwelling", "Lives in a proper house or flat", {
        "Formal dwelling/house or brick/concrete block structure on a separate stand or yard or on farm",
        "Flat or apartment in a block of flats/flat or apartment in a  block of flats in a complex",
        "Cluster house in complex", "Town house (semi-detached house in complex)", "Semi-detached house",
        "Formal dwelling/house/flat/room in backyard/servants’ quarters/granny flat/cottage"}),
    "cooking": ("energy_or_fuel_for_cooking", "Cooks with electricity or gas", {
        "Electricity from mains", "Gas", "Solar", "Other source of electricity (e.g. generator etc.)"}),
}

MATRIC_OR_MORE = {
    "Grade 12/ Standard 10/ Form 5/ Matric/ NCV Level 4/ Occupational Certificate NQF Level 4",
    "NTC III/N3", "N4/NTC 4/ Occupational Certificate NQF Level 5", "N5/NTC 5/ Occupational Certificate NQF Level 5",
    "N6/NTC 6/ Occupational Certificate NQF Level 5",
    "Higher/ National/ Advanced Certificate with Grade 12/ Std10/ Occupational Certificate NQF Level 5",
    "Diploma with Grade 12/ Standard 10/ Occupational Certificate NQF Level 6",
    "Higher Diploma/ Occupational Certificate NQF Level 7", "Bachelors Degree/ Occupational Certificate NQF Level 8",
    "Honours Degree/ Postgraduate Diploma/ Occupational Certificate NQF Level 8",
    "Masters/ Professional Masters at NQF Level 9",
    "PHD (Doctoral Degrees)/ Professional Doctoral Degree at NQF Level 10",
}
ADULT_BANDS = {"20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80-89", "90-99", "100+"}
YOUTH_AGE = "15-35 (ZA)"

DIMENSIONS = {
    "home": ["water", "toilet", "lighting", "refuse", "dwelling", "cooking"],
    "learning": ["matric_adults", "early_learning"],
    "work": ["formal_job_rate", "median_income"],
}
DIMENSION_LABELS = {"home": "Home and services", "learning": "Learning", "work": "Work and income",
                    "safety": "Safety"}


def _share(df: pd.DataFrame, indicator: str, column: str, yes: set[str]) -> pd.Series:
    sub = df[(df["indicator"] == indicator) & ~df[column].isin(UNKNOWN)]
    total = sub.groupby("code")["count"].sum()
    good = sub[sub[column].isin(yes)].groupby("code")["count"].sum()
    return (good.reindex(total.index).fillna(0) / total.replace(0, np.nan))


def census_2022(c22: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({name: _share(c22, name, col, yes) for name, (col, _, yes) in SERVICE_RULES.items()})

    pop = c22[c22["indicator"] == "population"]
    by_year = pop.groupby(["code", "census"])["count"].sum().unstack()
    out["population_2022"] = by_year.get("2022")
    out["population_2011"] = by_year.get("2011")
    out["population_growth"] = out["population_2022"] / out["population_2011"] - 1
    adults = pop[(pop["census"] == "2022") & pop["age_group"].isin(ADULT_BANDS)].groupby("code")["count"].sum()
    bands = pop[pop["census"] == "2022"].pivot_table(index="code", columns="age_group", values="count", aggfunc="sum")
    # About ages 20 to 64: whole 10-year bands 20 to 59, plus half of 60 to 69.
    out["working_age_2022"] = bands[["20-29", "30-39", "40-49", "50-59"]].sum(axis=1) + bands["60-69"] / 2
    edu = c22[c22["indicator"] == "education"]
    matric = edu[edu["highest_level_of_education"].isin(MATRIC_OR_MORE)].groupby("code")["count"].sum()
    out["matric_adults"] = (matric / adults).clip(upper=1)

    ecd = c22[(c22["indicator"] == "ecd") & ~c22["attendance_at_an_ecd_institution"].isin(UNKNOWN)]
    ecd_total = ecd.groupby("code")["count"].sum()
    ecd_none = ecd[ecd["attendance_at_an_ecd_institution"] == "None"].groupby("code")["count"].sum()
    out["early_learning"] = 1 - ecd_none.reindex(ecd_total.index).fillna(0) / ecd_total

    hh = c22[c22["indicator"] == "households"].groupby("code")["count"].sum()
    out["households_2022"] = hh
    out["informal_homes"] = _share(c22, "dwelling", "type_of_main_dwelling", {
        "Informal dwelling/shack in back yard",
        "Informal dwelling/shack not in backyard, e.g. in an informal/squatter settlement or on farm"})
    return out


def youth_2011(y11: pd.DataFrame) -> pd.DataFrame:
    y = y11[y11["age_group"] == YOUTH_AGE]
    out = pd.DataFrame(index=sorted(y["code"].unique()))
    out["youth_neet"] = _share(y, "neet", "neet_status", {"NEET"})
    out["youth_not_neet"] = 1 - out["youth_neet"]
    lab = y[y["indicator"] == "unemployment"]
    total = lab.groupby("code")["count"].sum()
    unemployed = lab[lab["official_unemployment_rate"] == "Unemployed"].groupby("code")["count"].sum()
    out["youth_unemployment"] = unemployed.reindex(total.index) / total
    out["youth_employed"] = 1 - out["youth_unemployment"]
    out["youth_poverty"] = _share(y, "youth_poverty", "multidimensionally_poor_status", {"Poor"})
    return out


def index(parts: pd.DataFrame, dimensions: dict[str, list[str]]) -> pd.DataFrame:
    """Score each dimension 0 to 100 against the national spread, then average.

    Each indicator is scaled so 0 = the worst municipality and 100 = the best
    (5th and 95th percentile, so one outlier cannot stretch the scale). A
    dimension needs at least half its indicators.
    """
    scaled = pd.DataFrame(index=parts.index)
    for cols in dimensions.values():
        for c in cols:
            lo, hi = parts[c].quantile(0.05), parts[c].quantile(0.95)
            scaled[c] = ((parts[c] - lo) / (hi - lo)).clip(0, 1) * 100
    out = pd.DataFrame(index=parts.index)
    for dim, cols in dimensions.items():
        present = scaled[cols].notna().sum(axis=1)
        out[f"dim:{dim}"] = scaled[cols].mean(axis=1).where(present >= max(1, len(cols) / 2)).round(0)
    dims = [f"dim:{d}" for d in dimensions]
    out["wellbeing"] = out[dims].mean(axis=1).where(out[dims].notna().sum(axis=1) >= 2).round(0)
    return out


def robustness(scores: pd.DataFrame, draws: int = 5000, seed: int = 7) -> pd.DataFrame:
    """Rank range under random weights (Dirichlet), so readers see how solid a rank is."""
    dims = [c for c in scores if c.startswith("dim:")]
    x = scores[dims].dropna()
    rng = np.random.default_rng(seed)
    w = rng.dirichlet(np.ones(len(dims)), size=draws)
    ranks = pd.DataFrame(x.to_numpy() @ w.T, index=x.index).rank(ascending=False)
    return pd.DataFrame({
        "rank": scores.loc[x.index, "wellbeing"].rank(ascending=False, method="min"),
        "rank_best": ranks.quantile(0.05, axis=1).round(0),
        "rank_worst": ranks.quantile(0.95, axis=1).round(0),
        "ranked_out_of": len(x),
    })
