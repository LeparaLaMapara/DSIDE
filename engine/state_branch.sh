#!/usr/bin/env bash
# Move a folder to and from a branch that always holds a single commit.
#   ./state_branch.sh restore <branch> <folder>   before a run: bring the folder back
#   ./state_branch.sh publish <branch> <folder>   after a run: replace the branch with one commit of it
# Used for the last good copies (`snapshots`) and the Ubunye model registry,
# run records and monitoring history (`registry`). The repository does not grow.
set -euo pipefail
action="${1:-}"; branch="${2:-}"; dir="${3:-}"
[ -n "$action" ] && [ -n "$branch" ] && [ -n "$dir" ] || { echo "usage: $0 restore|publish <branch> <folder>" >&2; exit 2; }
root="$(git rev-parse --show-toplevel)"
mkdir -p "$dir"
dir="$(cd "$dir" && pwd)"

case "$action" in
  restore)
    if git -C "$root" fetch -q origin "$branch" 2>/dev/null; then
      git -C "$root" archive FETCH_HEAD | tar -x -C "$dir"
      rm -f "$dir/README.md"
      echo "restored $(find "$dir" -type f | wc -l) files from $branch"
    else
      echo "no $branch branch yet; starting empty"
    fi
    ;;
  publish)
    tmp="$(mktemp -d)"
    git -C "$root" worktree add -q --detach "$tmp"
    (
      cd "$tmp"
      git checkout -q --orphan "$branch-new"
      git rm -rq --cached . && find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
      cp -r "$dir/." .
      printf 'Masepala state (%s), replaced after each run by engine/state_branch.sh. Do not edit by hand.\n' "$branch" > README.md
      git add -A
      git -c user.name="dside-data-bot" -c user.email="dside-data-bot@users.noreply.github.com" \
        commit -q -m "$branch $(date -u +%FT%H:%MZ)"
      git push -q -f origin "HEAD:$branch"
    )
    git -C "$root" worktree remove --force "$tmp"
    git -C "$root" branch -D "$branch-new" >/dev/null 2>&1 || true
    echo "published $branch"
    ;;
  *) echo "usage: $0 restore|publish <branch> <folder>" >&2; exit 2 ;;
esac
