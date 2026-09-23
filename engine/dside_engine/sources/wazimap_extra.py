"""More from Wazimap NG: ward election results, extra Census 2022 measures, GCRO quality of life.

Profile 23 = SANEF local government election dashboard (2021 LGE and 2024
NPE results by ward, plus Census 2022 person tables by municipality).
Profile 14 = Open Wazi, Census 2022 household tables.
Profile 10 = GCRO Quality of Life survey, Gauteng only.

Ward geographies in Wazimap are named by the Municipal Demarcation Board's
8-digit ward id, the same id our ward table uses (TSH ward 90 is
'79900090', whose parent in Wazimap is TSH). A child_data call on a metro or
local municipality returns one indicator for all of its wards, which is the
cheapest route: one call per municipality per indicator, against one call
per ward (4 468 wards) for all_details. Every call goes through the Fetcher
cache.

The indicator ids used here are profile indicator ids (the ids in the
`profile_data` of an all_details response), not the dataset indicator ids
shown in /profiles/{id}/.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from ..http import Fetcher
from .wazimap import API, CENSUS22_PROFILE, child_data, geography_tree, indicator_for_all, share

ELECTIONS_PROFILE = 23
GCRO_PROFILE = 10
SOURCE_23 = f"{API}/profile/{ELECTIONS_PROFILE} (SANEF local government election dashboard)"

# 2021 local government election, ward ballot
LGE21_COUNCILLOR = 1312      # "NAME - PARTY" of the councillor elected
LGE21_CANDIDATE_VOTES = 1341  # ward votes by candidate, key "party" holds "NAME - PARTY"
LGE21_TURNOUT = 2917          # party votes, spoilt votes, registered but did not vote
# 2024 national and provincial elections, national ballot
NPE24_TURNOUT = 3001
NPE24_PARTY_VOTES = 3000
# Census 2022
RDP_HOUSEHOLDS = 2812         # profile 14
HOUSEHOLD_HEAD_SEX = 2801     # profile 14
DISABILITY_SEEING = 2898      # profile 23
DISABILITY_WALKING = 2901     # profile 23

GCRO_QUESTIONS = [
    # (indicator, question, group column, answers counted, answers left out of the base)
    (2296, "Satisfied with local government", "satisfaction with local government", {"Satisfied"}, set()),
    (2299, "Satisfied with ward councillor", "satisfaction with ward councillor", {"Satisfied"}, set()),
    (2209, "Water cut at least once a month", "water interruptions (how often)",
     {"Every week", "A couple of times a month", "Once a month"}, set()),
    (2359, "Household has unpaid municipal account", "household have unpaid municipal accounts (arrears)",
     {"Yes"}, {"Don't know"}),
    (2496, "Satisfied with municipal billing", "billing satisfaction", {"Satisified", "Satisfied"},
     {"I don't have an account with the municipality"}),
    (2509, "Protest in the neighbourhood in the past year", "protest in the past year", {"Yes"}, {"Don't know"}),
    (2371, "Feels safe walking at night", "safety when walking at night", {"Safe"}, set()),
    (2308, "Quality of life index good or excellent", "quality of life index", {"Good", "Excellent"}, set()),
]

TURNOUT_VOTED = {"Party Votes", "Spoilt Votes"}
UNKNOWN = {"Do not know", "Unspecified", "Not applicable", "Don't know"}


# ---------------------------------------------------------------- helpers

def split_name_party(text: str) -> tuple[str | None, str | None]:
    """'ENOS PAPIKI CHILOANE - AFRICAN NATIONAL CONGRESS' -> ('Enos Papiki Chiloane', 'African National Congress')."""
    if not text or not str(text).strip():
        return None, None
    name, sep, party = str(text).rpartition(" - ")
    if not sep:
        return str(text).strip().title(), None
    return name.strip().title(), party.strip().title()


def turnout(rows: list[dict]) -> tuple[float | None, float | None]:
    """(registered voters, turnout share) from a Wazimap 'voter turnout' indicator."""
    counts = {r.get("voter turnout"): float(r.get("count") or 0) for r in rows}
    registered = sum(counts.values())
    if not registered:
        return None, None
    return registered, sum(v for k, v in counts.items() if k in TURNOUT_VOTED) / registered


def ranked(rows: list[dict], key: str) -> list[tuple[str, float]]:
    """(label, count) sorted by count, largest first."""
    out = [(r.get(key), float(r.get("count") or 0)) for r in rows if r.get(key)]
    return sorted(out, key=lambda x: -x[1])


def ward_serving_codes(f: Fetcher) -> list[str]:
    """Metros and local municipalities (the ones that have wards)."""
    geos, _ = geography_tree(f, CENSUS22_PROFILE)
    return sorted(g["code"] for g in geos if not g["code"].startswith("DC"))


def _for_municipalities(f: Fetcher, profile: int, indicator: int, codes: list[str],
                        workers: int = 4) -> dict[str, dict[str, list[dict]]]:
    """child_data for each municipality: {muni code: {ward id: rows}}."""
    def one(code: str):
        try:
            return code, child_data(f, profile, code, indicator)
        except (LookupError, RuntimeError):
            return code, {}

    with ThreadPoolExecutor(workers) as pool:
        return dict(pool.map(one, codes))


# ---------------------------------------------------------------- 2021 ward councillors

def ward_councillors_table(councillor: dict[str, dict], votes: dict[str, dict], turn: dict[str, dict]) -> pd.DataFrame:
    """Per-municipality child_data dicts for 1312, 1341 and 2917 to one row per ward."""
    rows = []
    for code, wards in councillor.items():
        for ward_id, data in wards.items():
            name, party = split_name_party(data[0].get("contents") if data else None)
            cand = ranked(votes.get(code, {}).get(ward_id, []), "party")
            valid = sum(c for _, c in cand)
            registered, share_voted = turnout(turn.get(code, {}).get(ward_id, []))
            win_name, win_party = split_name_party(cand[0][0]) if cand else (None, None)
            rows.append({
                "ward_id": str(ward_id), "code": code,
                "councillor": name or win_name, "party": party or win_party,
                "registered_voters": registered, "turnout_share": share_voted,
                "winning_votes": cand[0][1] if cand else None,
                "winning_share": cand[0][1] / valid if valid else None,
                "margin_share": (cand[0][1] - cand[1][1]) / valid if len(cand) > 1 and valid else None,
                "candidates": len(cand) or None,
                "winner_matches_votes": (win_name == name) if cand and name else None,
            })
    return pd.DataFrame(rows).sort_values("ward_id").reset_index(drop=True)


def ward_councillors_2021(f: Fetcher | None = None, codes: list[str] | None = None) -> pd.DataFrame:
    """Councillor elected in every ward at the 2021 local government election.

    Columns: ward_id (8-digit MDB ward id), code (municipality), councillor,
    party, registered_voters, turnout_share (ward ballot, spoilt votes
    included), winning_votes, winning_share (of valid ward votes),
    margin_share (winner minus runner up), candidates, winner_matches_votes,
    election, source. This is the 2021 result: by-elections and deaths since
    then are not reflected.
    """
    f = f or Fetcher()
    codes = codes or ward_serving_codes(f)
    out = ward_councillors_table(_for_municipalities(f, ELECTIONS_PROFILE, LGE21_COUNCILLOR, codes),
                                 _for_municipalities(f, ELECTIONS_PROFILE, LGE21_CANDIDATE_VOTES, codes),
                                 _for_municipalities(f, ELECTIONS_PROFILE, LGE21_TURNOUT, codes))
    out["election"] = "2021 local government (ward ballot)"
    out["source"] = SOURCE_23
    return out


# ---------------------------------------------------------------- 2024 ward results

def ward_results_table(turn: dict[str, dict], parties: dict[str, dict], top: int = 3) -> pd.DataFrame:
    """Per-municipality child_data dicts for 3001 and 3000 to one row per ward."""
    rows = []
    for code, wards in parties.items():
        for ward_id, data in wards.items():
            ranks = ranked(data, "political party")
            valid = sum(c for _, c in ranks)
            registered, share_voted = turnout(turn.get(code, {}).get(ward_id, []))
            row = {"ward_id": str(ward_id), "code": code, "registered_voters": registered,
                   "turnout_share": share_voted, "valid_votes": valid or None}
            for i in range(top):
                p, c = ranks[i] if i < len(ranks) else (None, None)
                row[f"party_{i + 1}"] = p.title() if p else None
                row[f"share_{i + 1}"] = c / valid if p and valid else None
            rows.append(row)
    return pd.DataFrame(rows).sort_values("ward_id").reset_index(drop=True)


def ward_results_2024(f: Fetcher | None = None, codes: list[str] | None = None) -> pd.DataFrame:
    """2024 national ballot turnout and the three largest parties in every ward.

    Columns: ward_id, code, registered_voters, turnout_share, valid_votes,
    party_1, share_1, party_2, share_2, party_3, share_3, election, source.
    Shares are of valid party votes in the ward. Special votes cast outside
    the voting district may be counted where the IEC assigned them.
    """
    f = f or Fetcher()
    codes = codes or ward_serving_codes(f)
    out = ward_results_table(_for_municipalities(f, ELECTIONS_PROFILE, NPE24_TURNOUT, codes),
                             _for_municipalities(f, ELECTIONS_PROFILE, NPE24_PARTY_VOTES, codes))
    out["election"] = "2024 national (national ballot)"
    out["source"] = SOURCE_23
    return out


# ---------------------------------------------------------------- census extras

def disability_share(rows: list[dict]) -> float | None:
    """Share of people with 'a lot of difficulty' or 'cannot do at all', unknowns left out of the base."""
    known = [r for r in rows if r.get("disability status") not in UNKNOWN]
    return share(known, "disability status", {"A lot of difficulty", "Cannot do at all"})


def census_extras_table(rdp: dict[str, list], heads: dict[str, list], seeing: dict[str, list],
                        walking: dict[str, list]) -> pd.DataFrame:
    """Indicator rows keyed by municipality code to one row per municipality."""
    codes = sorted(set(rdp) | set(heads) | set(seeing) | set(walking))
    rows = []
    for c in codes:
        rdp_known = [r for r in rdp.get(c, []) if r.get("rdp/government subsidised dwelling") not in UNKNOWN]
        see, walk = disability_share(seeing.get(c, [])), disability_share(walking.get(c, []))
        rows.append({
            "code": c,
            "rdp_household_share": share(rdp_known, "rdp/government subsidised dwelling", {"Yes"}),
            "female_headed_share": share(heads.get(c, []), "sex of the head of household", {"Female"}),
            "disability_seeing_share": see,
            "disability_walking_share": walk,
            # The two questions are published as separate tables, so people with
            # both difficulties cannot be removed; the larger of the two is a floor.
            "disability_floor_share": max(v for v in (see, walk) if v is not None) if see is not None or walk is not None else None,
        })
    return pd.DataFrame(rows)


def census_extras(f: Fetcher | None = None) -> pd.DataFrame:
    """Census 2022 extras per municipality (metros, districts and locals).

    Columns: code, rdp_household_share (households in an RDP or government
    subsidised dwelling, of those who answered), female_headed_share,
    disability_seeing_share, disability_walking_share (people with a lot of
    difficulty or who cannot do it at all), disability_floor_share (larger of
    the two; a lower bound on either), year, source. Census 2022 counts are
    weighted, so shares are what matter.
    """
    f = f or Fetcher()
    geos, _ = geography_tree(f, CENSUS22_PROFILE)
    districts = [g["code"] for g in geos if g["code"].startswith("DC")]
    out = census_extras_table(indicator_for_all(f, CENSUS22_PROFILE, RDP_HOUSEHOLDS, districts),
                              indicator_for_all(f, CENSUS22_PROFILE, HOUSEHOLD_HEAD_SEX, districts),
                              indicator_for_all(f, ELECTIONS_PROFILE, DISABILITY_SEEING, districts),
                              indicator_for_all(f, ELECTIONS_PROFILE, DISABILITY_WALKING, districts))
    out["year"] = 2022
    out["source"] = f"{API}/profile/{CENSUS22_PROFILE} (2812, 2801) and {API}/profile/{ELECTIONS_PROFILE} (2898, 2901), Census 2022"
    return out


# ---------------------------------------------------------------- GCRO

def gcro_table(data: dict[int, dict[str, list[dict]]]) -> pd.DataFrame:
    """{indicator: {code: rows}} to one row per municipality, question and survey year."""
    rows = []
    for ind, question, group, yes, drop in GCRO_QUESTIONS:
        for code, recs in data.get(ind, {}).items():
            for year in sorted({r.get("survey year") for r in recs if r.get("survey year")}):
                base = [r for r in recs if r.get("survey year") == year and r.get(group) not in drop]
                rows.append({"code": code, "indicator": ind, "question": question, "year": year,
                             "share": share(base, group, yes), "respondents_weighted": sum(float(r.get("count") or 0) for r in base)})
    return pd.DataFrame(rows)


def gcro_quality_of_life(f: Fetcher | None = None, latest_only: bool = True) -> pd.DataFrame:
    """GCRO Quality of Life survey answers for Gauteng metros, districts and local municipalities.

    Eight resident-facing questions (see GCRO_QUESTIONS). Columns: code,
    indicator, question, year (survey round, e.g. '2023/24'), share,
    respondents_weighted, source. With latest_only, only each code's latest
    round is kept. Local municipality samples are small; treat those shares
    as indicative.
    """
    f = f or Fetcher()
    data: dict[int, dict[str, list[dict]]] = {}
    for ind, *_ in GCRO_QUESTIONS:
        rows: dict[str, list[dict]] = {}
        for geo in ["GT", "DC42", "DC48"]:
            try:
                rows.update(child_data(f, GCRO_PROFILE, geo, ind))
            except (LookupError, RuntimeError):
                continue
        data[ind] = rows
    out = gcro_table(data)
    if latest_only and not out.empty:
        out = out[out["year"] == out.groupby("code")["year"].transform("max")].reset_index(drop=True)
    out["source"] = f"{API}/profile/{GCRO_PROFILE} (GCRO Quality of Life survey)"
    return out


__all__ = ["ward_councillors_2021", "ward_results_2024", "census_extras", "gcro_quality_of_life",
           "ward_councillors_table", "ward_results_table", "census_extras_table", "gcro_table",
           "split_name_party", "turnout", "disability_share", "ward_serving_codes"]
