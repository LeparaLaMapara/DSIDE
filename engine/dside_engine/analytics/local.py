"""Safety per municipality and police station, jobs now, and ward-level facts.

Crime is compared quarter to the same quarter a year before, never to the
quarter before, because crime is seasonal (December is not April).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

CRIME_LABELS = {
    "murders": "Murders", "sexual_offences": "Sexual offences", "rapes": "Rapes",
    "drug_crimes": "Drug crimes", "house_burglaries": "House break-ins",
    "house_robberies": "House robberies", "contact_crimes": "Violent crimes against people",
}


def safety(crime: pd.DataFrame, population: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    latest = int(crime["year"].max())
    period = crime.loc[crime["year"] == latest, "period"].iloc[0]
    by_year = crime.pivot_table(index=["muni_code", "crime"], columns="year", values="count", aggfunc="sum")

    muni = pd.DataFrame(index=population.index)
    for c in CRIME_LABELS:
        now = by_year.xs(c, level="crime")[latest] if c in by_year.index.get_level_values("crime") else None
        before = by_year.xs(c, level="crime").get(latest - 1)
        if now is None:
            continue
        muni[c] = now.reindex(muni.index)
        muni[f"{c}_last_year"] = before.reindex(muni.index) if before is not None else np.nan
        muni[f"{c}_rate"] = (muni[c] / population * 100_000).round(1)
    muni = muni.dropna(how="all")
    muni["murder_rate"] = muni["murders_rate"]
    muni["sexual_offence_rate"] = muni["sexual_offences_rate"]

    st = crime.pivot_table(index=["station", "muni_code", "precinct_code", "precinct_population"],
                           columns=["crime", "year"], values="count", aggfunc="sum")
    stations = pd.DataFrame(index=st.index)
    for c in CRIME_LABELS:
        if (c, latest) in st.columns:
            stations[c] = st[(c, latest)]
            stations[f"{c}_last_year"] = st.get((c, latest - 1))
            stations[f"{c}_trend"] = [list(map(float, st.loc[i, c].reindex(sorted(st[c].columns)).fillna(0)))
                                      for i in st.index]
    stations = stations.reset_index()
    stations["murder_rate"] = (stations["murders"] / stations["precinct_population"] * 100_000).round(1)
    info = {"period": period, "year": latest, "labels": CRIME_LABELS,
            "years": sorted(int(y) for y in crime["year"].unique())}
    return muni, stations, info


def jobs(qlfs: pd.DataFrame, meta: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Latest official unemployment for the closest area Stats SA publishes.

    Metros have their own figure; local municipalities get their province's.
    """
    q = qlfs[qlfs["measure"] == "unemployment"]
    periods = list(dict.fromkeys(q["period"]))
    latest, recent = periods[-1], periods[-8:]
    series = q[q["period"].isin(recent)].pivot_table(index="area", columns="period", values="value")[recent]

    out = pd.DataFrame(index=meta.index)
    area = np.where(meta["kind"] == "metro", meta.index, meta["province"])
    out["jobs_area"] = area
    out["jobs_area_level"] = np.where(meta["kind"] == "metro", "this city", "this province")
    out["unemployment_now"] = pd.Series(area, index=meta.index).map(series[latest])
    out["unemployment_trend"] = pd.Series(area, index=meta.index).map(
        {a: [round(float(v), 1) for v in series.loc[a]] for a in series.index})

    lf = qlfs[qlfs["measure"] == "labour_force"].pivot_table(index="area", columns="period", values="value")
    un = qlfs[qlfs["measure"] == "unemployed"].pivot_table(index="area", columns="period", values="value")
    youth = (un.loc[["ZA:15-24", "ZA:25-34"], latest].sum() / lf.loc[["ZA:15-24", "ZA:25-34"], latest].sum())
    info = {"period": latest, "periods": recent, "national_unemployment": float(series.loc["ZA", latest]),
            "youth_unemployment_15_34": round(float(youth) * 100, 1),
            "source": str(qlfs["source"].iloc[0]) if "source" in qlfs else None}
    return out, info


def ward_table(wards: pd.DataFrame, councillors: pd.DataFrame) -> pd.DataFrame:
    w = wards
    num = lambda c: pd.to_numeric(w[c], errors="coerce").fillna(0)
    water_known = sum(num(c) for c in ["Tap_In_Dwelling", "tap_in_Yard", "Tap_CommStand_Less_200m",
                                        "Tap_CommStand_bet_200m_500m", "Tap_CommStand_bet_500m_1000m",
                                        "Tap_CommStand_More_1000m", "No_access_to_piped_water"])
    toilet_known = sum(num(c) for c in ["None_Toilet", "Flush_Toilet_SewerSystem", "Flush_Toilet_SepticTank",
                                         "Chemical_Toilet", "Pit_Toilet_VIP", "Pit_Toilet_NoVentilation",
                                         "Bucket_Toilet", "Other_Toilet"])
    refuse_known = sum(num(c) for c in ["Removed_Weekly", "Removed_Seldom", "Communal_dump", "Own_dump",
                                         "No_Disposal", "Other_Refuse"])
    labour = num("Employed") + num("Unemployed")
    edu_known = sum(num(c) for c in ["Completed_Primary", "No_schooling", "Some_Primary", "Some_Secondary",
                                      "Grade_12_Std10", "Higher", "Other_Edu"])
    out = pd.DataFrame({
        "ward_id": w["WardID"].astype(str), "ward_no": pd.to_numeric(w["WardNo"], errors="coerce"),
        "code": w["CAT_B"], "population": num("Total_Pop"), "voters": num("Reg_Voters"),
        "area_km2": num("Area_SqKm"),
        "water": (num("Tap_In_Dwelling") + num("tap_in_Yard") + num("Tap_CommStand_Less_200m")) / water_known,
        "toilet": (num("Flush_Toilet_SewerSystem") + num("Flush_Toilet_SepticTank") + num("Pit_Toilet_VIP")) / toilet_known,
        "refuse": num("Removed_Weekly") / refuse_known,
        "unemployment": num("Unemployed") / labour,
        "matric_or_more": (num("Grade_12_Std10") + num("Higher")) / edu_known,
        "geometry": w["geometry"],
    }).replace([np.inf, -np.inf], np.nan)
    for c in ["water", "toilet", "refuse", "unemployment", "matric_or_more"]:
        out[c] = out[c].round(3)
    if not councillors.empty:
        k = councillors.rename(columns={"muni_code": "code"})
        out = out.merge(k[["code", "ward_no", "councillor", "party", "phone"]], on=["code", "ward_no"], how="left")
    return out
