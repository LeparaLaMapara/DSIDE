# Plan: model registry, promotion and monitoring on the Ubunye Engine

Status: **engine side mostly ready as of Ubunye 0.7.0 (2026-09-25); Masepala runs on 0.7.0.** Recorded 2026-09-24, updated 2026-09-25.

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

## Masepala steps once the engine is ready

1. Done: the engine is now a released dependency (0.7.x).
2. Wrap the audit model as an `UbunyeModel` (train, predict, save, load,
   metadata) and register it from `04_analyse`, with a promotion gate against
   the naive baseline and the live version.
3. Add `CONFIG.expectations` to the ingest and publish tasks (row counts, codes
   not null and unique, shares between 0 and 1), and gate each quarterly run
   against the previous run record with `ubunye gate --max-row-change`.
4. Add a `registry_state.sh` like `live_state.sh`: restore the `registry` branch
   before a run, publish it after.
5. Add a workflow step that opens a GitHub Issue when a monitor fails.
6. Add the model-against-reality scoring when new audit years appear.
7. Add the `/status` page.
8. Tests for each, and update the README and About page.
