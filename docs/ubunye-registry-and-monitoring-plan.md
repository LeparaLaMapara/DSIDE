# Plan: model registry, promotion and monitoring on the Ubunye Engine

Status: **built on Ubunye 0.7.0 (2026-09-25).** Recorded 2026-09-24, built 2026-09-25. What was built differs from the plan in two places, noted below: source health uses `CONFIG.expectations` and the gate instead of `CONFIG.monitors`, and the alerting lives in `dside_engine/health.py`.

Masepala uses the Ubunye Engine today for the data pipeline only (config
tasks, reader plugins, validation, pandas backend, lineage). This plan adds the
engine's model registry, promotion gates and monitors, for the three genuine
use cases below and nothing more. Everything stays free: it runs in GitHub
Actions and is stored in the repository.

## The three use cases

1. **Registry and promotion: the audit prediction.** The only trained model
   (`engine/dside_engine/analytics/audit_model.py`, logistic regression,
   retrained every quarter). Each quarter's model is registered as a version
   with its test scores. It is promoted only if it beats the "same as last year"
   guess (Brier score and balanced accuracy) and the current live version;
   otherwise the live version stays, or the site shows the simple guess and says
   so. This replaces the hand-written `model_beats_naive` check.
2. **Source-health monitoring.** Government sources break quietly (SAPS moved a
   header row, Stats SA serves a bot page, SASSA and DWS block GitHub runners,
   Treasury's ready-made indicators are wrong). Every run checks each source for:
   freshness (fresh or fallback copy, and its age), size against the last run
   (wards about 4,468, schools about 25,500, faults about 1,700), shape
   (expected columns present), and plausibility (how many Treasury figures were
   flagged).
3. **Model against reality.** When Treasury publishes real audit outcomes for a
   year the model predicted, score those predictions (accuracy, calibration) and
   add the result to the model's record. Over the years this shows whether the
   model deserves its place on the site.

Not in scope: the wellbeing score, the story, comparisons and maps are fixed
methods, not trained models; they do not go in a registry.

## Where everything sits (all free)

| Piece | Where | Notes |
|---|---|---|
| Registry (model file and scores per version) | `registry` branch of this repo: `models/audit/v<N>/model.pkl`, `metadata.json` | A few KB per version; checked out as a folder in CI, so Ubunye uses plain `file://` storage |
| Promotion decision | Quarterly GitHub Action (`refresh-data.yml`) | Decision and reason written to the registry |
| Monitors | Both GitHub Actions (quarterly and every 3 hours) | History appended to `monitoring/history.jsonl` on the `registry` branch |
| Alerts | The workflow opens a GitHub Issue when a monitor fails | GitHub emails the maintainers; the engine only reports, the workflow alerts |
| Lineage records | Committed to the `registry` branch (or uploaded as Actions artifacts, kept 90 days) | Today they are lost when the runner stops |
| Public view | A `/status` page on the site reading the branch | Live model version, source health, age of any fallback copy |

Bigger models or files later: Cloudflare R2 (free 10 GB, S3 compatible), which
Ubunye's artifact stores already support by path prefix.

## Engine prerequisites (status after Ubunye 0.7.0)

1. Done in 0.7.0: `ubunye models promote` honours the model's promotion gates
   (a forced promotion is marked `promotion_forced`).
2. Still open: the config schema does not accept `CONFIG.monitors`, although the
   runtime reads it. Much of the source-health plan no longer needs it: 0.7.0
   adds `CONFIG.expectations` (not_null, unique, between, one_of, matches,
   row_count, with fail, quarantine or warn), checked before anything is written.
3. Still to prove: the model registry on the pandas backend.
4. Done in 0.7.0: run record v2 has real row counts and data hashes on pandas,
   plus input hashes, a code hash and an environment hash. Verified on Masepala's
   run: 32 of 32 inputs hashed and counted, every output with a distinct hash.
5. Done: 0.7.0 is on PyPI with the pandas backend, and Masepala depends on
   `ubunye-engine[pandas]>=0.7,<0.8` instead of a pinned commit.

What moving to 0.7.0 needed in Masepala: transforms now receive plain,
Arrow-backed DataFrames (so `.native` went away and `dside_engine/frames.py`
converts to numpy-backed pandas at the boundary), and the built-in writers now
lay files out the way Spark does (a folder of part files), so site files are
written by Masepala's own `site_json` writer plugin. The published data was
identical before and after (257 municipalities, 4,468 wards, 25,224 schools,
0 differences on key fields).

## What was built (2026-09-25)

1. Done: the engine is a released dependency (0.7.x).
2. Done: the audit model is an `UbunyeModel` (`dside_engine/analytics/audit_registry.py`),
   registered from `04_analyse` whenever the audit history changes. Promotion
   gates: `min_brier_gain` 0.001 and `min_balanced_accuracy_gain` 0 against the
   simple guess, and `max_model_brier` against the live version (its recorded
   score on the same test year, or its score on the new year it never saw).
   A blocked version stays registered; the live one keeps predicting.
3. Done: `CONFIG.expectations` on every ingest task, the analysis and the live
   task (row counts, codes present and unique, shares and percentages in range,
   known audit opinions quarantined). `dside_engine/health.py` gates each task's
   run record against the previous one with the engine's gate
   (`allow_data_change`, `max_row_change` 0.25).
4. Done: `state_branch.sh` (with `registry_state.sh` and `snapshot_state.sh`)
   restores and publishes the `registry` branch: `models/`, `lineage/`,
   `openlineage/`, `monitoring/latest.json` and `monitoring/history.jsonl`.
5. Done: the quarterly workflow opens or comments on a `data-health` issue when
   the health is not ok, and only commits new data when the run and the health
   check pass.
6. Done: every live version stores its predictions; `track_record` scores them
   once the real outcomes are published.
7. Done: `/status` on the site, read in the browser from the `registry` branch.
8. Done: tests (`test_audit_registry.py`, `test_http.py`, `test_relay.py`, the
   snapshot shrink guard), README and About page.

Still open on the engine side: `CONFIG.monitors` is not in the config schema
(the expectations and the gate covered what Masepala needed without it).
