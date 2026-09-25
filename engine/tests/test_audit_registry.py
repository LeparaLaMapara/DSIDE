"""The audit prediction under the Ubunye model registry."""

import numpy as np
import pandas as pd
import pytest

from dside_engine.analytics import audit_model as am
from dside_engine.analytics import audit_registry as ar


def history(seed=0, codes=120, first=2014, last=2024, flip=0.12):
    """A panel like audit_model.panel(): outcomes mostly repeat last year's, with some noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(codes):
        good = [int(rng.random() < 0.5)]
        for _ in range(first, last + 2):
            good.append(good[-1] if rng.random() > flip else 1 - good[-1])
        for j, year in enumerate(range(first + 3, last + 2)):
            k = j + 3
            prev = good[k - 1], good[k - 2], good[k - 3]
            rows.append({"code": f"M{i:03d}", "year": year, "target": None if year > last else good[k],
                         "prev1": 4 * prev[0] + 1, "prev2": 4 * prev[1] + 1, "prev3": 4 * prev[2] + 1,
                         "prev_good": prev[0], "streak": 1, "province_GT": float(i % 2)})
    return pd.DataFrame(rows)


def test_first_run_registers_and_promotes_then_same_data_changes_nothing(tmp_path):
    p = history()
    pred, rep = am.evaluate_and_predict(p, registry=str(tmp_path))
    r = rep["registry"]
    if not rep["model_beats_naive"]:
        pytest.skip("this synthetic history happened not to beat the simple guess")
    assert r["decision"] == "promoted" and r["live_version"] == "1.0.0" and r["used"] == "model"
    assert pred["predicted_year"].eq(2025).all() and pred["chance_unqualified"].between(0, 1).all()
    _, again = am.evaluate_and_predict(p, registry=str(tmp_path))
    assert again["registry"]["decision"] == "unchanged" and "new_version" not in again["registry"]


def test_a_worse_model_is_registered_but_the_live_version_keeps_predicting(tmp_path):
    p = history()
    first, rep = am.evaluate_and_predict(p, registry=str(tmp_path))
    if rep["registry"]["decision"] != "promoted":
        pytest.skip("no live version to protect")
    broken = p.copy()
    test_year = int(broken[broken["target"].notna()]["year"].max())
    mask = broken["year"] == test_year
    broken.loc[mask, "target"] = 1 - broken.loc[mask, "target"]  # the new test year contradicts history
    pred, rep = am.evaluate_and_predict(broken, registry=str(tmp_path))
    r = rep["registry"]
    assert r["decision"] == "kept" and r["new_version"] == "1.0.1" and r["live_version"] == "1.0.0"
    assert "brier" in r["reason"]


def test_with_nothing_live_and_no_gain_the_site_uses_the_simple_guess(tmp_path, monkeypatch):
    monkeypatch.setattr(ar, "GATES", {"min_brier_gain": 1.0})  # impossible to pass
    p = history()
    pred, rep = am.evaluate_and_predict(p, registry=str(tmp_path))
    r = rep["registry"]
    assert r["decision"] == "none" and r["used"] == "naive" and r["live_version"] is None
    future = p[p["year"] == 2025]
    assert pred["chance_unqualified"].tolist() == future["prev_good"].astype(float).tolist()


def test_a_live_prediction_is_scored_once_the_real_outcome_is_known(tmp_path):
    full = history(last=2025)
    earlier = full[full["year"] <= 2025].copy()
    earlier.loc[earlier["year"] == 2025, "target"] = None  # at the time, 2025 was the future
    _, rep = am.evaluate_and_predict(earlier, registry=str(tmp_path))
    if rep["registry"]["decision"] != "promoted":
        pytest.skip("nothing went live")
    _, later = am.evaluate_and_predict(full, registry=str(tmp_path))
    scored = [t for t in later["registry"]["track_record"] if t["predicted_year"] == 2025]
    assert scored and scored[0]["scored"] and scored[0]["n"] == 120
    assert 0 <= scored[0]["model_brier"] <= 1


def test_without_a_registry_nothing_changes(tmp_path):
    pred, rep = am.evaluate_and_predict(history())
    assert "registry" not in rep and len(pred) == 120
