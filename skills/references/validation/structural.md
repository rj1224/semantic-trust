# Structural Validation Rules — `[S]` CI Gate

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Verifies the document skeleton is correct. Template-generated docs should always pass. Binary pass/fail — blocks PR merge on failure.

## What it checks

- All required YAML keys exist (top-level keys, config sections, entity/measure/dimension fields)
- `config.meta` field keys exist for all ownership, freshness, technical_details, and governance fields (values can be blank — that's an ownership gate concern)
- Valid YAML syntax, no parse errors
- Correct enum values (entity types, agg types, dimension types, metric types)
- dbt-core 1.12+ compliance:
  - `data_tests` not `tests` (renamed in dbt 1.8+)
  - derived metrics use `input_metrics:` at metric level; presence of `type_params` on ratio/derived is a latest-spec VIOLATION (dbt-core 1.12+)
  - cumulative metrics use `input_metric` + top-level `window:` key (dbt 1.12+ spec — NOT `cumulative_type_params`)
  - `expr:` used, never `column:` (semantic models)

## When it fails

- A hand-authored doc missed required keys → fix the doc
- A template bug omitted a key → fix the template

## Check Counts by Document Type

### dbt docs — 14 `[S]` checks
1. `version: 2` key present (if present, must be `2`) — `info` if missing (optional since dbt 1.5)
2. `models:` top-level key is an array
3. `name:` field matches model name
4. `config:` section exists
5. `columns:` array exists and is non-empty
6. Each column has `data_type:` field
7. Column names follow snake_case naming convention
8. Uses `data_tests:` not `tests:` — `critical` if wrong
9. `config.meta.owner` key exists (value checked by ownership gate)
10. `config.meta.tags` key exists (value checked by ownership gate)
11. `config.meta.requires_semantic_docs` field exists
12. `config.meta.requires_semantic_docs` is boolean (true/false)
13. `description:` field exists at model level
14. `description:` field exists for each column

### Semantic Model — 21 `[S]` checks
1-16. Standard structure checks: top-level key, name, model ref, entities array, measures array, dimensions array, entity types valid, measure agg types valid, dimension types valid (`categorical` not `boolean`), `expr:` not `column:`, `defaults.agg_time_dimension` set, time dimension exists matching agg_time_dimension, config section exists, config.meta section exists, valid YAML syntax, no unknown top-level keys
17. `config.meta.business_owner` key exists
18. `config.meta.technical_owner` key exists
19. `config.meta.business_domain` key exists
20. `config.meta.refresh_cadence` key exists
21. `config.meta.tags` key exists

### Metrics — 23 `[S]` checks
1-12. Standard structure checks: top-level key, name, type valid, type_params absent (ratio/derived/cumulative in latest spec use direct keys — `type_params` is a latest-spec VIOLATION), label field, description field, config section, config.meta section, filter syntax valid, valid YAML, derived metrics use `input_metrics:` at metric level (NOT the legacy `metrics:` key nested under `type_params` — that is a pre-1.12 violation), cumulative metrics use `input_metric` + top-level `window:` key (dbt 1.12+ spec — NOT `cumulative_type_params`)
13. `config.meta.business_owner` key exists
14. `config.meta.technical_owner` key exists
15. `config.meta.business_domain` key exists
16. `config.meta.approved_by` key exists
17. `config.meta.technical_details.calculation_logic` key exists
18. `config.meta.technical_details.source_semantic_model` key exists
19. `config.meta.technical_details.interpretation` key exists
20. `config.meta.freshness.refresh_cadence` key exists
21. `config.meta.freshness.data_latency` key exists
22. `config.meta.governance.approval_date` key exists
23. `config.meta.governance.version` key exists

### Few-Shot — 4 `[S]` checks
1. Valid JSON syntax
2. `examples:` top-level key is an array
3. Each example has required fields: `question`, `sql`, `difficulty`
4. `difficulty` value is valid enum: `basic`, `intermediate`, `hard`
