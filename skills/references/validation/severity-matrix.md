# Issue Severity Matrix

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Severity levels for all validation check types. Used when generating the validation report to classify each issue.

## Severity Levels

| Severity | Definition | Impact |
|----------|------------|--------|
| `critical` | CI gate failure — missing YAML key, invalid syntax, blank/spurious ownership, duplicate metric | Blocks merge. Not in trust score. |
| `warning` | Trust score failure — thin description, missing test, incomplete governance | Reduces trust score. Does not block merge. |
| `info` | Suggestion for improvement | No impact on score or merge. |

## Rules by Check Type

### Structural `[S]`
- Parse errors, missing required YAML keys → `critical`
- Invalid enum values, wrong syntax → `critical`
- Uses `tests:` instead of `data_tests:` → `critical` (will break in future dbt versions)
- Missing `version: 2` key → `info` (optional since dbt 1.5, recommended for clarity)
- Derived metric uses `input_metrics` instead of `metrics` → `critical` (will fail dbt parse)
- Cumulative metric uses deprecated `cumulative_type_params` / `type_params.measure` (pre-1.12 form) instead of `input_metric` + top-level `window:` (dbt 1.12+ spec) → `critical`

### Ownership `[O]`
- Blank ownership value → `critical` (CI gate blocks merge)
- Placeholder email (e.g., `employee-1@your-company.example.com`) → `critical` (CI gate blocks merge)
- Invalid email format or wrong domain → `critical` (CI gate blocks merge)

### Completeness `[D]`
- `requires_semantic_docs` field missing or not boolean → `critical` (CI gate blocks merge)
- `requires_semantic_docs: true` but semantic model + metrics file not found → `critical` (CI gate blocks merge)
- `requires_semantic_docs: true` but few-shot file not found → `critical` (CI gate blocks merge)
- `requires_semantic_docs: false` but semantic model file exists → `info` (reviewer should confirm tag)

### Uniqueness `[U]`
- Exact name match with existing metric in catalog → `critical` (CI gate blocks merge)
- Exact formula match with existing metric in catalog (after normalization) → `critical` (CI gate blocks merge)
- Semantically equivalent definition (LLM-judged) with existing metric → `critical` (CI gate blocks merge)

### Data Context `[C]`
- Missing description → `warning`
- Thin description (under 10 words) → `warning`
- Blank meta context value (calculation_logic, interpretation) → `warning`

### Data Quality `[Q]`
- Missing PK data_tests → `warning`
- Missing FK relationship data_tests → `warning`
- Invalid governance date format → `warning`
- Suggestion to add ratio/derived metrics → `info`
- Suggestion to add accepted_values → `info`
