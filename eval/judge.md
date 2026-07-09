# LLM-Judge Protocol — dbt Semantic-Layer Generation Eval

**Domain:** qcommerce (orders, customers, delivery partners, dark stores)
**Skills under evaluation:** `document-semantics`, `build-dbt-model`
**Harness for deterministic half:** `python -m eval.harness` (Task 2.2)

---

## Inputs

1. A sample dbt project — use `tests/fixtures/qcommerce_latest` as the baseline.
2. A target raw SQL or existing model name.
3. The skill output: generated MetricFlow YAML (latest spec).

---

## Step 1 — Structural validation (hard gate)

Run:

```bash
mf validate-configs
```

**HARD GATE:** if `mf validate-configs` fails, the case is a **FAIL** regardless of trust band or any other dimension. Record the exact error message verbatim in `adversarial_failures`.

This gate runs first. No further steps are evaluated if it fails.

---

## Step 2 — Deterministic trust score

Run:

```bash
python -m trust.cli <project_dir> <model>
```

Record: `{band, gates, issues}`. A band below B or any failed gate is a finding.

---

## Step 3 — Structural correctness rubric

For each generated YAML, verify every row below. A failed row is a finding.

| Check | Pass criterion |
|---|---|
| Column fidelity | All entity, dimension, and measure names exist as real columns in the source model (verified against the dbt manifest); no hallucinated names. |
| Entity roles | At least one `primary` entity present; foreign keys annotated correctly. |
| Time dimension | `agg_time_dimension` is set; at least one column carries `semantic_type: time`. |
| Metric types | All metric types (`simple`, `ratio`, `cumulative`, `derived`) are semantically correct for the SQL aggregation being modeled. |
| No `type_params` | Latest MetricFlow spec: `type_params` must be absent; params are top-level fields. |
| Aggregation alignment | `agg` value matches the SQL aggregation function actually used (e.g. `sum` for `SUM(...)`, `count_distinct` for `COUNT(DISTINCT ...)`). |

---

## Step 4 — Adversarial skeptic pass (dbt failure catalog)

Challenge each generated YAML against the failure modes below. Each row maps a known dbt/MetricFlow failure to a concrete check the judge must perform.

| Failure mode | Concrete check |
|---|---|
| Missing primary time dimension | `agg_time_dimension` is set AND the referenced column has `semantic_type: time`. Fail if either is absent. |
| No domain prefix | Model name starts with a recognizable domain token (e.g. `qcommerce_`). Flag if absent. |
| Missing owner | Every metric has `config.meta.owner` set to a non-empty string. Fail if any metric omits it. |
| Duplicate formula | Normalize each metric's formula (strip whitespace, lowercase); fail if any two metrics share the same normalized formula. |
| Undocumented metric | Every metric carries a non-empty `description`. Fail if any metric omits it or uses a placeholder string. |
| Wrong agg on ratio | Ratio metric `numerator` and `denominator` must both reference valid simple metrics — not raw columns. Fail if either references a raw column expression directly. |
| Hallucinated column | Cross-check all column references against the dbt manifest. Any name absent from the manifest is a hallucination; fail immediately. |
| Missing/incorrect `expr` | When a semantic-model entity/dimension/measure identifier differs from the source column name, an `expr` field must be present and reference an actual manifest column. Fail if `expr` is absent where needed or references a non-existent column. |
| YAML fails dbt parse | Re-run `mf validate-configs` after any YAML mutation made during review. A valid YAML must pass on every run. |

Each failing row must appear in `adversarial_failures` with `mode`, `detail`, and `line` (YAML line number if applicable).

---

## Step 5 — Verdict

Record the following JSON after completing Steps 1–4:

```json
{
  "mf_validate_pass": true,
  "trust_band": "A",
  "structural_checks": {
    "column_fidelity": true,
    "entity_roles": true,
    "time_dimension": true,
    "metric_types": true,
    "no_type_params": true,
    "aggregation": true
  },
  "adversarial_failures": [],
  "overall": "PASS"
}
```

**Overall PASS requires all four conditions:**

1. `mf_validate_pass` is `true`.
2. `trust_band` is `A` or `B`.
3. `adversarial_failures` is empty.
4. All `structural_checks` values are `true`.

Any condition failing sets `overall` to `FAIL`. Partial credit is not recorded — the verdict is binary.

---

## Step 6 — Document-quality judgment payload

After recording the verdict, emit a second JSON block consumed by `trust.judgment.apply_judgment`
at skill runtime (Task 3.1f).  This is the **only** payload shape `apply_judgment` reads;
any other keys are silently ignored by the guardrail.

```json
{
  "documents": {
    "<doc_type>": {
      "quality": 0,
      "issues": [
        {
          "severity": "warning",
          "dimension": "<dimension_name>",
          "rule": "<rule_id>",
          "message": "<human-readable finding>",
          "location": "<yaml_file_or_field_reference>"
        }
      ]
    }
  }
}
```

**Field rules:**

| Field | Values | Notes |
|---|---|---|
| `<doc_type>` | `"semantic_model"`, `"metrics"`, `"dbt_docs"`, `"few_shot"` | Must match an existing DocumentReport key; unknown keys are ignored. |
| `quality` | integer 0–100 | Advisory LLM quality score. Separate from the deterministic `trust_score` — never blended. |
| `severity` | `"critical"`, `"warning"`, `"info"` | Use `"warning"` or `"info"` for advisory findings; `"critical"` only for clear authoring errors. |
| `dimension` | e.g. `"data_context"`, `"completeness"`, `"clarity"` | Free-form but should match the rubric dimension being evaluated. |
| `rule` | snake_case identifier | e.g. `"description_business_meaning"`, `"metric_description_tautology"`. |
| `location` | file path or field ref | e.g. `"metrics[0].description"` or `"models/orders.yml"`. |

All issues in this payload are tagged `provenance="llm_judge"` by `apply_judgment` and kept
separate from `provenance="deterministic"` issues.  The guardrail guarantees that this payload
can never change gates, `trust_score`, `band`, `context`, `quality`, or any deterministic issue.

---

## Reference

- Deterministic half: `python -m eval.harness`
- dbt failure catalog: `skills/references/validation/structural.md`
- Trust rubric: spec §7 + `skills/references/validation/scoring-formula.md`
- Fixture baseline: `tests/fixtures/qcommerce_latest`
