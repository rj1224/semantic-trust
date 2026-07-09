# Data Quality Scoring Rules — `[Q]` Trust Score

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Measures whether the document ensures data correctness: foreign key relationships defined with cardinality, `agg_time_dimension` set and matching, time dimensions have granularity, governance dates in valid format, version tracking, measure references valid.

**Weight:** 40% of trust score

Important for auditability, runtime correctness, and semantic layer reliability.

## Trust Score Formula (quality component)

```
data_quality_score = (Q_checks_passed / Q_checks_total) × 100
weighted_quality = data_quality_score × 0.40
```

## Check Counts by Document Type

### dbt docs — 6 `[Q]` checks
1. Primary key has `data_tests: [not_null, unique]`
2. Foreign key columns have `data_tests: [relationships]` pointing to valid `ref()` models
3. Timestamp columns have `data_tests` (freshness, not_null)
4. Categorical columns have `accepted_values` where applicable
5. Row count or expression tests present for business logic assertions
6. `data_tests` use correct syntax (not deprecated `tests:`)

### Semantic Model — 4 `[Q]` checks
1. Foreign entity relationships defined with valid cardinality
2. `defaults.agg_time_dimension` is set and matches an existing time dimension name
3. At least one time dimension exists (required if measures exist)
4. Time dimensions have column-level `granularity:` set (dbt-core 1.12+ spec)

### Metrics — 4 `[Q]` checks
1. Governance date (`approval_date`) is valid ISO format
2. Version field is valid semver or integer format
3. Measure references are valid (referenced measures exist in source SM)
4. Metric alias (if used) matches naming conventions

### Few-Shot — 6 `[Q]` checks
1. SQL syntax is valid (parseable)
2. Uses fully qualified table names (`DATABASE.SCHEMA.TABLE`)
3. Column names in SQL match actual columns in the model
4. NULL handling is explicit where applicable
5. Difficulty distribution has mix (not all same level)
6. SQL follows project conventions (CTEs, formatting)

## Severity

- Missing PK data_tests → `warning`
- Missing FK relationship data_tests → `warning`
- Invalid governance date format → `warning`
- Suggestion to add ratio/derived metrics → `info`
- Suggestion to add accepted_values → `info`
