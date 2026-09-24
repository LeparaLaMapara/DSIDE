#!/usr/bin/env bash
# Run the whole Masepala pipeline once with the Ubunye Engine (pandas backend),
# then stop. Nothing keeps running. Use REFRESH=true to ignore the cache.
set -euo pipefail
cd "$(dirname "$0")"
export WORK_DIR="${WORK_DIR:-$PWD/.work}"
export SITE_DATA="${SITE_DATA:-$PWD/../web/data}"
mkdir -p "$WORK_DIR" "$SITE_DATA"
ubunye validate -d pipelines -u dside -p municipal --all
ubunye run -d pipelines -u dside -p municipal --all --backend pandas --lineage -dt "$(date +%F)"
