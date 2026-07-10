#!/usr/bin/env bash
# Bump the vendored dbt-labs spec refs to upstream main IF they have drifted.
# Rewrites vendor/dbt-agent-skills/*.md + the pinned commit/date in VERSION.
# Used by .github/workflows/vendor-sync.yml, which opens a PR iff this produced changes.
# No-op (exit 0, no file changes) when already current.
set -euo pipefail

V="vendor/dbt-agent-skills/VERSION"
BASE="skills/dbt/skills/building-dbt-semantic-layer/references"
FILES=(latest-spec.md legacy-spec.md time-spine.md best-practices.md)

pinned=$(grep -oE '[0-9a-f]{40}' "$V" | head -1)
[ -n "$pinned" ] || { echo "error: no pinned commit in $V" >&2; exit 1; }

upstream=$(gh api repos/dbt-labs/dbt-agent-skills/commits/main --jq '.sha') \
  || { echo "error: could not reach upstream" >&2; exit 1; }

if [ "$pinned" = "$upstream" ]; then
  echo "vendor current at $pinned — no bump needed"
  exit 0
fi

echo "DRIFT: pinned $pinned -> upstream $upstream — applying bump"
for f in "${FILES[@]}"; do
  content=$(gh api "repos/dbt-labs/dbt-agent-skills/contents/$BASE/$f?ref=$upstream" --jq '.content' | base64 -d) \
    || { echo "error: could not fetch $f" >&2; exit 1; }
  printf '%s' "$content" > "vendor/dbt-agent-skills/$f"
done

today=$(date -u +%Y-%m-%d)
sed -i.bak "s/^commit:.*/commit: $upstream/" "$V" && rm -f "$V.bak"
sed -i.bak "s/^retrieved:.*/retrieved: $today/" "$V" && rm -f "$V.bak"
echo "bumped vendor/dbt-agent-skills to $upstream (retrieved $today)"
