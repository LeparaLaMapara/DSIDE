# Plan: model registry, promotion and monitoring on the Ubunye Engine

Status: **waiting on the Ubunye Engine upgrade**. Recorded 2026-09-24.

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

## Engine prerequisites (do these in the Ubunye Engine repository, on its own branch)

1. `ubunye models promote` must run the promotion gates (today `cli/models.py`
   never passes `gates=`).
2. The config schema must accept `CONFIG.monitors` (today it is rejected,
   although the runtime reads it).
3. The model registry must be proven on the pandas backend (untested today).
4. Pandas lineage must record real row counts and data fingerprints (today
   `fingerprint_dataframe` returns the schema hash as the data hash and no row
   count, because the pandas adapter has no `sample()`).
5. Release the pandas backend (PRs #50 and #51, then 0.6.0) so Masepala can
   depend on a version instead of a pinned commit.

## Masepala steps once the engine is ready

1. Move the pin in `engine/pyproject.toml` from commit `c6ceb07` to the released
   version.
2. Wrap the audit model as an `UbunyeModel` (train, predict, save, load,
   metadata) and register it from `04_analyse`, with a promotion gate against
   the naive baseline and the live version.
3. Add `CONFIG.monitors` to the ingest tasks (freshness, row counts, expected
   columns) and to the live task.
4. Add a `registry_state.sh` like `live_state.sh`: restore the `registry` branch
   before a run, publish it after.
5. Add a workflow step that opens a GitHub Issue when a monitor fails.
6. Add the model-against-reality scoring when new audit years appear.
7. Add the `/status` page.
8. Tests for each, and update the README and About page.
