#!/usr/bin/env bash
# Regenerate committed semantic_manifest.json fixtures from source dbt projects.
# Latest-spec cases need dbt-core 1.12+; legacy-spec cases need dbt-core 1.6-1.11.
# Usage: scripts/build_fixture_manifests.sh <dbt-binary> <case> [<case> ...]
set -euo pipefail
DBT="$1"; shift
SRC="tests/fixtures/manifest_src"
OUT="tests/fixtures/manifests"
for case in "$@"; do
  proj="$SRC/$case"
  ( cd "$proj" && DBT_PROFILES_DIR=. DBT_PROJECT_DIR=. "$DBT" parse )
  mkdir -p "$OUT/$case/target"
  cp "$proj/target/semantic_manifest.json" "$OUT/$case/target/semantic_manifest.json"
  echo "built $case"
done
