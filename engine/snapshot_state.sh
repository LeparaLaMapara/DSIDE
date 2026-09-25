#!/usr/bin/env bash
# The last good copy of every source, on the single-commit `snapshots` branch.
#   ./snapshot_state.sh restore | publish
exec "$(dirname "$0")/state_branch.sh" "${1:-}" snapshots "$(dirname "$0")/fallback/snapshots"
