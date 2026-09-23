#!/usr/bin/env bash
# Move the live layer's files to and from the `live-data` branch.
#   ./live_state.sh restore   pull the fault memory before a run
#   ./live_state.sh publish   replace the branch with one commit of the latest files
# The branch always holds a single commit, so the repository does not grow.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
state="$root/engine/state"
live="$root/web/public/live"
mkdir -p "$state" "$live"

case "${1:-}" in
  restore)
    if git -C "$root" fetch -q origin live-data 2>/dev/null; then
      for f in tshwane_faults.csv tshwane_faults_cleared.csv; do
        git -C "$root" show "FETCH_HEAD:state/$f" > "$state/$f" 2>/dev/null || rm -f "$state/$f"
      done
      echo "restored fault memory from live-data"
    else
      echo "no live-data branch yet; starting fresh"
    fi
    ;;
  publish)
    tmp="$(mktemp -d)"
    git -C "$root" worktree add -q --detach "$tmp"
    (
      cd "$tmp"
      git checkout -q --orphan live-data-new
      git rm -rq --cached . && find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
      mkdir -p live state && cp -r "$live/." live/ && cp -r "$state/." state/
      printf 'Live files for masepala.vercel.app, replaced every few hours by engine/live_state.sh.\n' > README.md
      git add -A
      git -c user.name="dside-data-bot" -c user.email="dside-data-bot@users.noreply.github.com" \
        commit -q -m "Live data $(date -u +%FT%H:%MZ)"
      git push -q -f origin HEAD:live-data
    )
    git -C "$root" worktree remove --force "$tmp"
    git -C "$root" branch -D live-data-new >/dev/null 2>&1 || true
    echo "published live-data"
    ;;
  *) echo "usage: $0 restore|publish" >&2; exit 2 ;;
esac
