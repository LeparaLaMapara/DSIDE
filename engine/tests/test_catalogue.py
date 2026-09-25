"""A failing outside website must fall back to its last good copy, not stop the run."""

import json

import pandas as pd
import pytest

from dside_engine import catalogue, snapshots


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(snapshots, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(snapshots, "STATUS", tmp_path / "status.json")
    return tmp_path


def test_success_saves_a_snapshot(isolated, monkeypatch):
    monkeypatch.setitem(catalogue.SOURCES, "demo", lambda r: pd.DataFrame({"code": ["TSH"], "v": [1]}))
    assert catalogue.load("demo")["v"].tolist() == [1]
    assert (isolated / "demo.parquet").exists()
    assert json.loads((isolated / "status.json").read_text())["demo"]["ok"] is True


def test_failure_uses_last_good_copy_and_records_it(isolated, monkeypatch):
    monkeypatch.setitem(catalogue.SOURCES, "demo", lambda r: pd.DataFrame({"code": ["TSH"], "v": [1]}))
    catalogue.load("demo")

    def broken(refresh):
        raise RuntimeError("site changed its page")

    monkeypatch.setitem(catalogue.SOURCES, "demo", broken)
    assert catalogue.load("demo")["v"].tolist() == [1]
    status = json.loads((isolated / "status.json").read_text())["demo"]
    assert status["ok"] is False and "site changed" in status["error"]


def test_failure_without_any_copy_still_raises(isolated, monkeypatch):
    def broken(refresh):
        raise RuntimeError("down")

    monkeypatch.setitem(catalogue.SOURCES, "demo", broken)
    with pytest.raises(RuntimeError):
        catalogue.load("demo")


def test_core_readers_fall_back_too(isolated):
    from dside_engine.connectors import SnapshotReader

    class Flaky(SnapshotReader):
        calls = 0

        def fetch(self, cfg):
            Flaky.calls += 1
            if Flaky.calls > 1:
                raise TimeoutError("treasury timed out")
            return pd.DataFrame({"code": ["TSH"]})

    class Backend:
        is_spark = False

    cfg = {"cube": "audit_opinions", "refresh": "false"}
    assert Flaky().read(cfg, Backend()).native["code"].tolist() == ["TSH"]
    assert Flaky().read({**cfg, "refresh": "true"}, Backend()).native["code"].tolist() == ["TSH"]  # same key, served from the copy
    key = snapshots.key_for("Flaky", cfg)
    assert json.loads((isolated / "status.json").read_text())[key]["ok"] is False


def test_a_shrunken_table_does_not_replace_a_good_copy(isolated, monkeypatch):
    monkeypatch.setitem(catalogue.SOURCES, "demo", lambda r: pd.DataFrame({"code": list("ABCDEFGHIJ")}))
    catalogue.load("demo")
    monkeypatch.setitem(catalogue.SOURCES, "demo", lambda r: pd.DataFrame({"code": ["A", "B"]}))
    assert len(catalogue.load("demo")) == 10
    status = json.loads((isolated / "status.json").read_text())["demo"]
    assert status["ok"] is False and "2 rows" in status["error"] and status["label"] == "demo"
