"""Checks on the parts of the analysis that turn numbers into verdicts.

They use small hand-made tables, so they run offline in a second.
"""

import numpy as np
import pandas as pd

from dside_engine.analytics import compare, local, money, wellbeing
from dside_engine.sources import safety_jobs_wards as s


def test_ramp_scores_against_norms():
    x = pd.Series([0.40, 0.675, 0.95, 1.2])
    assert money._ramp(x, 0.4, 0.95).round(6).tolist() == [0.0, 50.0, 100.0, 100.0]
    # reversed ramp: less wasted money is better
    assert money._ramp(pd.Series([0.0, 0.2]), 0.20, 0.0).tolist() == [100.0, 0.0]


def test_waste_water_is_not_counted_as_water():
    assert money.service_bucket("Waste Water Management") == "Toilets and sewage"
    assert money.service_bucket("Water Distribution") == "Water"
    assert money.service_bucket("Mayor and Council") == "Running the office"


def test_anchor_year_needs_budget_and_actuals():
    rows = []
    for code in "ABCDE":
        for y, types in [(2023, ["ADJB", "AUDA"]), (2024, ["ADJB", "AUDA"]), (2025, ["AUDA"])]:
            rows += [{"demarcation_code": code, "year": y, "amount_type_code": t} for t in types]
    df = pd.DataFrame(rows)
    assert money.anchor_year(df, df) == 2024  # 2025 has no budget yet


def test_impossible_treasury_numbers_are_flagged_and_dropped():
    out = pd.DataFrame({"build_spent_share": [0.5, 7.9], "warnings": [[], []]})
    money._flag(out, "build_spent_share", 0.0, 3.0, "looks wrong")
    assert out["build_spent_share"].isna().tolist() == [False, True]
    assert out["warnings"].tolist() == [[], ["looks wrong"]]


def test_index_scales_best_to_100_and_needs_two_dimensions():
    parts = pd.DataFrame({"a": np.linspace(0, 1, 21), "b": np.linspace(0, 1, 21)})
    scores = wellbeing.index(parts, {"x": ["a"], "y": ["b"]})
    assert scores["wellbeing"].iloc[-1] == 100 and scores["wellbeing"].iloc[0] == 0
    one = wellbeing.index(parts, {"x": ["a"]})
    assert one["wellbeing"].isna().all()


def test_robustness_gives_a_range_around_the_rank():
    scores = pd.DataFrame({"dim:x": [90, 10, 50], "dim:y": [10, 90, 50], "wellbeing": [50, 50, 50]},
                          index=["P", "Q", "R"])
    r = wellbeing.robustness(scores, draws=500)
    assert (r["rank_best"] <= r["rank_worst"]).all()
    assert r.loc["P", "rank_best"] == 1 and r.loc["P", "rank_worst"] == 3  # depends entirely on the weights


def test_reasons_say_goes_with_not_caused_by():
    row = pd.Series({"build_spent_share": 0.44, "build_actual": 868e6, "build_planned": 1981e6, "year": 2024,
                     "wasted": 5.35e9, "wasted_share": 0.12, "unpaid_share": 0.05, "audit_code": "qualified",
                     "population_growth": 0.38, "informal_homes": 0.10})
    texts = [r["text"] for r in compare.reasons(row)]
    assert any("44%" in t for t in texts)
    assert any("R5.3 billion" in t or "R5.4 billion" in t for t in texts)
    assert not any("caused" in t for t in texts)


def test_station_names_match_the_precinct_table():
    assert s._norm("Middelburg Mpumalang") == s._norm("Middelburg MP")
    assert s._norm("JHB Central") == s._norm("Johannesburg Central")
    assert s._norm("Soshanguve") == "soshanguve"


def test_crime_compares_the_same_months_a_year_apart():
    crime = pd.DataFrame([
        {"station": "A", "muni_code": "X", "precinct_code": "P1", "precinct_population": 1000, "crime": c, "year": y,
         "period": f"April {y} to June {y}", "count": n}
        for c in local.CRIME_LABELS for y, n in [(2025, 10), (2026, 6)]
    ])
    muni, stations, info = local.safety(crime, pd.Series({"X": 100_000}))
    assert muni.loc["X", "murders"] == 6 and muni.loc["X", "murders_last_year"] == 10
    assert muni.loc["X", "murder_rate"] == 6.0
    assert info["period"] == "April 2026 to June 2026"
    assert stations.loc[0, "murders_trend"] == [10.0, 6.0]
