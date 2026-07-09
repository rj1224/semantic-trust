# Documentation Completeness Rules — `[D]` CI Gate

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Verifies that a model has all the documents it declares it needs. This gate requires cross-file reasoning — it reads a field from the dbt doc and checks for the existence of other files. This is why validation operates at the model level, not on individual files.

Binary pass/fail — blocks PR merge on failure.

## What it checks

- `config.meta.requires_semantic_docs` field exists in the dbt doc and is a boolean
- If `requires_semantic_docs` is `true`: a semantic model + metrics file exists at `models/semantics/**/<model_name>.yml`
- If `requires_semantic_docs` is `true`: a few-shot examples file exists at `models/few_shot_examples/**/<model_name>.json`

## When `requires_semantic_docs` is `false`

- Gate passes automatically — only the dbt doc is required
- If a semantic model file happens to exist anyway, flag as `info` (not a gate failure) — the reviewer should confirm whether the tag needs updating

## When it fails

- `requires_semantic_docs: true` but semantic model + metrics file not found → author must create it
- `requires_semantic_docs: true` but few-shot file not found → author must create it
- `requires_semantic_docs` field missing or not a boolean → structural issue in the dbt doc

## Check Counts

### dbt docs — 3 `[D]` checks
1. If `requires_semantic_docs: true` → semantic model + metrics file exists
2. If `requires_semantic_docs: true` → few-shot file exists
3. Tag-mismatch info: if `requires_semantic_docs: false` but semantic file exists → `info`

### Semantic Model / Metrics / Few-Shot — 0 `[D]` checks
Completeness is checked at the model level via the dbt doc, not on individual semantic/metric/few-shot files.
