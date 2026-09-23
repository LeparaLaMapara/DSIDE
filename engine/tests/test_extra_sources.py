"""Offline checks for the Treasury and Wazimap extras.

Small hand-made cells in the shape the APIs return (after dots in names
become underscores), so they run with no network.
"""

import pandas as pd
import pytest

from dside_engine.sources import treasury_extra as t
from dside_engine.sources import wazimap_extra as w


def test_period_label_maps_financial_months_to_calendar():
    assert t.period_label(2026, 1) == "July 2025"
    assert t.period_label(2026, 6) == "December 2025"
    assert t.period_label(2026, 9) == "March 2026"
    assert t.period_label(2026, 12) == "June 2026"
    assert t.financial_year(2026) == "2025/26"


def test_latest_month_skips_zero_months_and_takes_the_latest_year():
    cells = [
        {"demarcation.code": "AAA", "financial_year_end.year": 2025, "financial_period.period": 12, "total_amount.sum": 5},
        {"demarcation.code": "AAA", "financial_year_end.year": 2026, "financial_period.period": 8, "total_amount.sum": 7},
        {"demarcation.code": "AAA", "financial_year_end.year": 2026, "financial_period.period": 9, "total_amount.sum": 0},
        {"demarcation.code": "BBB", "financial_year_end.year": 2025, "financial_period.period": 11, "total_amount.sum": 3},
    ]
    out = t.latest_month(cells, "total_amount_sum").set_index("code")
    assert (out.loc["AAA", "year"], out.loc["AAA", "month"]) == (2026, 8)
    assert (out.loc["BBB", "year"], out.loc["BBB", "month"]) == (2025, 11)


def _debtor(item, group, total, g1=0.0, l30=0.0):
    return {"demarcation_code": "TSH", "item_code": item, "customer_group_code": group, "year": 2026, "month": 9,
            "total_amount_sum": total, "g1_amount_sum": g1, "l30_amount_sum": l30, "l1_amount_sum": 0.0}


def test_debtors_use_only_the_blank_customer_group():
    cells = pd.DataFrame([
        _debtor("2000", "", 32.4, g1=21.3, l30=3.1),
        _debtor("2000", "2401", 19.8, g1=14.0),  # detail row: must not be added again
        _debtor("2400", "", 20.6), _debtor("2300", "", 10.0), _debtor("2200", "", 1.8),
        _debtor("1200", "", 7.0), _debtor("1200", "2401", 5.1), _debtor("1300", "", 4.2),
        _debtor("1400", "", 5.7), _debtor("1900", "", 2.3),
    ])
    row = t.debtors_table(cells).iloc[0]
    assert row["owed_total"] == 32.4 and row["owed_over_1yr"] == 21.3
    assert row["owed_households"] == 20.6 and row["owed_business"] == 10.0 and row["owed_government"] == 1.8
    assert row["owed_water"] == 7.0 and row["owed_electricity"] == 4.2 and row["owed_rates"] == 5.7
    assert row["owed_other_services"] == 2.3
    assert row["period"] == "March 2026"
    assert row["share_over_1yr"] == pytest.approx(21.3 / 32.4)


def test_creditors_split_eskom_and_water_boards_and_age():
    base = {"demarcation_code": "TSH", "year": 2026, "month": 9, "l60_amount_sum": 0.0}
    cells = pd.DataFrame([
        {**base, "item_code": "1000", "total_amount_sum": 5105.0, "l30_amount_sum": 3000.0, "l90_amount_sum": 100.0},
        {**base, "item_code": "0100", "total_amount_sum": 4231.0, "l30_amount_sum": 2300.0, "l90_amount_sum": 0.0},
        {**base, "item_code": "0200", "total_amount_sum": 11.0, "l30_amount_sum": 11.0, "l90_amount_sum": 0.0},
        {**base, "item_code": "TP01", "total_amount_sum": 999.0, "l30_amount_sum": 0.0, "l90_amount_sum": 0.0},
    ])
    row = t.creditors_table(cells).iloc[0]
    assert row["owes_total"] == 5105.0 and row["owes_eskom"] == 4231.0 and row["owes_water_boards"] == 11.0
    assert row["owes_over_90d"] == 2005.0 and row["owes_eskom_over_90d"] == 1931.0


def test_grants_budget_falls_back_to_original_and_spending_sums_months():
    rows = [
        ("USDG", "year", "ADJB", 2026, 1176.8), ("USDG", "year", "ORGB", 2026, 1000.0),
        ("USDG", "month", "ACT", 3, 185.7), ("USDG", "month", "ACT", 6, -334.1), ("USDG", "month", "ACT", 8, 1114.6),
        ("MIG", "year", "ORGB", 2026, 100.0), ("MIG", "year", "TRFR", 2026, 60.0), ("MIG", "month", "ACT", 2, 20.0),
        ("OLD", "year", "ORGB", 2026, None),
    ]
    cells = pd.DataFrame([{"demarcation_code": "TSH", "grant_code": g, "period_length_length": pl, "amount_type_code": a,
                           "financial_period_period": p, "amount_sum": v} for g, pl, a, p, v in rows])
    out = t.grants_table(cells, {"USDG": "Urban Settlement Development Grant", "MIG": "Municipal Infrastructure Grant"}, 2026)
    out = out.set_index("grant_code")
    assert "OLD" not in out.index
    assert out.loc["USDG", "budget"] == 1176.8 and out.loc["USDG", "budget_type"] == "ADJB"
    assert out.loc["USDG", "spent"] == pytest.approx(966.2)
    assert out.loc["MIG", "budget"] == 100.0 and out.loc["MIG", "budget_type"] == "ORGB"
    assert out.loc["MIG", "transferred"] == 60.0 and out.loc["MIG", "spent_share"] == 0.2
    assert set(out["months_reported"]) == {8}


def test_year_to_date_sums_single_months_and_flags_repeats():
    inc = []
    for p, r, s in [(1, 100.0, 90.0), (2, 100.0, 90.0), (3, 120.0, 80.0)]:
        inc += [{"demarcation_code": "TSH", "measure": "revenue", "period_length_length": "month",
                 "amount_type_code": "ACT", "financial_period_period": p, "amount_sum": r},
                {"demarcation_code": "TSH", "measure": "spending", "period_length_length": "month",
                 "amount_type_code": "ACT", "financial_period_period": p, "amount_sum": s}]
    inc += [{"demarcation_code": "TSH", "measure": "revenue", "period_length_length": "year", "amount_type_code": "ADJB",
             "financial_period_period": 2026, "amount_sum": 1280.0},
            {"demarcation_code": "TSH", "measure": "spending", "period_length_length": "year", "amount_type_code": "ORGB",
             "financial_period_period": 2026, "amount_sum": 1040.0}]
    cap = [{"demarcation_code": "TSH", "capital_type_label": lbl, "period_length_length": pl, "amount_type_code": a,
            "financial_period_period": p, "amount_sum": v}
           for lbl, pl, a, p, v in [("New", "month", "ACT", 3, 30.0), ("Upgrading", "month", "ACT", 3, 10.0),
                                    ("Repairs and maintenance", "month", "ACT", 3, 999.0),
                                    ("New", "year", "ADJB", 2026, 160.0), ("Deprecation", "year", "ADJB", 2026, 999.0)]]
    row = t.year_to_date_table(pd.DataFrame(inc), pd.DataFrame(cap), 2026).iloc[0]
    assert row["months_reported"] == 3 and row["latest_month"] == "September 2025"
    assert row["repeated_months"] == 1
    assert row["revenue_ytd"] == 320.0 and row["revenue_ytd_share"] == 0.25 and row["revenue_budget_type"] == "ADJB"
    assert row["spending_ytd"] == 260.0 and row["spending_budget"] == 1040.0 and row["spending_budget_type"] == "ORGB"
    assert row["capital_ytd"] == 40.0 and row["capital_ytd_share"] == 0.25
    assert row["expected_share"] == 0.25


def test_officials_keep_leaders_and_only_work_contacts():
    facts = [
        {"municipality.demarcation_code": "EC157", "role.role": "Mayor/Executive Mayor", "contact_details.name": "A  Person",
         "contact_details.email_address": "someone@gmail.com", "contact_details.phone_number": "047 495 1272",
         "contact_details.title": "Mr"},
        {"municipality.demarcation_code": "EC157", "role.role": "Municipal Manager", "contact_details.name": "B Person",
         "contact_details.email_address": "mm@ksd.gov.za", "contact_details.phone_number": "082 123 4567",
         "contact_details.title": ""},
        {"municipality.demarcation_code": "EC157", "role.role": "Secretary of Speaker", "contact_details.name": "C",
         "contact_details.email_address": "c@ksd.gov.za", "contact_details.phone_number": "047 1", "contact_details.title": "Ms"},
    ]
    out = t.officials_table(facts).set_index("role_key")
    assert list(out.index) == ["mayor", "municipal_manager"]
    assert pd.isna(out.loc["mayor", "email"]) and out.loc["mayor", "office_phone"] == "047 495 1272"
    assert out.loc["mayor", "name"] == "A Person"
    assert out.loc["municipal_manager", "email"] == "mm@ksd.gov.za" and pd.isna(out.loc["municipal_manager", "office_phone"])


def test_cash_cover_excludes_non_cash_spending():
    s = lambda v: pd.Series({"AAA": v})
    row = t.cash_table(s(300.0), s(310.0), s(1500.0), s(200.0), s(100.0), 2025).iloc[0]
    assert row["monthly_cash_spending"] == 100.0 and row["months_cover"] == 3.0
    assert bool(row["statements_agree"]) and not bool(row["cash_negative"])
    neg = t.cash_table(s(-50.0), s(10.0), s(1200.0), s(0.0), s(0.0), 2025).iloc[0]
    assert bool(neg["cash_negative"]) and neg["months_cover"] == -0.5


def test_split_name_party_uses_the_last_dash():
    assert w.split_name_party("ENOS PAPIKI CHILOANE - AFRICAN NATIONAL CONGRESS") == (
        "Enos Papiki Chiloane", "African National Congress")
    assert w.split_name_party("JANE SMITH-DLAMINI - DEMOCRATIC ALLIANCE") == ("Jane Smith-Dlamini", "Democratic Alliance")
    assert w.split_name_party("") == (None, None)


def test_ward_councillors_combine_three_indicators():
    ward = "79900090"
    councillor = {"TSH": {ward: [{"contents": "ENOS PAPIKI CHILOANE - AFRICAN NATIONAL CONGRESS"}]}}
    votes = {"TSH": {ward: [{"count": "3502", "party": "ENOS PAPIKI CHILOANE - AFRICAN NATIONAL CONGRESS"},
                            {"count": "1000", "party": "X Y - DEMOCRATIC ALLIANCE"},
                            {"count": "498", "party": "Z - ACTIONSA"}]}}
    turn = {"TSH": {ward: [{"count": "5786", "voter turnout": "Party Votes"}, {"count": "61", "voter turnout": "Spoilt Votes"},
                           {"count": "10292", "voter turnout": "Registered But Did Not Vote"}]}}
    row = w.ward_councillors_table(councillor, votes, turn).iloc[0]
    assert row["ward_id"] == ward and row["code"] == "TSH"
    assert row["councillor"] == "Enos Papiki Chiloane" and row["party"] == "African National Congress"
    assert row["registered_voters"] == 16139 and row["turnout_share"] == pytest.approx(5847 / 16139)
    assert row["winning_share"] == pytest.approx(3502 / 5000) and row["margin_share"] == pytest.approx(2502 / 5000)
    assert row["winner_matches_votes"] and row["candidates"] == 3


def test_ward_results_2024_rank_top_parties():
    parties = {"TSH": {"79900090": [{"count": "10", "political party": "SMALL PARTY"},
                                    {"count": "601", "political party": "AFRICAN NATIONAL CONGRESS"},
                                    {"count": "200", "political party": "ECONOMIC FREEDOM FIGHTERS"},
                                    {"count": "189", "political party": "DEMOCRATIC ALLIANCE"}]}}
    turn = {"TSH": {"79900090": [{"count": "1000", "voter turnout": "Party Votes"},
                                 {"count": "1000", "voter turnout": "Registered But Did Not Vote"}]}}
    row = w.ward_results_table(turn, parties).iloc[0]
    assert row["party_1"] == "African National Congress" and row["share_1"] == pytest.approx(0.601)
    assert row["party_3"] == "Democratic Alliance" and row["turnout_share"] == 0.5 and row["valid_votes"] == 1000


def test_census_extras_leave_unknowns_out_of_the_base():
    rdp = {"AAA": [{"rdp/government subsidised dwelling": "Yes", "count": "20"},
                   {"rdp/government subsidised dwelling": "No", "count": "60"},
                   {"rdp/government subsidised dwelling": "Not applicable", "count": "20"}]}
    heads = {"AAA": [{"sex of the head of household": "Female", "count": "45"},
                     {"sex of the head of household": "Male", "count": "55"}]}
    see = {"AAA": [{"disability status": "No difficulty", "count": "90"}, {"disability status": "A lot of difficulty", "count": "3"},
                   {"disability status": "Cannot do at all", "count": "1"}, {"disability status": "Some difficulty", "count": "6"},
                   {"disability status": "Unspecified", "count": "50"}]}
    walk = {"AAA": [{"disability status": "No difficulty", "count": "98"}, {"disability status": "Cannot do at all", "count": "2"}]}
    row = w.census_extras_table(rdp, heads, see, walk).iloc[0]
    assert row["rdp_household_share"] == 0.25 and row["female_headed_share"] == 0.45
    assert row["disability_seeing_share"] == 0.04 and row["disability_walking_share"] == 0.02
    assert row["disability_floor_share"] == 0.04


def test_gcro_shares_per_survey_round():
    recs = [{"survey year": "2020/21", "satisfaction with local government": "Satisfied", "count": "30"},
            {"survey year": "2020/21", "satisfaction with local government": "Dissatisfied", "count": "70"},
            {"survey year": "2023/24", "satisfaction with local government": "Satisfied", "count": "20"},
            {"survey year": "2023/24", "satisfaction with local government": "Neither", "count": "80"}]
    unpaid = [{"survey year": "2023/24", "household have unpaid municipal accounts (arrears)": "Yes", "count": "25"},
              {"survey year": "2023/24", "household have unpaid municipal accounts (arrears)": "No", "count": "75"},
              {"survey year": "2023/24", "household have unpaid municipal accounts (arrears)": "Don't know", "count": "900"}]
    out = w.gcro_table({2296: {"TSH": recs}, 2359: {"TSH": unpaid}})
    sat = out[out["indicator"] == 2296].set_index("year")["share"]
    assert sat["2020/21"] == 0.3 and sat["2023/24"] == 0.2
    assert out[out["indicator"] == 2359]["share"].iloc[0] == 0.25
