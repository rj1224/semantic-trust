#!/usr/bin/env bash
# Detect drift between vendored dbt-labs spec refs and upstream main.
# exit 0 = current; exit 3 = drift; exit 1 = error.
set -euo pipefail

V="vendor/dbt-agent-skills/VERSION"

pinned=$(grep -oE 'commit:[[:space:]]*[0-9a-f]{40}' "$V" | grep -oE '[0-9a-f]{40}')
[ -n "$pinned" ] || { echo "error: no pinned commit in $V" >&2; exit 1; }

upstream=$(gh api repos/dbt-labs/dbt-agent-skills/commits/main --jq '.sha') || { echo "error: gh api call failed" >&2; exit 1; }

if [ "$pinned" = "$upstream" ]; then
  echo "vendor current at $pinned"
  exit 0
fi

echo "DRIFT: pinned $pinned -> upstream $upstream"

base="skills/dbt/skills/building-dbt-semantic-layer/references"
for f in latest-spec.md legacy-spec.md time-spine.md best-practices.md; do
  up=$(gh api "repos/dbt-labs/dbt-agent-skills/contents/$base/$f?ref=$upstream" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null || true)
  [ -n "$up" ] || { echo "warn: could not fetch $f from upstream" >&2; continue; }
  if ! diff -q <(printf '%s' "$up") "vendor/dbt-agent-skills/$f" >/dev/null 2>&1; then
    echo "--- changed: $f ---"
    diff <(printf '%s' "$up") "vendor/dbt-agent-skills/$f" || true
  fi
done

exit 3
