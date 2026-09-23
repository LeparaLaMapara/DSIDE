#!/usr/bin/env bash
# The live layer: one pass, then stop. Run every few hours by the workflow.
set -euo pipefail
cd "$(dirname "$0")"
export SITE_DATA="${SITE_DATA:-$PWD/../web/data}"
export LIVE_DIR="${LIVE_DIR:-$PWD/../web/public/live}"
mkdir -p "$LIVE_DIR"
ubunye validate -d pipelines -u dside -p live --all
ubunye run -d pipelines -u dside -p live --all --backend pandas -dt "$(date +%F)"
