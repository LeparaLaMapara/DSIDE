"""Last good copy of every source, so one slow government site cannot stop a refresh.

Every successful fetch is saved as a parquet snapshot. When a later fetch fails
(timeout, blocked runner, changed page), the snapshot is returned instead and
the failure is recorded in status.json, which the site's About page shows.

Snapshots live in engine/fallback/snapshots/ locally. In CI that folder is
restored from, and published back to, the single-commit `snapshots` branch
(see snapshot_state.sh), so the repository does not grow with every refresh.
A source that fails with no snapshot yet still fails the run.

A fetch that "works" but returns less than SHRINK_LIMIT of the rows of the last
good copy counts as a failure too (a site serving half a table, or a paging
bug), so a bad fetch can never replace a good copy. The run's declared
expectations (CONFIG.expectations) and `ubunye gate` then judge what was used.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SNAPSHOTS = Path(os.environ.get("DSIDE_SNAPSHOTS", Path(__file__).resolve().parent.parent / "fallback" / "snapshots"))
STATUS = SNAPSHOTS / "status.json"
SHRINK_LIMIT = 0.5
# Sources fetched elsewhere (the South African runner, see za-sources.yml): the
# run uses their copy as it is and leaves their status as that runner wrote it.
ZA_SOURCES = ("srd_grants", "water_quality")


def prefetched() -> set[str]:
    return {n.strip() for n in os.environ.get("DSIDE_PREFETCHED", "").split(",") if n.strip()}


def status() -> dict:
    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}


def key_for(kind: str, cfg: dict) -> str:
    """A stable name for one configured source (the refresh flag does not change it)."""
    settings = {k: v for k, v in sorted(cfg.items()) if k not in {"refresh", "format"}}
    digest = hashlib.sha1(json.dumps(settings, sort_keys=True, default=str).encode()).hexdigest()[:10]
    return f"{kind}-{digest}"


def _rows(snap: Path) -> int | None:
    try:
        import pyarrow.parquet as pq

        return pq.ParquetFile(snap).metadata.num_rows
    except Exception:  # noqa: BLE001 - no readable copy means nothing to compare with
        return None


def guarded(name: str, fetch: Callable[[], pd.DataFrame], label: str | None = None) -> pd.DataFrame:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    snap = SNAPSHOTS / f"{name}.parquet"
    state = status()
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")
    label = label or state.get(name, {}).get("label") or name
    if name in prefetched() and snap.exists():
        return pd.read_parquet(snap)
    try:
        df = fetch()
        df.attrs = {}  # run reports stay in logs; parquet cannot store arbitrary attrs
        if df.empty:
            raise ValueError("source returned no rows")
        before = _rows(snap) if snap.exists() else None
        if before and len(df) < SHRINK_LIMIT * before:
            raise ValueError(f"source returned {len(df)} rows, the last good copy has {before}")
        df.to_parquet(snap, index=False)
        state[name] = {"ok": True, "fetched_at": now, "rows": len(df), "label": label}
    except Exception as exc:  # noqa: BLE001 - any failure of an outside site
        if not snap.exists():
            raise
        df = pd.read_parquet(snap)
        last = state.get(name, {}).get("fetched_at")
        state[name] = {"ok": False, "fetched_at": last, "failed_at": now, "rows": len(df), "label": label,
                       "error": f"{type(exc).__name__}: {exc}"[:200]}
        print(f"[fallback] {name}: {exc}; using the copy from {last}")
    STATUS.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    return df


def adopt(folder: Path) -> list[str]:
    """Take the copies another runner fetched (a restored za-snapshots branch) into SNAPSHOTS.

    A copy only replaces ours when it is newer; its status entry comes with it.
    """
    theirs_file = Path(folder) / "status.json"
    if not theirs_file.exists():
        return []
    theirs = json.loads(theirs_file.read_text(encoding="utf-8"))
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    state, taken = status(), []
    for name, entry in theirs.items():
        src = Path(folder) / f"{name}.parquet"
        mine = state.get(name, {}).get("fetched_at") or ""
        if src.exists() and entry.get("fetched_at") and entry["fetched_at"] > mine:
            (SNAPSHOTS / src.name).write_bytes(src.read_bytes())
            state[name] = entry
            taken.append(name)
    STATUS.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    return taken


def _main(argv: list[str]) -> int:
    """python -m dside_engine.snapshots adopt <folder>   |   fetch-za <out folder>"""
    if len(argv) == 2 and argv[0] == "adopt":
        print("adopted:", ", ".join(adopt(Path(argv[1]))) or "nothing newer")
        return 0
    if len(argv) == 2 and argv[0] == "fetch-za":
        # On the South African runner: fetch only the sources that refuse foreign addresses.
        from . import catalogue

        out = Path(argv[1])
        out.mkdir(parents=True, exist_ok=True)
        failed = []
        for name in ZA_SOURCES:
            try:
                df = catalogue.SOURCES[name](True)
                if df.empty:
                    raise ValueError("no rows")
                df.attrs = {}
                df.to_parquet(out / f"{name}.parquet", index=False)
                now = datetime.now(timezone.utc).isoformat(timespec="minutes")
                entry = {"ok": True, "fetched_at": now, "rows": len(df), "label": name, "fetched_by": "za runner"}
                state = json.loads((out / "status.json").read_text(encoding="utf-8")) if (out / "status.json").exists() else {}
                state[name] = entry
                (out / "status.json").write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
                print(f"{name}: {len(df)} rows")
            except Exception as exc:  # noqa: BLE001 - report every source, fail at the end
                failed.append(f"{name}: {type(exc).__name__}: {exc}")
        for line in failed:
            print("FAILED", line)
        return 1 if failed else 0
    print(_main.__doc__)
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv[1:]))
