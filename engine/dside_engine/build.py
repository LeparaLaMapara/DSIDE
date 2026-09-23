"""Assemble one plain-language record per municipality from the raw tables.

Kept separate from the Ubunye task files so it can be tested and reused; the
tasks in pipelines/ only move data in and out.
"""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from .analytics import audit_model, compare, fresh, local, money, projects, story, wellbeing

PROVINCES = {"EC": "Eastern Cape", "FS": "Free State", "GT": "Gauteng", "KZN": "KwaZulu-Natal",
             "LIM": "Limpopo", "MP": "Mpumalanga", "NC": "Northern Cape", "NW": "North West",
             "WC": "Western Cape"}


def municipalities_meta(treasury: pd.DataFrame, geos: pd.DataFrame) -> pd.DataFrame:
    t = treasury.rename(columns=lambda c: c.replace("municipality_", "")).drop_duplicates("demarcation_code")
    t = t.set_index("demarcation_code")
    g = geos.set_index("code")
    out = pd.DataFrame(index=g.index)
    out["name"] = g["name"]
    out["parent"] = g["parent"]
    out["kind"] = np.where(g.index.str.startswith("DC"), "district",
                           np.where(g["level"] == "local", "local", "metro"))
    out["province"] = [p if k != "local" else None for p, k in zip(g["parent"], out["kind"])]
    local = out["kind"] == "local"
    out.loc[local, "province"] = out.loc[local, "parent"].map(g["parent"])
    out["province_name"] = out["province"].map(PROVINCES)
    out["peer_group"] = t["miif_category"].reindex(out.index)
    out["phone"] = t["phone_number"].reindex(out.index)
    out["website"] = t["url"].reindex(out.index).str.lower()
    out["label_lng"], out["label_lat"] = g["label_lng"], g["label_lat"]
    return out


def analyse(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    meta = municipalities_meta(raw["municipalities"], raw["geographies"])

    m, year = money.money_table(raw["income_items"], raw["capital"], raw["uifw"], raw["audits"])
    m = m.set_index("code")
    services = money.planned_by_service(raw["income_services"], year)

    people = wellbeing.census_2022(raw["census_2022"]).join(wellbeing.youth_2011(raw["youth_2011"]), how="left")
    df = meta.join(m, how="left").join(people, how="left")

    extra, nested = fresh.municipal(meta, raw)
    df = df.join(extra, how="left")
    df["formal_job_rate"] = df["formal_jobs"] / df["working_age_2022"]
    schools = fresh.schools_table(raw["schools"], raw["matric"])
    df = df.join(fresh.schools_by_muni(schools).add_prefix("sch_"), how="left")

    safety, stations, safety_info = local.safety(raw["crime"], df["population_2022"])
    df = df.join(safety, how="left")
    jobs, jobs_info = local.jobs(raw["jobs"], meta)
    df = df.join(jobs, how="left")
    df["safety_murder"] = -df["murder_rate"]
    df["safety_sexual"] = -df["sexual_offence_rate"]
    dims = {**wellbeing.DIMENSIONS, "safety": ["safety_murder", "safety_sexual"]}

    # Rank only the municipalities that deliver services (locals and metros).
    serving = df["kind"] != "district"
    scores = wellbeing.index(df[serving], dims)
    df = df.join(scores).join(wellbeing.robustness(scores))
    df = df.join(compare.peer_standing(df[serving]))

    grp, grp_info = compare.groups(df[serving], ["dim:home", "dim:learning", "money_score", "population_growth"])
    df["group"] = grp

    audits = raw["audits"]
    pred, model_report = audit_model.evaluate_and_predict(
        audit_model.panel(audits, meta.reset_index(names="code")))
    df = df.join(pred.set_index("code"), how="left")

    located = projects.locate(raw["projects"], raw["geographies"])
    located.loc[(located["estimated_total_project_cost"] > 3e9) & (located["sector"] != "Transport"),
                "estimated_total_project_cost"] = np.nan  # a clinic does not cost R20bn; source typo
    df = df.join(projects.summary(located), how="left")

    records = []
    for code, row in df.iterrows():
        strengths, problems = compare.strengths_and_problems(row) if row["kind"] != "district" else ([], [])
        rec = {k: _clean(v) for k, v in row.items()
               if not str(k).startswith(("peer_pct:", "peer_median:", "peer_best:", "safety_"))}
        rec.update(code=code, strengths=strengths, problems=problems, reasons=compare.reasons(row),
                   headline=story.headline(row), story=story.story(row) if row["kind"] != "district" else [],
                   officials=nested[code].get("officials", []), grants=nested[code].get("grants", []),
                   residents_say=nested[code].get("residents_say", []), siu=nested[code].get("siu", []),
                   planned_by_service=services[services["code"] == code][["service", "amount"]].to_dict("records"))
        records.append({k: _clean(v) for k, v in rec.items()})
    munis = pd.DataFrame(records)

    info = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "money_year": year,
        "groups": grp_info,
        "audit_model": model_report,
        "national": {**_national(df[serving], year),
                     "clean_audits": int((df["audit_code"] == "unqualified").sum()),
                     "audited": int(df["audit_code"].notna().sum())},
        "dimensions": {k: wellbeing.DIMENSION_LABELS[k] for k in dims},
        "safety": {**safety_info, "source": str(raw["crime"]["source"].iloc[0]),
                   "unmatched_stations": str(raw["crime"]["unmatched_stations"].iloc[0])},
        "jobs": jobs_info,
        "stale_sources": {k: v for k, v in _source_status().items() if not v.get("ok")},
    }
    slim_projects = located.dropna(subset=["code"])[
        ["code", "name", "sector", "department", "stage", "status", "estimated_total_project_cost",
         "estimated_completion_date", "latitude", "longitude", "url_path"]]
    wards = fresh.wards(local.ward_table(raw["wards"], raw["councillors"]), raw, schools)
    return {"municipalities": munis, "projects": slim_projects.reset_index(drop=True),
            "stations": stations, "wards": wards, "schools": schools,
            "meta": pd.DataFrame([{"json": json.dumps(info, default=_clean)}])}


def _source_status() -> dict:
    from .catalogue import STATUS

    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}


def _national(df: pd.DataFrame, year: int) -> dict:
    pop = df["population_2022"]
    w = lambda c: float((df[c] * pop).sum() / pop[df[c].notna()].sum())
    return {
        "municipalities": int(len(df)),
        "population_2022": int(pop.sum()),
        "wasted": float(df["wasted"].sum()),
        "build_planned": float(df["build_planned"].sum()),
        "build_actual": float(df.loc[df["build_planned"].notna(), "build_actual"].sum()),
        **{f"share:{c}": round(w(c), 4) for c in ["water", "toilet", "lighting", "refuse", "dwelling", "matric_adults"]},
    }


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else round(float(v), 4)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.ndarray):
        return [_clean(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if v is pd.NA or v is pd.NaT:
        return None
    return v
