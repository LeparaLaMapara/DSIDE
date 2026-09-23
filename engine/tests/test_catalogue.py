"""A failing outside website must fall back to its last good copy, not stop the run."""

import json

import pandas as pd
import pytest

from dside_engine import catalogue


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(catalogue, "SNAPSHOTS", tmp_path)
    monkeypatch.setattr(catalogue, "STATUS", tmp_path / "status.json")
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
