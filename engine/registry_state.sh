#!/usr/bin/env bash
# The Ubunye model registry, run records and monitoring history, on the single-commit `registry` branch.
#   ./registry_state.sh restore | publish
exec "$(dirname "$0")/state_branch.sh" "${1:-}" registry "$(dirname "$0")/registry"
