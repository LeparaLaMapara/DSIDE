"""Source and model health after a run, from what the Ubunye Engine recorded.

Reads, for one run of the quarterly pipeline:

* each source's state (snapshots.py status.json): fresh, or a last good copy and how old;
* each task's Ubunye run record: did it succeed, which expectations broke;
* the Ubunye gate: this run against the previous one (a row count that moved
  by more than MAX_ROW_CHANGE fails, as does a broken ``fail`` expectation);
* the audit model's registry decision and track record (meta.json).

Writes health.json (the site's /status page reads it from the `registry`
branch), appends a line to the monitoring history, writes the gate tables to
the CI job summary, and writes an issue body when anything needs a person.
Exit code 1 when the verdict is "fail": the workflow then keeps the old data
on the site and opens an issue.

    python -m dside_engine.health --lineage registry/lineage --since 2026-09-25T10:00:00 \
        --out registry/monitoring/latest.json --history registry/monitoring/history.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ubunye.core import gate as gate_rules
from ubunye.lineage.storage import FileSystemLineageStore

from . import snapshots

TASKS = ["01_ingest_money", "02_ingest_people", "03_ingest_places", "03b_ingest_fresh", "04_analyse", "05_publish"]
PACKAGE = "dside/municipal"
MAX_ROW_CHANGE = 0.25
STALE_DAYS = 120  # a last good copy older than this is a failure, not a warning
RANK = {"ok": 0, "warn": 1, "fail": 2}


def _days_since(stamp: str | None, now: datetime) -> float | None:
    if not stamp:
        return None
    return round((now - _when(stamp)).total_seconds() / 86400, 1)


def _when(stamp: str) -> datetime:
    t = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def sources(status: dict, now: datetime) -> list[dict]:
    out = []
    for key, s in sorted(status.items(), key=lambda kv: kv[1].get("label", kv[0])):
        age = _days_since(s.get("fetched_at"), now)
        verdict = "ok" if s.get("ok") else ("fail" if age is None or age > STALE_DAYS else "warn")
        out.append({"key": key, "label": s.get("label", key), "status": verdict, "fresh": bool(s.get("ok")),
                    "fetched_at": s.get("fetched_at"), "age_days": age, "rows": s.get("rows"),
                    "failed_at": s.get("failed_at"), "error": s.get("error")})
    return out


def tasks(lineage: Path, since: str, policy: gate_rules.Policy) -> tuple[list[dict], list[str]]:
    start = _when(since)
    out, tables = [], []
    for name in TASKS:
        # One store per task: `ubunye run --all` gives every task the same run id, and the
        # store caches records by run id alone, so a shared store would hand task 2 the
        # record of task 1 (Ubunye Engine 0.7.0).
        store = FileSystemLineageStore(base_dir=str(lineage))
        runs = sorted(store.list_runs(f"{PACKAGE}/{name}", n=1_000_000), key=lambda r: r.started_at, reverse=True)
        current = [r for r in runs if _when(r.started_at) >= start]
        if not current:
            out.append({"task": name, "status": "fail", "ran": False, "detail": "did not run (an earlier task stopped the run)"})
            continue
        cand = current[0]
        base = next((r for r in runs if _when(r.started_at) < start and r.status == "success"), None)
        broken = [e for e in cand.expectations if not e.get("passed")]
        entry = {"task": name, "ran": True, "run_id": cand.run_id, "run_status": cand.status,
                 "seconds": cand.duration_sec, "error": (cand.error or None) and cand.error[:300],
                 "expectations_checked": len(cand.expectations),
                 "expectations_broken": [{k: e.get(k) for k in ("output", "rule", "severity", "failed", "total")}
                                         for e in broken],
                 "outputs": {s.name: s.row_count for s in cand.outputs}}
        if base is None:
            findings = [f for f in gate_rules.evaluate(cand, cand, policy) if f.rule in ("run", "expectation")]
            entry["baseline"] = None
        else:
            # A refresh exists to change the data: an allowed change is expected, not a warning.
            findings = [gate_rules.Finding(f.rule, gate_rules.OK, f.detail, f.output)
                        if f.rule == "data" and f.detail.startswith("changed (allowed)") else f
                        for f in gate_rules.evaluate(base, cand, policy)]
            entry["baseline"] = base.run_id
            tables.append(gate_rules.markdown(findings, base, cand))
        # A broken `warn` rule is a known gap in a source (a few rows without a code): shown,
        # but it does not call a person every quarter. Quarantined rows and `fail` rules do.
        notes = [f for f in findings if f.rule == "expectation" and f.status == gate_rules.WARN
                 and not f.detail.endswith("(quarantined)")]
        findings = [f for f in findings if f not in notes]
        entry["notes"] = [f.as_dict() for f in notes]
        entry["gate"] = [f.as_dict() for f in findings if f.status != gate_rules.OK]
        entry["status"] = max((f.status for f in findings), key=RANK.get, default="ok")
        out.append(entry)
    return out, tables


def model(meta_path: Path) -> dict | None:
    if not meta_path.exists():
        return None
    rows = json.loads(meta_path.read_text(encoding="utf-8"))
    info = json.loads(rows[0]["json"]) if isinstance(rows, list) else rows
    audit = info.get("audit_model", {})
    reg = audit.get("registry")
    if not reg:
        return {"status": "ok", "used": "model" if audit.get("model_beats_naive") else "naive", "registry": None}
    status = "warn" if reg.get("decision") in ("kept", "none") else "ok"
    return {"status": status, **{k: reg.get(k) for k in ("decision", "reason", "live_version", "new_version",
                                                          "used", "gates", "track_record")},
            "test": audit.get("test"), "tested_on_year": audit.get("tested_on_year"),
            "predicts_year": audit.get("predicts_year")}


def build(lineage: Path, since: str, status_file: Path, meta_path: Path, now: datetime | None = None) -> tuple[dict, list[str]]:
    now = now or datetime.now(timezone.utc)
    policy = gate_rules.Policy(allow_data_change=True, max_row_change=MAX_ROW_CHANGE)
    src = sources(json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {}, now)
    tsk, tables = tasks(lineage, since, policy)
    mdl = model(meta_path)
    parts = [s["status"] for s in src] + [t["status"] for t in tsk] + ([mdl["status"]] if mdl else [])
    overall = max(parts, key=RANK.get, default="ok")
    report = {"checked_at": now.isoformat(timespec="minutes"), "status": overall,
              "rules": {"max_row_change": MAX_ROW_CHANGE, "stale_days": STALE_DAYS},
              "sources": src, "tasks": tsk, "model": mdl}
    return report, tables


def issue_body(report: dict, run_url: str | None) -> str:
    lines = [f"The quarterly Masepala refresh finished with status **{report['status']}** "
             f"({report['checked_at']}).", ""]
    if run_url:
        lines += [f"Run: {run_url}", ""]
    bad_src = [s for s in report["sources"] if s["status"] != "ok"]
    if bad_src:
        lines += ["**Sources on their last good copy**", ""]
        lines += [f"- {s['label']}: copy from {s['fetched_at'] or 'unknown'} ({s['age_days']} days); "
                  f"error: {s['error']}" for s in bad_src] + [""]
    for t in report["tasks"]:
        if t["status"] == "ok":
            continue
        lines.append(f"**{t['task']}**: {t.get('detail') or t.get('error') or ''}")
        lines += [f"- {g['rule']} {g.get('output') or ''}: {g['detail']}" for g in t.get("gate", [])]
        lines.append("")
    m = report.get("model")
    if m and m["status"] != "ok":
        lines += [f"**Audit model**: {m.get('decision')}: {m.get('reason')}", ""]
    lines.append("Written by engine/dside_engine/health.py. The site keeps showing the last good data "
                 "when the status is fail.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lineage", type=Path, required=True)
    ap.add_argument("--since", required=True, help="ISO time the run started; older records are the baseline")
    ap.add_argument("--status", type=Path, default=snapshots.STATUS)
    ap.add_argument("--meta", type=Path, default=Path(__file__).resolve().parents[2] / "web" / "data" / "meta.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--history", type=Path)
    ap.add_argument("--summary", type=Path, help="append the gate tables here ($GITHUB_STEP_SUMMARY)")
    ap.add_argument("--issue", type=Path, help="write an issue body here when the status is not ok")
    ap.add_argument("--run-url")
    a = ap.parse_args(argv)

    report, tables = build(a.lineage, a.since, a.status, a.meta)
    report["run_url"] = a.run_url
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    if a.history:
        a.history.parent.mkdir(parents=True, exist_ok=True)
        line = {"checked_at": report["checked_at"], "status": report["status"], "run_url": a.run_url,
                "fallback": [s["label"] for s in report["sources"] if not s["fresh"]],
                "tasks": {t["task"]: t["status"] for t in report["tasks"]},
                "rows": {t["task"]: t.get("outputs") for t in report["tasks"] if t.get("ran")},
                "model": report["model"] and {k: report["model"].get(k) for k in ("decision", "live_version", "used")}}
        with a.history.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    if a.summary:
        with a.summary.open("a", encoding="utf-8") as fh:
            fh.write(f"## Masepala health: {report['status']}\n\n" + "\n".join(tables) + "\n")
    if a.issue and report["status"] != "ok":
        a.issue.write_text(issue_body(report, a.run_url), encoding="utf-8")
    print(f"health: {report['status']} "
          f"({sum(not s['fresh'] for s in report['sources'])} sources on a last good copy, "
          f"{sum(t['status'] == 'fail' for t in report['tasks'])} tasks failing)")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
