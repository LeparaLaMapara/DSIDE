#!/usr/bin/env bash
# Move the last-good-copy snapshots to and from the `snapshots` branch.
#   ./snapshot_state.sh restore   before a run: bring back every source's last good copy
#   ./snapshot_state.sh publish   after a run: replace the branch with one commit of the latest copies
# The branch always holds a single commit, so the repository does not grow.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
dir="$root/engine/fallback/snapshots"
mkdir -p "$dir"

case "${1:-}" in
  restore)
    if git -C "$root" fetch -q origin snapshots 2>/dev/null; then
      git -C "$root" archive FETCH_HEAD | tar -x -C "$dir"
      rm -f "$dir/README.md"
      echo "restored $(ls "$dir" | wc -l) snapshot files"
    else
      echo "no snapshots branch yet; sources that fail will fail the run"
    fi
    ;;
  publish)
    tmp="$(mktemp -d)"
    git -C "$root" worktree add -q --detach "$tmp"
    (
      cd "$tmp"
      git checkout -q --orphan snapshots-new
      git rm -rq --cached . && find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
      cp -r "$dir/." .
      printf 'Last good copy of every Masepala source, replaced after each refresh by engine/snapshot_state.sh.\n' > README.md
      git add -A
      git -c user.name="dside-data-bot" -c user.email="dside-data-bot@users.noreply.github.com" \
        commit -q -m "Snapshots $(date -u +%FT%H:%MZ)"
      git push -q -f origin HEAD:snapshots
    )
    git -C "$root" worktree remove --force "$tmp"
    git -C "$root" branch -D snapshots-new >/dev/null 2>&1 || true
    echo "published snapshots"
    ;;
  *) echo "usage: $0 restore|publish" >&2; exit 2 ;;
esac
