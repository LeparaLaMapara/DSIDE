"""Health after a run: sources, the gate on each task's run record, the verdict."""

import json
from datetime import datetime, timezone

from ubunye.lineage.context import RunContext, StepRecord
from ubunye.lineage.storage import FileSystemLineageStore

from dside_engine import health

NOW = datetime(2026, 11, 20, 6, 0, tzinfo=timezone.utc)
SINCE = "2026-11-20T04:00:00Z"


def record(store, task, run_id, started, rows, status="success", expectations=()):
    store.save(RunContext(
        run_id=run_id, task_path=f"dside/municipal/{task}", usecase="dside", package="municipal", task_name=task,
        profile="DEV", model="etl", version="1.0.0", config_hash="sha256:c", started_at=started,
        duration_sec=12.0, status=status,
        outputs=[StepRecord(name="wards", direction="output", format="s3", location="x", row_count=rows,
                            data_hash=f"sha256:{rows}", schema_hash="sha256:s", hash_method="content")],
        expectations=list(expectations)))


def every_task(store, run_id, started, rows=4468, **kw):
    for t in health.TASKS:
        record(store, t, f"{run_id}-{t}", started, rows, **kw)


def write_status(path, **sources):
    path.write_text(json.dumps(sources), encoding="utf-8")
    return path


def test_a_clean_run_is_ok(tmp_path):
    store = FileSystemLineageStore(str(tmp_path / "lineage"))
    every_task(store, "old", "2026-08-20T04:10:00+00:00")
    every_task(store, "new", "2026-11-20T04:10:00+00:00", rows=4470)
    status = write_status(tmp_path / "status.json", wards={"ok": True, "fetched_at": "2026-11-20T04:20+00:00", "label": "wards"})
    report, tables = health.build(tmp_path / "lineage", SINCE, status, tmp_path / "none.json", NOW)
    assert report["status"] == "ok"
    assert all(t["baseline"] and t["status"] == "ok" for t in report["tasks"])
    assert len(tables) == len(health.TASKS)


def test_a_table_that_collapses_fails_the_gate(tmp_path):
    store = FileSystemLineageStore(str(tmp_path / "lineage"))
    every_task(store, "old", "2026-08-20T04:10:00+00:00")
    every_task(store, "new", "2026-11-20T04:10:00+00:00", rows=1200)
    report, _ = health.build(tmp_path / "lineage", SINCE, tmp_path / "missing.json", tmp_path / "none.json", NOW)
    assert report["status"] == "fail"
    assert any(g["rule"] == "rows" for g in report["tasks"][0]["gate"])


def test_a_task_that_did_not_run_and_a_broken_rule_fail(tmp_path):
    store = FileSystemLineageStore(str(tmp_path / "lineage"))
    broken = {"output": "wards", "rule": "ward_id_unique", "kind": "unique", "severity": "fail",
              "column": "ward_id", "failed": 3, "total": 4468, "passed": False}
    record(store, "01_ingest_money", "a", "2026-11-20T04:10:00+00:00", 4468, status="error", expectations=[broken])
    report, _ = health.build(tmp_path / "lineage", SINCE, tmp_path / "missing.json", tmp_path / "none.json", NOW)
    first, second = report["tasks"][0], report["tasks"][1]
    assert first["status"] == "fail" and first["expectations_broken"][0]["rule"] == "ward_id_unique"
    assert second["ran"] is False and second["status"] == "fail"


def test_a_last_good_copy_warns_and_a_very_old_one_fails(tmp_path):
    status = write_status(
        tmp_path / "status.json",
        treasury={"ok": False, "fetched_at": "2026-09-25T10:00+00:00", "failed_at": "2026-11-20T04:30+00:00",
                  "error": "HostDown", "label": "treasury_facts audit_opinions"},
        sassa={"ok": False, "fetched_at": "2026-03-01T10:00+00:00", "error": "timeout", "label": "srd_grants"},
    )
    by_label = {s["label"]: s for s in health.sources(json.loads(status.read_text()), NOW)}
    assert by_label["treasury_facts audit_opinions"]["status"] == "warn"
    assert by_label["srd_grants"]["status"] == "fail" and by_label["srd_grants"]["age_days"] > health.STALE_DAYS


def test_main_writes_history_and_an_issue(tmp_path):
    store = FileSystemLineageStore(str(tmp_path / "lineage"))
    every_task(store, "new", "2026-11-20T04:10:00+00:00")
    status = write_status(tmp_path / "status.json", t={"ok": False, "fetched_at": "2026-11-01T00:00+00:00",
                                                       "error": "HostDown", "label": "treasury"})
    code = health.main(["--lineage", str(tmp_path / "lineage"), "--since", SINCE, "--status", str(status),
                        "--meta", str(tmp_path / "none.json"), "--out", str(tmp_path / "latest.json"),
                        "--history", str(tmp_path / "history.jsonl"), "--issue", str(tmp_path / "issue.md")])
    assert code == 0  # a warning keeps the data, but still tells a person
    assert json.loads((tmp_path / "history.jsonl").read_text().splitlines()[0])["fallback"] == ["treasury"]
    assert "treasury" in (tmp_path / "issue.md").read_text()
