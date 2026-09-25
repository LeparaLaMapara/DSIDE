#!/usr/bin/env bash
# Run the whole Masepala pipeline once with the Ubunye Engine (pandas backend),
# then stop. Nothing keeps running. Use REFRESH=true to ignore the cache.
# Run records (lineage) and the audit model registry go to registry/, which CI
# keeps on the `registry` branch (registry_state.sh); dside_engine.health reads them.
set -euo pipefail
cd "$(dirname "$0")"
export WORK_DIR="${WORK_DIR:-$PWD/.work}"
export SITE_DATA="${SITE_DATA:-$PWD/../web/data}"
export DSIDE_REGISTRY="${DSIDE_REGISTRY:-$PWD/registry/models}"
LINEAGE_DIR="${LINEAGE_DIR:-$PWD/registry/lineage}"
mkdir -p "$WORK_DIR" "$SITE_DATA" "$DSIDE_REGISTRY" "$LINEAGE_DIR"
ubunye validate -d pipelines -u dside -p municipal --all
ubunye run -d pipelines -u dside -p municipal --all --backend pandas --lineage --lineage-dir "$LINEAGE_DIR" -dt "$(date +%F)"
