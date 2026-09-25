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
