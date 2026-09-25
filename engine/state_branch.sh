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
    # Build the commit with a temporary index, so no checkout or working file is touched.
    index="$(mktemp)"; rm -f "$index"
    export GIT_INDEX_FILE="$index"
    git -C "$root" --work-tree="$dir" add -A -f .
    note="Masepala state ($branch), replaced after each run by engine/state_branch.sh. Do not edit by hand."
    readme="$(echo "$note" | git -C "$root" hash-object -w --stdin)"
    git -C "$root" update-index --add --cacheinfo "100644,$readme,README.md"
    tree="$(git -C "$root" write-tree)"
    bot=(-c user.name="dside-data-bot" -c user.email="dside-data-bot@users.noreply.github.com")
    commit="$(git -C "$root" "${bot[@]}" commit-tree "$tree" -m "$branch $(date -u +%FT%H:%MZ)")"
    rm -f "$index"; unset GIT_INDEX_FILE
    git -C "$root" push -q -f origin "$commit:refs/heads/$branch"
    echo "published $branch ($(git -C "$root" ls-tree -r --name-only "$commit" | wc -l) files)"
    ;;
  *) echo "usage: $0 restore|publish <branch> <folder>" >&2; exit 2 ;;
esac
