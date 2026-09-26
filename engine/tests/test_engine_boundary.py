"""The two places Masepala meets Ubunye 0.7: frames coming in, site files going out."""

import datetime as dt
import json

import pandas as pd
import pyarrow as pa

from dside_engine.connectors import SiteJsonWriter
from dside_engine.frames import numpy_backed


def test_arrow_frames_become_the_dtypes_read_parquet_gives():
    arrow = pd.DataFrame({
        "code": pd.array(["TSH", "CPT"], dtype=pd.ArrowDtype(pa.string())),
        "n": pd.array([1, None], dtype=pd.ArrowDtype(pa.int64())),
        "m": pd.array([1, 2], dtype=pd.ArrowDtype(pa.int64())),
        "share": pd.array([0.5, None], dtype=pd.ArrowDtype(pa.float64())),
        "flag": pd.array([True, None], dtype=pd.ArrowDtype(pa.bool_())),
        "day": pd.array([dt.date(2026, 9, 21), None], dtype=pd.ArrowDtype(pa.date32())),
    })
    out = numpy_backed(arrow)
    assert str(out["n"].dtype) == "float64" and out["n"].isna().tolist() == [False, True]
    assert str(out["m"].dtype) == "int64"
    assert str(out["share"].dtype) == "float64"
    assert out["flag"].dtype == object and out["flag"].tolist() == [True, None]
    assert out["day"].tolist()[0] == dt.date(2026, 9, 21)
    assert not any(isinstance(t, pd.ArrowDtype) for t in out.dtypes)


def test_numpy_frames_pass_through_untouched():
    df = pd.DataFrame({"a": [1, 2]})
    assert numpy_backed(df) is df


def test_site_json_writes_one_array_file(tmp_path):
    class Backend:
        def to_native(self, frame):
            return frame

    path = tmp_path / "site" / "municipalities.json"
    SiteJsonWriter().write(pd.DataFrame({"code": ["TSH"], "score": [76.0]}), {"path": str(path)}, Backend())
    assert path.is_file()
    assert json.loads(path.read_text(encoding="utf-8")) == [{"code": "TSH", "score": 76.0}]
    assert not (tmp_path / "site" / "municipalities.json.tmp").exists()


def test_site_json_needs_a_path():
    assert SiteJsonWriter.validate_config({}) == ["site_json requires 'path'"]


def test_the_live_layer_is_never_blocked_by_its_own_checks():
    """One odd answer (Eskom says -1 at times) must never hold back the news and the faults."""
    from pathlib import Path

    import yaml

    cfg = yaml.safe_load((Path(__file__).resolve().parents[1] / "pipelines/dside/live/01_collect/config.yaml").read_text())
    rules = [r for spec in cfg["CONFIG"]["expectations"].values() for r in spec["rules"]]
    assert rules and all(r.get("severity") == "warn" for r in rules)
