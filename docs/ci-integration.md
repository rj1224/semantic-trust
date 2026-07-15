# Gating CI on semantic-trust

Run semantic-trust's **deterministic** trust score in CI to catch semantic-layer
regressions on every pull request — the "did my change break my trust score?" gate, the
same reflex as "did my change break my tests?".

## What runs in CI

The `semantic-trust` console script produces the **deterministic** report (gates + trust
score + band) from a compiled dbt manifest. It does **not** run the LLM-judgment layer —
that needs an interactive Claude session. CI gets the fast, fully reproducible half, which
is exactly what you want in a hot path: no model calls, no flakiness.

## Prerequisites

- Your dbt project compiles: `dbt parse` succeeds and emits `target/semantic_manifest.json`
  (semantic-trust reads that artifact — it never parses raw YAML).
- Pick the semantic model(s) to gate and a minimum trust band (e.g. `B`).

## Example GitHub Actions workflow

Drop this into your **dbt project** repo (not the semantic-trust repo):

```yaml
name: semantic-trust
on:
  pull_request:
    paths:
      - "models/**"
      - "**/*.yml"
jobs:
  trust:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dbt + semantic-trust
        run: pip install dbt-<your-adapter> semantic-trust
      - name: Compile the dbt project
        run: dbt parse # produces target/semantic_manifest.json
      - name: Trust gate
        env:
          MODEL: fct_orders # the semantic model to gate
          MIN_BAND: B
        run: |
          report="$(semantic-trust "$PWD" "$MODEL")"
          echo "$report" | python -m json.tool
          python - "$report" "$MIN_BAND" <<'PY'
          import json, sys
          report, min_band = json.loads(sys.argv[1]), sys.argv[2]
          rank = {"A": 5, "B": 4, "C": 3, "D": 2, "F": 1}
          failed = [g for g, ok in report.get("gates", {}).items() if not ok]
          band = report.get("band", "F")
          if failed:
              sys.exit("❌ trust gates failed: " + ", ".join(failed))
          if rank.get(band, 0) < rank.get(min_band, 0):
              sys.exit(f"❌ trust band {band} is below the required {min_band}")
          print(f"✅ {report['model']}: band {band}, all gates pass")
          PY
```

## Notes

- **Exit code:** the CLI prints the report and exits `0` regardless of score — the gate
  logic above turns the report into pass/fail. A first-class `--fail-under-band` flag is a
  planned enhancement to remove this boilerplate.
- **Multiple models:** loop over them and gate each.
- **Report shape:** the JSON carries `trust_score`, `band`, and a `gates` object
  (`structural` / `ownership` / `completeness` / `uniqueness` / `joinability`). Gate on
  whichever dimensions matter to you.
