# Metric Uniqueness Validation Rules — `[U]` CI Gate

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Verifies that no metric duplicates an existing metric within the project. Prevents redundant definitions that fragment the metric layer and create conflicting numbers across dashboards and reports.

Binary pass/fail — blocks PR merge on failure. Hard block, no override.

## When it runs

On every metric in the file being validated. Performs a within-project scan of the project's own semantic-model and metrics YAML files, comparing each metric being validated against all other metrics found in those files.

## Self-exclusion

When validating an existing metric (i.e., the metric already exists in the project's semantic-model YAML), exclude it from the comparison set. Match on metric name + owner to identify "self." This prevents a metric from flagging itself as a duplicate.

## What it checks (in order)

Each check is progressively more expensive. Run them in order and stop at the first failure.

### 1. Exact name match (`exact_name_match`)

- Normalize the metric name: lowercase, replace hyphens with underscores, strip leading/trailing whitespace
- Scan all metrics across the project's semantic-model and metrics YAML files for metrics matching this normalized name
- **Self-exclusion:** If the metric being validated already exists in the project (same name + same owner), exclude it from results
- If any match remains → `critical` failure

### 2. Exact formula match (`exact_formula_match`)

- Extract `calculation_logic` from `config.meta.technical_details`
- Normalize the formula:
  - Strip all whitespace (spaces, tabs, newlines)
  - Lowercase everything
  - Standardize SQL function names to canonical forms: `count(`, `sum(`, `avg(`, `min(`, `max(`, `count_distinct(` (treat `count(distinct x)` as `count_distinct(x)`)
  - Normalize column ordering in commutative operations: sort operands alphabetically within `+` and `*` expressions (e.g., `b + a` → `a + b`)
  - Remove redundant parentheses
- Scan all metrics in the project that share at least one `source_semantic_model` with the metric being validated
- For each candidate, normalize its formula using the same rules
- **Self-exclusion:** Same rule as Check 1
- If any normalized formula matches exactly → `critical` failure

### 3. Definition equivalence (`definition_equivalent`)

- Extract `description` from the metric
- Scan all metrics in the project that share at least one base table or measure with the metric being validated (same scope as Check 2)
- **Self-exclusion:** Same rule as Check 1
- For each candidate metric, use LLM-based semantic comparison:
  - Input: the two `description` fields
  - Question: "Do these two descriptions describe the same business metric — same entity being counted/measured, same aggregation logic, same business purpose?"
  - Output: yes/no judgment
- Different phrasing of the same concept → match (e.g., "Total unique customers who ordered" vs "Count of distinct customers with at least one order")
- Different metrics with similar language → no match (e.g., "Total orders placed" vs "Total deliveries completed")
- If the LLM judges equivalence → `critical` failure

**Comparison scope:** Only compare against metrics that share at least one base table or measure. This bounds the candidate set and avoids false positives from unrelated metrics with coincidentally similar language.

## Failure response

On any uniqueness failure, present to the user:

```
⛔ Duplicate metric detected

Your metric '<new_metric_name>' conflicts with an existing metric:
- Existing metric: '<existing_name>' (owned by <owner_email>)
- Match type: <Exact name | Exact formula | Equivalent definition>
- Action: Cannot proceed. Contact the metric owner to discuss consolidation.
```

Resolution options:
- Rename the metric (if name collision)
- Change the formula (if formula collision)
- Remove the metric (if true duplicate)
- Contact existing owner to consolidate

## Check Counts

### Metrics — 3 `[U]` checks
1. `exact_name_match` against project metrics
2. `exact_formula_match` against project metrics after normalization
3. `definition_equivalent` via LLM comparison for metrics sharing base tables/measures

### dbt docs / Semantic Model / Few-Shot — 0 `[U]` checks
Uniqueness is a metrics-only concern.

## Notes for CI implementation

- Checks 1 and 2 are deterministic and can be implemented in CI pipelines directly; they operate on the project's YAML files on disk
- Check 3 (definition equivalence) requires LLM inference and is currently implemented at the skill level only (interactive sessions). CI pipelines should implement Checks 1 and 2; Check 3 can be added to CI when an LLM-backed CI step is available
- The source of truth is the within-project scan of semantic-model and metrics YAML files. The gate is always runnable from the project checkout — no external service dependency
