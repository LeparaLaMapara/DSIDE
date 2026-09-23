"""Ubunye Engine readers for the public South African sources.

Each reader turns one family of public API into a pandas DataFrame, so a
pipeline config can say `format: treasury_cube` the same way it says
`format: s3`. They are registered under the `ubunye.readers` entry point
group in pyproject.toml.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
from shapely.geometry import shape, mapping
from ubunye.adapters.pandas_adapter import PandasDataFrameAdapter
from ubunye.core.interfaces import Reader

from .http import Fetcher
from .sources import municipal_money as mm
from .sources import vulekamali as vk
from .sources import wazimap as wz


def _fetcher(cfg: dict) -> Fetcher:
    return Fetcher(refresh=str(cfg.get("refresh", "false")).lower() == "true")


def _frame(rows: list[dict] | pd.DataFrame, backend: Any):
    df = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    return PandasDataFrameAdapter(df) if not backend.is_spark else backend.spark.createDataFrame(df)


def _years(cfg: dict) -> list[int]:
    return [int(y) for y in str(cfg["years"]).split(",")]


class TreasuryCubeReader(Reader):
    """Annual cells from a Municipal Money cube for every municipality.

    cfg: cube, years ("2021,2022"), drilldown ("amount_type.code|item.code"),
    amount_types (optional, comma separated, filtered locally because the API
    does not accept multi-value cuts on text fields).
    """

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return [f"treasury_cube requires '{k}'" for k in ("cube", "years", "drilldown") if not cfg.get(k)]

    def read(self, cfg: dict, backend: Any):
        df = pd.DataFrame(mm.yearly(_fetcher(cfg), cfg["cube"], _years(cfg), cfg["drilldown"]))
        if cfg.get("amount_types") and "amount_type.code" in df:
            df = df[df["amount_type.code"].isin(cfg["amount_types"].split(","))]
        df.columns = [c.replace(".", "_") for c in df.columns]
        return _frame(df.reset_index(drop=True), backend)


class TreasuryFactsReader(Reader):
    """Row level facts: dataset is one of municipalities, audit_opinions, uifw."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        ok = {"municipalities", "audit_opinions", "uifw"}
        return [] if cfg.get("dataset") in ok else [f"treasury_facts 'dataset' must be one of {sorted(ok)}"]

    def read(self, cfg: dict, backend: Any):
        f = _fetcher(cfg)
        rows = {"municipalities": mm.municipalities, "audit_opinions": mm.audit_history, "uifw": mm.uifw}[cfg["dataset"]](f)
        df = pd.DataFrame(rows)
        df.columns = [c.replace(".", "_") for c in df.columns]
        return _frame(df, backend)


class WazimapIndicatorReader(Reader):
    """Long table of Wazimap indicator rows for every municipality.

    cfg: profile (8 or 14 or 23), indicators ("2818:water,2821:toilet"),
    level ("local" for local and metro municipalities).
    Output columns: code, indicator, count, plus one column per group.
    """

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return [f"wazimap_indicator requires '{k}'" for k in ("profile", "indicators") if not cfg.get(k)]

    def read(self, cfg: dict, backend: Any):
        f = _fetcher(cfg)
        geos, _ = wz.geography_tree(f)
        districts = [g["code"] for g in geos if g["code"].startswith("DC")]
        rows: list[dict] = []
        for pair in cfg["indicators"].split(","):
            ind_id, name = pair.split(":")
            for code, items in wz.indicator_for_all(f, int(cfg["profile"]), int(ind_id), districts).items():
                for item in items:
                    rows.append({"code": code, "indicator": name, **{k: v for k, v in item.items()}})
        df = pd.DataFrame(rows)
        df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0.0)
        df.columns = [c.replace(" ", "_") for c in df.columns]
        return _frame(df, backend)


class WazimapGeographyReader(Reader):
    """Every district, metro and local municipality with a simplified boundary.

    cfg: tolerance (degrees, default 0.004, about 400 m), which keeps the
    national map small enough for a phone on a slow connection.
    """

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        tol = float(cfg.get("tolerance", 0.004))
        geos, shapes = wz.geography_tree(_fetcher(cfg))
        for g in geos:
            geom = shape(shapes[g["code"]])
            simple = geom.simplify(tol, preserve_topology=True)
            g["geometry"] = json.dumps(_round(mapping(simple)))
            point = geom.representative_point()
            g["label_lng"], g["label_lat"] = round(point.x, 4), round(point.y, 4)
        return _frame(geos, backend)


class VulekamaliProjectsReader(Reader):
    """Every geolocated provincial and national infrastructure project."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        df = pd.DataFrame(vk.projects(_fetcher(cfg)))
        for c in ("latitude", "longitude", "estimated_total_project_cost"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return _frame(df, backend)


def _round(geojson: dict, nd: int = 4) -> dict:
    def r(c):
        return [round(c[0], nd), round(c[1], nd)] if isinstance(c[0], float) else [r(x) for x in c]

    return {"type": geojson["type"], "coordinates": r(list(json.loads(json.dumps(geojson["coordinates"]))))}


class SapsCrimeReader(Reader):
    """Latest SAPS quarterly crime per police station, linked to municipalities."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        from .sources import safety_jobs_wards as s

        refresh = str(cfg.get("refresh", "false")).lower() == "true"
        crime, url = s.crime_by_station(refresh)
        linked, unmatched = s.link_stations(crime, s.precincts(refresh))
        linked["source"] = url
        linked["unmatched_stations"] = ", ".join(unmatched)
        return _frame(linked, backend)


class QlfsReader(Reader):
    """Stats SA Quarterly Labour Force Survey trends (province, metro, age)."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        from .sources import safety_jobs_wards as s

        table, url = s.qlfs(str(cfg.get("refresh", "false")).lower() == "true")
        return _frame(table.assign(source=url), backend)


class WardReader(Reader):
    """Every ward of every local and metro municipality, with its MDB profile and shape."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        from .sources import safety_jobs_wards as s

        f = _fetcher(cfg)
        geos, _ = wz.geography_tree(f)
        codes = [g["code"] for g in geos if not g["code"].startswith("DC")]
        return _frame(s.wards(codes, f.refresh, float(cfg.get("offset", 0.0004))), backend)


class CouncillorReader(Reader):
    """Ward councillors where a city publishes them in a readable table (pilot: Tshwane)."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        return []

    def read(self, cfg: dict, backend: Any):
        from .sources import safety_jobs_wards as s

        return _frame(s.tshwane_councillors(str(cfg.get("refresh", "false")).lower() == "true"), backend)


class DsideSourceReader(Reader):
    """Any source in dside_engine.catalogue, by name (cfg: name, refresh)."""

    @classmethod
    def validate_config(cls, cfg: dict) -> list[str]:
        from .catalogue import SOURCES

        return [] if cfg.get("name") in SOURCES else [f"dside_source 'name' must be one of {sorted(SOURCES)}"]

    def read(self, cfg: dict, backend: Any):
        from .catalogue import load

        return _frame(load(cfg["name"], str(cfg.get("refresh", "false")).lower() == "true"), backend)
