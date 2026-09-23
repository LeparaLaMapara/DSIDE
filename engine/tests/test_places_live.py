"""Offline checks for the place-level live sources, on tiny hand-made inputs."""

import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from dside_engine.sources import places_live as pl


def square(x0, y0, x1, y1):
    return json.dumps({"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]})


WARDS = pd.DataFrame({
    "ward_id": ["79900090", "79900091"], "ward_no": [90, 91], "code": ["TSH", "TSH"],
    "geometry": [square(28.0, -25.6, 28.1, -25.5), square(28.1, -25.6, 28.2, -25.5)],
})
MUNIS = pd.DataFrame({
    "code": ["TSH", "JHB", "EC136", "MP312", "DC13", "DC31", "BUF"],
    "name": ["City of Tshwane Metro", "City of Johannesburg Metro", "Emalahleni", "Emalahleni",
             "Chris Hani District", "Nkangala District", "Buffalo City Metro"],
    "level": ["district_or_metro", "district_or_metro", "local", "local", "district_or_metro",
              "district_or_metro", "district_or_metro"],
    "parent": ["GT", "GT", "DC13", "DC31", "EC", "MP", "EC"],
    "geometry": [square(28.0, -25.6, 28.2, -25.5)] * 7,
})


def test_point_in_polygon_with_tiny_square_wards():
    loc = pl.WardLocator(WARDS, snap_km=1.0)
    codes, wards = loc.locate([-25.55, -25.55, -25.595, -30.0, np.nan], [28.05, 28.15, 28.2045, 25.0, 28.0])
    assert list(wards) == ["79900090", "79900091", "79900091", None, None]  # third point snaps in from 500 m
    assert list(codes) == ["TSH", "TSH", "TSH", None, None]


def test_swapped_and_sign_fixed_coordinates():
    lat, lng, fixes = pl.fix_coords(pd.Series([29.97, -25.54, 25.54, 10.0]), pd.Series([-31.15, 28.10, 28.10, 10.0]))
    assert lat.round(2).tolist()[:3] == [-31.15, -25.54, -25.54]
    assert lng.round(2).tolist()[:3] == [29.97, 28.10, 28.10]
    assert np.isnan(lat.iloc[3]) and fixes == {"swapped": 1, "sign_fixed": 1, "out_of_country": 1}


def test_northern_cape_stripped_decimals():
    # the NC provincial file drops the decimal point and also swaps the columns
    lat, lng, fixes = pl.fix_coords(pd.Series(["247247", "2474351"]), pd.Series(["-287158", "-2871433"]))
    assert lat.tolist() == [-28.7158, -28.71433]
    assert lng.tolist() == [24.7247, 24.74351]
    assert fixes["swapped"] == 2


def test_emis_page_picks_latest_quarter():
    page = ('<h2>Quarter 3 of 2025</h2><a href="/LinkClick.aspx?fileticket=NEW%3d&amp;tabid=1">National</a>'
            '<a href="/LinkClick.aspx?fileticket=NC%3d&amp;tabid=1">Northern Cape</a>'
            '<h2>Quarter 4 of 2024</h2><a href="/LinkClick.aspx?fileticket=OLD%3d">National</a> 3/17/2025')
    q, links = pl._emis_links(page)
    assert q == "Q3 2025"
    assert links["National"].endswith("fileticket=NEW%3d&tabid=1") and "Northern Cape" in links


def _markers(rows):
    return pd.DataFrame(rows, columns=["lat", "lng", "suburb", "street"])


def test_fault_snapshot_first_seen_and_cleared():
    t1 = datetime(2026, 9, 23, 8, tzinfo=timezone.utc)
    t2 = t1 + timedelta(hours=6)
    run1 = _markers([(-25.50001, 28.10001, "SOSHANGUVE-L", "A ST"), (-25.7, 28.2, "DORINGKLOOF", "B ST"),
                     (-25.7, 28.2, "DORINGKLOOF", "B ST")])
    cur1, cleared1 = pl.update_fault_snapshot(run1, None, t1)
    assert len(cleared1) == 0 and (cur1["open_hours"] == 0).all()
    assert cur1["fault_key"].nunique() == 3  # two faults at one spot stay separate
    # a round trip through CSV must still carry first_seen
    prev = pd.read_csv(pd.io.common.StringIO(cur1.to_csv(index=False)))
    run2 = _markers([(-25.500012, 28.100014, "Soshanguve-L", "A ST"), (-25.7, 28.2, "DORINGKLOOF", "B ST"),
                     (-25.9, 28.3, "MAMELODI", "C ST")])
    cur2, cleared2 = pl.update_fault_snapshot(run2, prev, t2)
    hours = dict(zip(cur2["suburb"], cur2["open_hours"]))
    assert hours["Soshanguve-L"] == 6.0 and hours["MAMELODI"] == 0.0
    assert len(cleared2) == 1 and cleared2["cleared_at"].iloc[0] == pd.Timestamp(t2)
    assert cleared2["open_hours"].iloc[0] == 6.0


def test_parse_fault_markers():
    page = ('<script>window.OUTAGE_MARKERS = [{"latitude":-25.5,"longitude":28.1,"district":"SOSHANGUVE-L",'
            '"street":"PL 1"}];\nvar m = window.OUTAGE_MARKERS || [];</script>')
    df = pl.parse_fault_markers(page)
    assert df.to_dict("records") == [{"lat": -25.5, "lng": 28.1, "suburb": "SOSHANGUVE-L", "street": "PL 1"}]


GAZ = pd.DataFrame([
    ("Soshanguve", -25.52, 28.05, 872309, "place", "TSH", 872309),
    ("Soshanguve", -25.49, 27.97, 0, "place", "NW371", 0),
    ("Mamelodi", -24.59, 31.02, 3619, "place", "MP324", 3619),
    ("Mamelodi", -25.55, 28.15, np.nan, "township", "TSH", 40),
    ("Pretoria", -25.74, 28.18, 2112693, "city", "TSH", 2112693),
    ("Jacaranda", -25.0, 28.0, 0, "place", "TSH", 0),
    ("Hope", -30.0, 25.0, 0, "place", "NC071", 0),
    ("Tiny", -25.55, 28.05, 0, "place", "TSH", 0),
    ("Blockhouse", -25.55, 28.05, 0, "place", "TSH", 0),
    ("Tshwane", -25.55, 28.05, np.nan, "township", "TSH", 2),
    ("Tshwane", -25.60, 28.30, np.nan, "municipality", "TSH", np.nan),
],columns=["name", "lat", "lng", "population", "kind", "code", "weight"])


def test_gazetteer_matching_stoplist_and_ambiguity():
    index, maxlen = pl._index_gazetteer(GAZ)
    assert "jacaranda" not in index and "hope" not in index and "tiny" not in index  # stoplist and min length
    keys = [k for _, k in pl.find_places("Jacaranda FM says Soshanguve residents march for water", index, maxlen)]
    assert keys == ["soshanguve"]
    assert pl.resolve_place(keys, index, None)["code"] == "TSH"  # largest population wins
    # a township from school suburbs beats the same name far away
    assert pl.resolve_place(["mamelodi"], index, None)["code"] == "TSH"
    # lower-case words are never places, and a name before 'FM' is an organisation
    assert pl.find_places("the soshanguve story", index, maxlen) == []
    assert pl.find_places("Pretoria FM", index, maxlen) == []


def test_geolocate_gives_ward_only_for_small_places():
    items = pd.DataFrame({"title": ["Water cut in Blockhouse", "Pretoria protest", "Tshwane fines drivers"],
                          "summary": ["", "", ""]})
    out = pl.geolocate_news(items, GAZ, WARDS, MUNIS)
    assert out["ward_id"].tolist() == ["79900090", None, None]  # a municipality name never gets a ward
    assert out["code"].tolist() == ["TSH", "TSH", "TSH"] and out["event"].tolist()[:2] == ["water", "protest"]


def test_municipality_names_and_ambiguous_shared_name():
    names = pl.muni_names(MUNIS)
    assert pl.match_municipality("R350 of 2026 - Buffalo City Municipality - Eastern Cape", names, MUNIS)[1] == "BUF"
    assert pl.match_municipality("Emalahleni Local Municipality, Mpumalanga", names, MUNIS)[1] == "MP312"
    assert pl.match_municipality("Emalahleni Local Municipality", names, MUNIS)[1] is None
    assert pl.match_municipality("Tshwane council meets", names, MUNIS)[1] == "TSH"


def test_dedup_by_url_then_near_identical_titles():
    t = pd.Timestamp("2026-09-22T08:00Z")
    items = pd.DataFrame({
        "title": ["Soshanguve residents protest over water", "Soshanguve residents protest over water!",
                  "Soshanguve residents protest over water", "Soshanguve residents protest over water"],
        "url": ["https://www.news24.com/a/?utm_source=x", "https://news24.com/a", "https://iol.co.za/b",
                "https://citizen.co.za/c"],
        "outlet": ["News24", "News24", "IOL", "The Citizen"],
        "published": [t, t, t + pd.Timedelta(hours=3), t + pd.Timedelta(hours=72)],
    })
    out = pl.dedupe_news(items)
    assert len(out) == 2  # same URL dropped; the 72-hour-later story is its own cluster
    assert out.iloc[0]["also_reported_by"] == "IOL" and out.iloc[1]["also_reported_by"] == ""
    assert pl.normalise_url("https://WWW.News24.com/a/?x=1#y") == "news24.com/a"


def test_event_keywords():
    assert pl.classify_event("Sewage spillage floods Mamelodi streets") == "sewage"
    assert pl.classify_event("Residents without water for a week") == "water"
    assert pl.classify_event("Load shedding back at stage 2") == "electricity"
    assert pl.classify_event("Man arrested for rape of teen") == "gbv"
    assert pl.classify_event("SIU probes tender fraud at municipality") == "corruption"
    assert pl.classify_event("Potholes swallow cars on the N4") == "roads"
    assert pl.classify_event("Matric learners write final exams") == "education"
    assert pl.classify_event("Cabinet reshuffle announced") == "other"
    assert pl.classify_event("Tender Q28-2026-27: supply of cleaning materials") == "other"  # a tender is not a scandal
