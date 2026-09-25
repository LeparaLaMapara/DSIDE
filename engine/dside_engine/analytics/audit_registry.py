"""The audit prediction under the Ubunye model registry: registered, gated, promoted, scored against reality.

Every quarterly run trains a fresh model (audit_model.fit_and_score). This
module decides whether the public site should use it:

1. If the audit data has not changed since the live version was trained,
   nothing is registered and the live version keeps predicting.
2. Otherwise the fresh model is registered as a new version, with its test
   scores. The engine's promotion gates must pass before it goes live:
   * it beats the simple guess "same as last year" on the error score (Brier)
     by at least MIN_BRIER_GAIN, and is at least as good on balanced accuracy;
   * it is no worse than the live version on the same test year.
   If a gate fails, the live version stays (or, with no live version, the site
   shows the simple guess and says so).
3. Every version that ever went live stored its predictions. Once real audit
   outcomes for that year are published, they are scored here, so the site can
   show whether the model deserved its place.

The registry is a folder (the `registry` branch in CI, see state_branch.sh).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from ubunye.core.errors import PromotionBlockedError
from ubunye.models import ModelRegistry, ModelStage, UbunyeModel

from .audit_model import naive_prediction

USE_CASE = "masepala"
MODEL_NAME = "audit_outcome"
MIN_BRIER_GAIN = 0.001
GATES = {"min_brier_gain": MIN_BRIER_GAIN, "min_balanced_accuracy_gain": 0.0}
BY = "masepala-refresh"


class AuditModel(UbunyeModel):
    """A fitted scikit-learn classifier plus the feature list it was trained on."""

    def __init__(self, estimator=None, features: list[str] | None = None, info: dict | None = None,
                 predictions: pd.DataFrame | None = None):
        self.estimator = estimator
        self.features = list(features or [])
        self.info = dict(info or {})
        self.predictions = predictions

    def train(self, df: pd.DataFrame) -> dict:
        self.estimator.fit(df[self.features], df["target"].astype(int))
        return {}

    def chance(self, df: pd.DataFrame) -> np.ndarray:
        # Peer groups and provinces are one-hot columns; a group unseen in training is all zeros.
        return self.estimator.predict_proba(df.reindex(columns=self.features, fill_value=0.0))[:, 1]

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[["code"]].assign(chance_unqualified=self.chance(df))

    def save(self, path: str) -> None:
        import joblib

        folder = Path(path)
        folder.mkdir(parents=True, exist_ok=True)
        joblib.dump({"estimator": self.estimator, "features": self.features, "info": self.info},
                    folder / "model.joblib")
        if self.predictions is not None:
            self.predictions.to_csv(folder / "predictions.csv", index=False)

    @classmethod
    def load(cls, path: str) -> "AuditModel":
        import joblib

        saved = joblib.load(Path(path) / "model.joblib")
        preds = Path(path) / "predictions.csv"
        return cls(saved["estimator"], saved["features"], saved["info"],
                   pd.read_csv(preds) if preds.exists() else None)

    def metadata(self) -> dict:
        import sklearn

        params = json.loads(json.dumps(self.estimator.get_params(), default=str))
        return {"library": "sklearn", "library_version": sklearn.__version__, "features": self.features,
                "params": params, **self.info}


def fingerprint(known: pd.DataFrame) -> str:
    """A hash of the audit history the model learned from: same history, same model."""
    rows = known[["code", "year", "target"]].sort_values(["code", "year"]).to_csv(index=False)
    return hashlib.sha256(rows.encode()).hexdigest()[:16]


def _brier(y: pd.Series, p: np.ndarray) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - y.astype(float).to_numpy()) ** 2))


def _live(reg: ModelRegistry):
    try:
        path, mv = reg.get_model(USE_CASE, MODEL_NAME, stage=ModelStage.PRODUCTION)
    except Exception:  # noqa: BLE001 - no registry yet, or nothing live yet
        return None, None
    return AuditModel.load(path), mv


def govern(registry: str, fitted: dict) -> tuple[np.ndarray, dict]:
    """Register the fresh model, let the promotion gates decide, predict with whatever is live."""
    reg = ModelRegistry(str(registry))
    report, known, future = fitted["report"], fitted["known"], fitted["future"]
    t = report["test"]
    test_year = report["tested_on_year"]
    live_model, live = _live(reg)
    fp = fingerprint(known)
    out = {"use_case": USE_CASE, "model": MODEL_NAME, "data_fingerprint": fp, "gates": dict(GATES)}

    if live is not None and live.metadata.get("data_fingerprint") == fp:
        out.update(decision="unchanged", reason="the audit history has not changed since the live version was trained")
    else:
        metrics = {**t, "tested_on_year": test_year,
                   "brier_gain": round(t["naive_brier"] - t["model_brier"], 4),
                   "balanced_accuracy_gain": round(t["model_balanced_accuracy"] - t["naive_balanced_accuracy"], 4)}
        gates = dict(GATES)
        if live is not None:
            test = known[known["year"] == test_year]
            if live.metrics.get("tested_on_year") == test_year:
                live_brier = float(live.metrics["model_brier"])  # same exam, recorded when it was sat
            else:
                live_brier = round(_brier(test["target"], live_model.chance(test)), 4)  # a year it never saw
            metrics["live_brier"] = live_brier
            gates["max_model_brier"] = live_brier
        info = {"data_fingerprint": fp, "kind": report["model"], "trained_on_years": report["trained_on_years"],
                "tested_on_year": test_year, "predicts_year": report["predicts_year"]}
        fresh = AuditModel(fitted["estimator"], fitted["features"], info)
        fresh.predictions = fresh.predict(future).assign(predicted_year=report["predicts_year"])
        mv = reg.register(USE_CASE, MODEL_NAME, None, fresh, metrics, registered_by=BY, promotion_gates=GATES)
        out.update(new_version=mv.version, gates=gates)
        try:
            reg.promote(USE_CASE, MODEL_NAME, mv.version, ModelStage.PRODUCTION, promoted_by=BY, gates=gates)
            out.update(decision="promoted", reason="the new version passed every gate")
        except PromotionBlockedError as exc:
            out.update(decision="kept" if live is not None else "none",
                       reason="; ".join(line.strip()[2:] for line in str(exc).splitlines()
                                        if line.strip().startswith("- ")))
        live_model, live = _live(reg)

    if live is not None:
        out.update(live_version=live.version, used="model", live_metrics=live.metrics)
        chance = live_model.chance(future)
    else:
        out.update(live_version=None, used="naive")
        chance = naive_prediction(future).to_numpy()
    out["track_record"] = track_record(reg, known)
    return chance, out


def track_record(reg: ModelRegistry, known: pd.DataFrame) -> list[dict]:
    """Every version that went live, scored on the real outcomes of the year it predicted (once known)."""
    try:
        versions = reg.list_versions(USE_CASE, MODEL_NAME)
    except Exception:  # noqa: BLE001 - nothing registered yet
        return []
    rows = []
    for v in sorted(versions, key=lambda v: v.registered_at):
        year = v.metadata.get("predicts_year")
        if not v.promoted_to_prod or year is None:
            continue
        actual = known[known["year"] == year]
        if actual.empty:
            rows.append({"version": v.version, "predicted_year": year, "scored": False})
            continue
        path, _ = reg.get_model(USE_CASE, MODEL_NAME, version=v.version)
        preds = AuditModel.load(path).predictions
        if preds is None:
            continue
        both = preds.merge(actual[["code", "target", "prev_good"]], on="code")
        y = both["target"].astype(int)
        rows.append({
            "version": v.version, "predicted_year": year, "scored": True, "n": int(len(both)),
            "model_accuracy": round(float(((both["chance_unqualified"] >= 0.5).astype(int) == y).mean()), 3),
            "model_brier": round(_brier(y, both["chance_unqualified"]), 3),
            "naive_accuracy": round(float((both["prev_good"].astype(int) == y).mean()), 3),
            "naive_brier": round(_brier(y, both["prev_good"].astype(float).clip(0.02, 0.98)), 3),
        })
    return rows
