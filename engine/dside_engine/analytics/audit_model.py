"""Predict next year's audit outcome, and prove it beats a simple guess.

Target: does the municipality get an unqualified opinion (clean, or clean
with findings) in year t. Features: its opinions in the three years before,
how long its current streak is, its peer group and province.

The honest bar is the naive guess "same as last year". The model is only
published if it beats that guess on years it never saw (train up to t-2,
choose on t-1, test on the latest year). Otherwise the site shows the naive
guess and says the model did not add anything.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

GOOD = {"unqualified", "unqualified_emphasis_of_matter"}
RANK = {"unqualified": 5, "unqualified_emphasis_of_matter": 4, "qualified": 3, "adverse": 2,
        "disclaimer": 1, "outstanding": 0}


def panel(audits: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    a = audits.pivot_table(index="demarcation_code", columns="financial_year_end_year",
                           values="opinion_code", aggfunc="first")
    years = sorted(a.columns)
    rows = []
    for code, hist in a.iterrows():
        for i, y in enumerate(years[3:], start=3):
            prev = [hist[years[i - k]] for k in (1, 2, 3)]
            if any(pd.isna(p) for p in prev):
                continue
            streak = 0
            for p in prev:
                if (p in GOOD) == (prev[0] in GOOD):
                    streak += 1
                else:
                    break
            rows.append({"code": code, "year": y, "target": None if pd.isna(hist[y]) else int(hist[y] in GOOD),
                         "prev1": RANK[prev[0]], "prev2": RANK[prev[1]], "prev3": RANK[prev[2]],
                         "prev_good": int(prev[0] in GOOD), "streak": streak * (1 if prev[0] in GOOD else -1)})
        # the year after the last known one: what we predict
        last = [hist[years[-k]] for k in (1, 2, 3)]
        if not any(pd.isna(p) for p in last):
            streak = 0
            for p in last:
                if (p in GOOD) == (last[0] in GOOD):
                    streak += 1
                else:
                    break
            rows.append({"code": code, "year": years[-1] + 1, "target": None,
                         "prev1": RANK[last[0]], "prev2": RANK[last[1]], "prev3": RANK[last[2]],
                         "prev_good": int(last[0] in GOOD), "streak": streak * (1 if last[0] in GOOD else -1)})
    p = pd.DataFrame(rows).merge(meta[["code", "peer_group", "province"]], on="code", how="left")
    return pd.get_dummies(p, columns=["peer_group", "province"], dtype=float)


def fit_and_score(p: pd.DataFrame) -> dict:
    """Choose a model on the validation year, score it on the test year, refit on everything known.

    Returns the report (as published), the final fitted estimator, its feature
    names and the rows to predict (the year after the last known one).
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss

    feats = [c for c in p.columns if c not in {"code", "year", "target"}]
    known = p[p["target"].notna()]
    test_year = int(known["year"].max())
    val_year = test_year - 1
    future_year = test_year + 1

    candidates = {
        "logistic": lambda: LogisticRegression(max_iter=2000, C=0.5),
        "boosting": lambda: HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05, max_iter=200, random_state=0),
    }

    def fit(name, upto):
        tr = known[known["year"] <= upto]
        return candidates[name]().fit(tr[feats], tr["target"].astype(int))

    val = known[known["year"] == val_year]
    val_scores = {n: balanced_accuracy_score(val["target"].astype(int), fit(n, val_year - 1).predict(val[feats]))
                  for n in candidates}
    chosen = max(val_scores, key=val_scores.get)

    test = known[known["year"] == test_year]
    y = test["target"].astype(int)
    model = fit(chosen, test_year - 1)
    prob = model.predict_proba(test[feats])[:, 1]
    naive = test["prev_good"].astype(int)
    report = {
        "question": "Will the municipality get an unqualified audit (clean or clean with findings)?",
        "trained_on_years": f"{int(known['year'].min())} to {test_year - 1}",
        "tested_on_year": test_year,
        "model": chosen,
        "validation_balanced_accuracy": {k: round(v, 3) for k, v in val_scores.items()},
        "test": {
            "n": int(len(test)),
            "model_accuracy": round(accuracy_score(y, prob >= 0.5), 3),
            "model_balanced_accuracy": round(balanced_accuracy_score(y, prob >= 0.5), 3),
            "model_brier": round(brier_score_loss(y, prob), 3),
            "naive_accuracy": round(accuracy_score(y, naive), 3),
            "naive_balanced_accuracy": round(balanced_accuracy_score(y, naive), 3),
            "naive_brier": round(brier_score_loss(y, naive.clip(0.02, 0.98)), 3),
        },
        "predicts_year": future_year,
    }
    report["model_beats_naive"] = bool(report["test"]["model_brier"] < report["test"]["naive_brier"]
                                       and report["test"]["model_balanced_accuracy"] >= report["test"]["naive_balanced_accuracy"])
    return {"report": report, "estimator": fit(chosen, test_year), "features": feats,
            "future": p[p["year"] == future_year].copy(), "known": known}


def naive_prediction(future: pd.DataFrame) -> pd.Series:
    """The simple guess: same as last year."""
    return future["prev_good"].astype(float)


def evaluate_and_predict(p: pd.DataFrame, registry: str | None = None) -> tuple[pd.DataFrame, dict]:
    """Predict next year's audits and report how the prediction was chosen.

    Without a registry the fresh model is used if it beats the simple guess,
    else the simple guess. With a registry (a folder, see audit_registry.py)
    the Ubunye model registry decides: the fresh model is registered and only
    replaces the live version if it passes the promotion gates.
    """
    fitted = fit_and_score(p)
    report, future = fitted["report"], fitted["future"]
    if registry:
        from .audit_registry import govern

        chance, report["registry"] = govern(registry, fitted)
    else:
        chance = (fitted["estimator"].predict_proba(future[fitted["features"]])[:, 1]
                  if report["model_beats_naive"] else naive_prediction(future))
    future["chance_unqualified"] = chance
    return future[["code", "chance_unqualified"]].assign(predicted_year=report["predicts_year"]), report
