"""Compare each municipality with places like it, and say why in plain words.

Peers are Treasury's MIIF categories: metros (A), secondary cities (B1),
large towns (B2), small towns (B3) and mostly rural areas (B4). Comparing
a rural municipality with Cape Town tells a resident nothing they can act on;
comparing it with similar places shows what is possible with similar means.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PEER_NAMES = {"A": "big cities (metros)", "B1": "secondary cities", "B2": "large towns",
              "B3": "small towns", "B4": "mostly rural areas"}

# indicator -> (plain name, higher is better)
MEASURES: dict[str, tuple[str, bool]] = {
    "water": ("Tap water at home", True),
    "toilet": ("Proper toilets", True),
    "lighting": ("Electricity", True),
    "refuse": ("Rubbish collected weekly", True),
    "dwelling": ("Proper houses", True),
    "matric_adults": ("Adults with matric", True),
    "early_learning": ("Small children in early learning", True),
    "youth_neet": ("Young people with no job, school or training (2011)", False),
    "build_spent_share": ("Building budget actually spent", True),
    "wasted_share": ("Money spent wrongly or wastefully", False),
    "unpaid_share": ("Bills never paid", False),
    "murder_rate": ("Murders per 100 000 people, in 3 months", False),
    "sexual_offence_rate": ("Sexual offences per 100 000 people, in 3 months", False),
}


def peer_standing(df: pd.DataFrame) -> pd.DataFrame:
    """Percentile of each measure within the peer group (100 = best among peers)."""
    out = pd.DataFrame(index=df.index)
    for m, (_, higher_better) in MEASURES.items():
        if m not in df:
            continue
        pct = df.groupby("peer_group")[m].rank(pct=True, ascending=higher_better)
        out[f"peer_pct:{m}"] = (pct * 100).round(0)
        out[f"peer_median:{m}"] = df.groupby("peer_group")[m].transform("median")
        best = df.loc[df[m].notna()].sort_values(m, ascending=not higher_better).groupby("peer_group").head(1)
        out[f"peer_best:{m}"] = df["peer_group"].map(best.set_index("peer_group")["name"])
    return out


def strengths_and_problems(row: pd.Series, top: int = 3) -> tuple[list[dict], list[dict]]:
    items = []
    for m, (label, higher_better) in MEASURES.items():
        pct = row.get(f"peer_pct:{m}")
        if pct is None or pd.isna(pct) or pd.isna(row.get(m)):
            continue
        items.append({"measure": m, "label": label, "value": float(row[m]),
                      "peer_median": float(row[f"peer_median:{m}"]), "peer_pct": float(pct),
                      "higher_is_better": higher_better, "best_peer": row.get(f"peer_best:{m}")})
    items.sort(key=lambda i: i["peer_pct"])
    problems = [i for i in items if i["peer_pct"] <= 35][:top]
    strengths = [i for i in reversed(items) if i["peer_pct"] >= 65][:top]
    return strengths, problems


def rand(v: float) -> str:
    return f"R{v / 1e9:.1f} billion" if abs(v) >= 1e9 else f"R{v / 1e6:,.0f} million"


def fin_year(y: int) -> str:
    return f"{y - 1}-{str(y)[2:]}"


def reasons(row: pd.Series) -> list[dict]:
    """Evidence-backed reasons that go together with the problems.

    These are things the data shows side by side, not proven causes; the site
    says "goes with", never "caused by".
    """
    out: list[dict] = []

    def add(kind: str, text: str, evidence: str):
        out.append({"kind": kind, "text": text, "evidence": evidence})

    share = row.get("build_spent_share")
    if pd.notna(share) and share < 0.7 and pd.notna(row.get("build_planned")):
        add("money", f"It spent only {share:.0%} of the money it planned for building and fixing pipes, roads and power lines.",
            f"{rand(row['build_actual'])} spent of {rand(row['build_planned'])} planned in {fin_year(int(row['year']))}")
    wasted = row.get("wasted")
    if pd.notna(wasted) and pd.notna(row.get("wasted_share")) and row["wasted_share"] >= 0.05:
        add("money", f"{rand(wasted)} was spent against the rules or wasted in one year.",
            "Unauthorised, irregular, fruitless and wasteful spending, Treasury")
    unpaid = row.get("unpaid_share")
    if pd.notna(unpaid) and unpaid >= 0.15:
        add("money", f"About {unpaid:.0%} of what it bills for rates and services is never paid, so less money reaches services.",
            "Debt impairment compared with rates and service charges")
    audit = row.get("audit_code")
    if audit in {"qualified", "adverse", "disclaimer", "outstanding"}:
        add("honesty", "The Auditor-General could not confirm that its books are right.", f"Audit for {fin_year(int(row['year']))}")
    growth = row.get("population_growth")
    if pd.notna(growth) and growth >= 0.25:
        add("pressure", f"The number of people living here grew by {growth:.0%} between 2011 and 2022, so services must stretch further.",
            "Census 2011 and 2022")
    informal = row.get("informal_homes")
    if pd.notna(informal) and informal >= 0.15:
        add("pressure", f"About {informal:.0%} of people live in shacks, which are harder and costlier to connect to services.",
            "Census 2022")
    return out


def groups(df: pd.DataFrame, features: list[str], seed: int = 3) -> tuple[pd.Series, dict]:
    """Place each municipality on a 2x2 grid: services (x) against money handling (y).

    We tried k-means first. The best k-means split scores a silhouette of only
    about 0.27, meaning municipalities do not fall into natural clusters, and a
    cluster label then contradicts some members' own numbers. A transparent
    grid around the national middle is honest and easy to read, so the
    clustering result is kept only as evidence in the method notes.
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    from sklearn.preprocessing import StandardScaler

    x = df[features].dropna()
    z = StandardScaler().fit_transform(x)
    tried = {k: round(float(silhouette_score(z, KMeans(n_clusters=k, n_init=20, random_state=seed).fit(z).labels_)), 3)
             for k in range(2, 7)}

    services_mid, money_mid = df["dim:home"].median(), df["money_score"].median()
    good_services = df["dim:home"] >= services_mid
    well_run = df["money_score"] >= money_mid
    label = np.select(
        [good_services & well_run, good_services & ~well_run, ~good_services & well_run, ~good_services & ~well_run],
        ["Good services, money well handled", "Good services, money badly handled",
         "Poor services, money well handled", "Poor services, money badly handled"], default=None)
    label = pd.Series(label, index=df.index).where(df["dim:home"].notna() & df["money_score"].notna())
    return label, {"method": "2x2 grid around the national median", "services_median": float(services_mid),
                   "money_median": float(money_mid), "sizes": label.value_counts().to_dict(),
                   "kmeans_silhouette_by_k": tried}


def rate_per_100k(count: pd.Series, population: pd.Series) -> pd.Series:
    return (count / population.replace(0, np.nan) * 100_000).round(1)
