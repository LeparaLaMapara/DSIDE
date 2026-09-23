"""The few plain sentences at the top of every municipality page.

Written by fixed rules from the numbers, never by a language model, so a
sentence can only say what the data says. Each line carries a topic (for its
icon), a tone (good, bad or mixed) and the source it rests on. Lines whose
numbers are missing are simply left out.
"""

from __future__ import annotations

import math

import pandas as pd

SERVICE_WORDS = {
    "water": "tap water nearby",
    "lighting": "electricity",
    "toilet": "a proper toilet",
    "refuse": "weekly rubbish collection",
}


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def rand(v: float) -> str:
    if abs(v) >= 1e9:
        return f"R{v / 1e9:.1f} billion"
    return f"R{v / 1e6:,.0f} million"


def in_ten(share: float) -> str:
    n = round(share * 10)
    return "almost everyone" if n >= 10 else "almost no one" if n <= 0 else f"{n} in 10 people"


def fin_year(y: int) -> str:
    return f"{y - 1}-{str(y)[2:]}"


def headline(row: pd.Series) -> str | None:
    group = row.get("group")
    return {
        "Good services, money well handled": "Services mostly work, and the money is handled well.",
        "Good services, money badly handled": "Services mostly work, but the money is badly handled.",
        "Poor services, money well handled": "The money is handled well, but many people still lack basic services.",
        "Poor services, money badly handled": "Many people lack basic services, and the money is badly handled.",
    }.get(group) if isinstance(group, str) else None


# How much each kind of line matters to a resident; the story keeps the top few.
WEIGHT = {"services_bad": 10, "water_bad": 9, "money_now": 8, "money_old": 7, "waste": 7, "safety_bad": 7,
          "work": 6, "siu": 6, "services_good": 5, "safety_good": 5, "debt": 4}
MAX_LINES = 5


def story(row: pd.Series) -> list[dict]:
    lines: list[dict] = []

    def add(topic: str, tone: str, text: str, source: str, kind: str = "") -> None:
        lines.append({"topic": topic, "tone": tone, "text": text, "source": source, "kind": kind})

    # Services: say what works, then the biggest gap.
    have = {k: row.get(k) for k in SERVICE_WORDS if _ok(row.get(k))}
    if have:
        good = [SERVICE_WORDS[k] for k, v in have.items() if v >= 0.9]
        gaps = sorted((v, k) for k, v in have.items() if v < 0.85)[:2]
        if good:
            add("services", "good", f"Most people here have {' and '.join(good[:2])}.", "Census 2022", "services_good")
        if gaps:
            parts = [f"{in_ten(v)} have {SERVICE_WORDS[k]}" for v, k in gaps]
            add("services", "bad", "Only " + " and only ".join(parts) + ".", "Census 2022", "services_bad")

    # Money: planned against spent, then waste.
    share, planned = row.get("build_spent_share"), row.get("build_planned")
    year = row.get("year")
    if _ok(share) and _ok(planned) and _ok(year):
        if share < 0.7:
            add("money", "bad", f"It spent only {share:.0%} of the {rand(planned)} it planned for fixing pipes, roads "
                f"and power lines in {fin_year(int(year))}.", "National Treasury", "money_old")
        elif share > 1.1:
            add("money", "mixed", f"It spent {share:.0%} of what it planned for fixing pipes, roads and power lines "
                f"in {fin_year(int(year))}: more than the budget.", "National Treasury", "money_old")
        elif share >= 0.9:
            add("money", "good", f"It spent {min(share, 1):.0%} of the money it planned for fixing pipes, roads and "
                f"power lines in {fin_year(int(year))}.", "National Treasury", "money_old")
    wasted, wasted_share = row.get("wasted"), row.get("wasted_share")
    if _ok(wasted) and _ok(wasted_share) and wasted_share >= 0.05:
        add("money", "bad", f"{rand(wasted)} was spent against the rules or wasted in one year.", "National Treasury", "waste")

    owed = row.get("owed_households")
    if _ok(owed) and owed >= 50e6:
        add("money", "mixed", f"Households owe the municipality {rand(owed)} in unpaid bills, money that cannot "
            "go to services.", "National Treasury", "debt")

    green = row.get("green_drop_score")
    if _ok(green) and green < 50:
        add("water", "bad", f"Its sewage works scored {green:.0f}% in the latest national inspection "
            "(Green Drop). Under 50% is a serious risk.", "Department of Water and Sanitation", "water_bad")

    # Safety: same months this year and last year.
    now, before = row.get("murders"), row.get("murders_last_year")
    if _ok(now) and _ok(before) and before > 0:
        if now < before:
            add("safety", "good", f"Murders are down: {int(now)} in the latest three months, from {int(before)} a year before.", "SAPS", "safety_good")
        elif now > before:
            add("safety", "bad", f"Murders are up: {int(now)} in the latest three months, from {int(before)} a year before.", "SAPS", "safety_bad")

    # This year so far: building money spent against time gone.
    ytd, gone = row.get("ytd_capital_ytd_share"), row.get("ytd_expected_share")
    if _ok(ytd) and _ok(gone) and gone > 0 and ytd < gone - 0.15:
        add("money", "bad", f"This year it has spent {ytd:.0%} of its building budget, with {gone:.0%} of the year "
            f"gone (to {row.get('ytd_latest_month')}).", "National Treasury", "money_now")

    if _ok(row.get("siu_recent")) and row["siu_recent"] > 0:
        add("money", "bad", "In the last three years the President ordered the Special Investigating Unit to "
            "investigate this municipality.", "SIU", "siu")

    # Work: newest figure available (tax data), else the survey.
    jobs, jobs_before = row.get("formal_jobs"), row.get("formal_jobs_before")
    if _ok(jobs) and _ok(jobs_before) and jobs_before > 0:
        change = jobs / jobs_before - 1
        word = "more" if change > 0 else "fewer"
        if abs(change) >= 0.01:
            add("work", "good" if change > 0 else "bad",
                f"There are {abs(change):.0%} {word} formal jobs here than a year before ({int(jobs):,} now).",
                "SARS and National Treasury tax data", "work")
        else:
            add("work", "mixed", f"Formal jobs are flat at about {int(jobs):,}.", "SARS and National Treasury tax data", "work")
    elif _ok(row.get("unemployment_now")):
        add("work", "bad" if row["unemployment_now"] > 30 else "mixed",
            f"About {round(row['unemployment_now'] / 10)} in 10 people who want work here have none.", "Stats SA", "work")
    return pick(lines)


def pick(lines: list[dict]) -> list[dict]:
    """Keep the most important lines, newest money over older, and at least one good one."""
    kinds = {l["kind"] for l in lines}
    if "money_now" in kinds:
        lines = [l for l in lines if l["kind"] != "money_old"]
    ranked = sorted(lines, key=lambda l: -WEIGHT.get(l["kind"], 1))
    keep = ranked[:MAX_LINES]
    goods = [l for l in ranked if l["tone"] == "good"]
    if goods and not any(l["tone"] == "good" for l in keep):
        keep = keep[:-1] + [goods[0]]
    order = {id(l): i for i, l in enumerate(lines)}
    return [{k: v for k, v in l.items() if k != "kind"} for l in sorted(keep, key=lambda l: order[id(l)])]
