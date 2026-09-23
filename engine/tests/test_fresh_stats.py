"""Offline checks for the fresh_stats parsers and the name to code matcher.

Each test feeds a small hand-copied piece of the real source (text lines
from the PDFs, rows from the spreadsheet, JSON from the API) so nothing
touches the network.
"""

import io

import pandas as pd

from dside_engine.sources import fresh_stats as fs

REG = pd.DataFrame([
    {"code": "TSH", "name": "Tshwane", "category": "A", "province": "GT", "district": "TSH"},
    {"code": "JHB", "name": "City of Joburg", "category": "A", "province": "GT", "district": "JHB"},
    {"code": "JHB", "name": "City of Johannesburg", "category": "A", "province": "GT", "district": "JHB"},
    {"code": "NMA", "name": "Nelson Mandela Bay", "category": "A", "province": "EC", "district": "NMA"},
    {"code": "BUF", "name": "Buffalo City", "category": "A", "province": "EC", "district": "BUF"},
    {"code": "EC157", "name": "King Sabata Dalindyebo", "category": "B", "province": "EC", "district": "DC15"},
    {"code": "DC15", "name": "O R Tambo", "category": "C", "province": "EC", "district": "DC15"},
    {"code": "MP304", "name": "Pixley Ka Seme (MP)", "category": "B", "province": "MP", "district": "DC30"},
    {"code": "DC7", "name": "Pixley Ka Seme (NC)", "category": "C", "province": "NC", "district": "DC7"},
    {"code": "FS194", "name": "Maluti-a-Phofung", "category": "B", "province": "FS", "district": "DC19"},
    {"code": "NC091", "name": "Sol Plaatje", "category": "B", "province": "NC", "district": "DC9"},
    {"code": "NC065", "name": "Hantam", "category": "B", "province": "NC", "district": "DC6"},
    {"code": "NC064", "name": "Kamiesberg", "category": "B", "province": "NC", "district": "DC6"},
    {"code": "NW405", "name": "JB Marks", "category": "B", "province": "NW", "district": "DC40"},
    {"code": "DC38", "name": "Ngaka Modiri Molema", "category": "C", "province": "NW", "district": "DC38"},
    {"code": "GT484", "name": "Merafong City", "category": "B", "province": "GT", "district": "DC48"},
    {"code": "GT485", "name": "Rand West City", "category": "B", "province": "GT", "district": "DC48"},
])
REG["key"] = REG["name"].map(fs._key)


def test_key_strips_council_words():
    assert fs._key("City of Tshwane Metropolitan Municipality") == "tshwane"
    assert fs._key("Maluti-a-Phofung Local Municipality") == "malutiaphofung"
    assert fs._key("Pixley Ka Seme (NC)") == "pixleykaseme"
    assert fs._key("Khâi-Ma LM") == "khaima"
    assert fs._key("Municipality") == ""


def test_match_code_uses_province_kind_alias_and_fuzzy():
    assert fs.match_code("City of Tshwane Metropolitan Municipality", REG, "GT") == "TSH"
    assert fs.match_code("CITY OF JOHANNESBURG METROPOLITAN MUNICIPALITY", REG, "GT") == "JHB"
    assert fs.match_code("Nelson Mandela MM", REG, "EC") == "NMA"            # alias
    assert fs.match_code("Buffalo City LM", REG, "EC") == "BUF"               # label says local, it is a metro
    assert fs.match_code("Pixley Ka Seme LM", REG, "MP") == "MP304"           # same name, other province
    assert fs.match_code("Pixley ka Seme District Municipality", REG, "NC") == "DC7"
    assert fs.match_code("Sol Plaatjie LM", REG, "NC") == "NC091"             # fuzzy
    assert fs.match_code("King Sabata Dalindyebo Local Municipality", REG, "EC") == "EC157"
    assert fs.match_code("Nowhere LM", REG, "GT") is None


def test_stp_values_keeps_councils_only():
    rows = [
        {"cat_b": "Missing Location Data", "display": 115846},
        {"cat_b": "TSH", "display": 975615},
        {"cat_b": "EC157", "display": 36130},
        {"cat_b": "TSH_X", "display": "n/a"},
    ]
    assert fs._stp_values(rows, {"TSH", "EC157"}) == {"TSH": 975615.0, "EC157": 36130.0}


def _p0302_workbook() -> bytes:
    ages = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54",
            "55-59", "60-64", "65-69", "70-74", "75-79", "80+"]
    rows = [["District Council projections for PC-axis", None, None, None, None], [None] * 5,
            ["Name ", "Sex", "Age", 2026.0, 2027.0]]
    for name in ["GT - West Rand DM (DC48)", "GT - City of Tshwane Metropolitan Municipality"]:
        for sex in ["Male", "Female"]:
            for a in ages:
                rows.append([name, sex, a, 10.0, 11.0])
    rows.append([None, None, None, 999.0, 999.0])  # national total row below the table
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, header=False, index=False)
    return buf.getvalue()


def test_parse_p0302_groups_ages():
    out = fs.parse_p0302(_p0302_workbook())
    tsh = out[(out["code"] == "TSH") & (out["period"] == 2026)].iloc[0]
    assert tsh["population"] == 17 * 2 * 10
    assert tsh["children_0_14"] == 3 * 2 * 10
    assert tsh["youth_15_34"] == 4 * 2 * 10
    assert tsh["elderly_65_plus"] == 4 * 2 * 10
    assert sorted(out["code"].unique()) == ["DC48", "TSH"]
    assert fs.p0302_code("KZN - eThekwini Metropolitan Municipality") == "ETH"
    assert fs.p0302_code("WC- Garden Route (DC4)") == "DC4"


SRD_TEXT = """PAYMENT BY DISTRICT MUNICIPLALITY
TABLE 11: NUMBER OF APPROVED, PAID AND UNPAID APPLICATIONS BY DISTRICT MUNICIPALITY END OF JUNE 2026
%
Region Municipality Paid Unpaid Approved % Paid Paid Unpaid Approved Paid Paid Unpaid Approved % Paid
EC 935,257 129,292 1,064,549 88% 926,533 123,592 1,050,125 88% 924,930 119,086 1,044,016 89%
1839 704 2543 72% 1758 660 2418 73% 1762 653 2415 73%
King Sabata Dalindyebo Local
Municipality 55756 10072 65828 85% 54956 9754 64710 85% 54370 9438 63808 85%
GP 1,276,052 154,831 1,430,883 89% 1,264,296 149,238 1,413,534 89% 1,260,068 143,254 1,403,322 90%
City of Tshwane Metropolitan
Municipality 282120 30127 312247 90% 280034 29051 309085 91% 278665 27800 306465 91%
Merafong City Local Municipality 19549 2114 21663 90% 18936 2056 20992 90% 18967 2018 20985 90%
Total 7083173 941985 8025158 88% 1 1 2 50% 1 1 2 50%
TABLE 12: SOMETHING ELSE
Nowhere Local Municipality 1 1 2 50%
"""


def test_srd_table_and_rows():
    lines = fs.srd_table_lines("contents\nAPPLICATIONS BY DISTRICT MUNICIPALITY END ... 17\n" + SRD_TEXT)
    t = fs.parse_srd_lines(lines)
    assert t["name"].tolist() == ["King Sabata Dalindyebo Local Municipality",
                                  "City of Tshwane Metropolitan Municipality", "Merafong City Local Municipality"]
    tsh = t.iloc[1]
    assert (tsh["province"], tsh["srd_paid"], tsh["srd_approved"], tsh["srd_pct_paid"]) == ("GT", 282120, 312247, 90)
    assert t["consistent"].all()
    assert t.iloc[0]["province"] == "EC"


def test_latest_srd_report_picks_newest_month():
    html = ('<a href="https://sassa.gov.za/documents/uploads/Report_covid_19_analysis_unemployment_trends_report_'
            'end_of_September_2025.pdf">x</a><a href="https://sassa.gov.za/documents/uploads/Report_covid_19_analysis_'
            'unemployment_trends_report_end_of_June_2026_V2.pdf">y</a>'
            '<a href="https://sassa.gov.za/documents/uploads/Social_assistance_report_June_2026.pdf">z</a>')
    url, period = fs.latest_srd_report(html)
    assert period == "2026-06" and "June_2026_V2" in url


GD_TEXT = """Table 1 - Gauteng 2024 Green Drop Audit Results Summary
 WSA Name
2013 GD
Score
(%)*
City of Ekurhuleni  84% 86% 82%↓
Merafong City LM 54% 21% 45%↑   Khutsong, Wedela,
City of Tshwane  82% 60% 34%↓
Rand West City LM   24% 16%↓   Badirile, Hannes van
Randfontein LM 67%
Ngaka Modiri Molema
DM 18% 0% 40%↑   Atamelang, Mafikeng, Mmabatho,
Thaba Chweu LM 79.8% 10% 58%↑
Dipaleseng LM 3% 4% 0.4%↓   Balfour, Greylingstad,
Table 2 - Next table
Other LM 50% 50% 50%↑
"""


def test_parse_gd_summary():
    block = fs._table_block(GD_TEXT, "Gauteng 2024 Green Drop Audit Results Summary")
    gd = fs.parse_gd_summary(block)
    assert gd["City of Tshwane"] == 34
    assert gd["Rand West City LM"] == 16
    assert gd["Ngaka Modiri Molema DM"] == 40
    assert gd["Thaba Chweu LM"] == 58 and gd["Dipaleseng LM"] == 0.4
    assert "Randfontein LM" not in gd  # old council, 2013 score only
    assert "Other LM" not in gd        # belongs to the next table


CRR_TEXT = """Table 7 - %CRR/CRRmax scores and WWTWs in critical and high-risk state (Current and Previous)
WSA Name 2024 Average CRR/CRRmax % deviation
WWTWs in critical and high-risk state
Critical Risk (90-100%CRR) High Risk (70-<90%CRR)
OR Tambo DM 52.10%   Mqanduli, Nqgeleni, Port St Johns, Qumbu, Tsolo
Sunday's River Valley
LM 88.70% Addo, Enon/ Bersheba, Paterson Kirkwood
Provincial Average 68% 21 of 125 (17%) 52 of 125 (42%)

WSA Name 2021 Average CRR/CRRmax % deviation
Buffalo City LM 53.2%   Kidds Beach, West Bank
"""


def test_parse_crr_current_block_only():
    crr = fs.parse_crr(fs._table_block(CRR_TEXT, "%CRR/CRRmax scores and WWTWs in critical"))
    assert crr == {"OR Tambo DM": 52.1, "Sunday's River Valley LM": 88.7}


BD_TEXT = """6.2 City of Johannesburg Metropolitan Municipality ........................... 36
 GAUTENG
6.3 CITY OF TSHWANE METROPOLITAN MUNICIPALITY

Institutional Scores
2024 BDRR 35.2%
2023 BDRR 33.8%
 KWAZULU NATAL
6.1. AMAJUBA DISTRICT MUNICIPALITY

Institutional Scores
2024BDRR 38.8%
"""


def test_parse_bdrr_and_category():
    assert fs.parse_bdrr(BD_TEXT) == {"CITY OF TSHWANE METROPOLITAN MUNICIPALITY": 35.2,
                                      "AMAJUBA DISTRICT MUNICIPALITY": 38.8}
    assert [fs.bdrr_category(x) for x in (35.2, 50, 89.9, 90, None)] == ["low", "medium", "high", "critical", None]


def test_parse_eskom():
    assert fs.parse_eskom("1") == 0
    assert fs.parse_eskom("3\n") == 2
    assert fs.parse_eskom("-1") is None
    assert fs.parse_eskom("<html>") is None
