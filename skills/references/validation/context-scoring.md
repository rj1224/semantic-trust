# Data Context Scoring Rules — `[C]` Trust Score

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Measures whether a human has provided meaningful context: model descriptions, entity descriptions, measure descriptions, dimension labels and descriptions, metric interpretation, calculation logic documentation.

**Weight:** 60% of trust score

This is the dominant dimension. Structure can be automated; ownership can be mandated; but context requires human judgment and domain knowledge. Highest weight because this is the primary quality signal.

## Trust Score Formula (context component)

```
data_context_score = (C_checks_passed / C_checks_total) × 100
weighted_context = data_context_score × 0.60
```

## Check Counts by Document Type

### dbt docs — 7 `[C]` checks
1. Model-level `description` is meaningful (>10 words, explains business purpose)
2. Grain statement documented (what does one row represent?)
3. Source lineage documented (where does data come from?)
4. Table path documented (database.schema.table)
5. Column descriptions present and meaningful (>5 words each)
6. Column descriptions cover >80% of columns
7. Business logic explained for derived/calculated columns

### Semantic Model — 4 `[C]` checks
1. Model-level `description` is meaningful (>10 words)
2. Entity descriptions present and meaningful
3. Measure descriptions present and meaningful (explain business meaning, not just "sum of X")
4. Dimension descriptions present with labels

### Metrics — 7 `[C]` checks
1. `description` is meaningful (>10 words, explains what the metric measures)
2. `label` is human-readable (business-friendly name)
3. `calculation_logic` value is non-blank and explains the formula in plain language
4. `source_semantic_model` value is non-blank and references a valid SM
5. `interpretation` value is non-blank (how to read the metric, what high/low means)
6. `refresh_cadence` value is non-blank
7. `data_latency` value is non-blank

### Few-Shot — 8 `[C]` checks
1. At least 3 examples provided
2. Questions use business language (not SQL jargon)
3. Questions don't contain SQL keywords in the question text
4. Each example has a meaningful `description` explaining what it demonstrates
5. Questions cover variety of query patterns (aggregation, filtering, joining)
6. At least one question asks "why" or "how" (interpretation, not just "what")
7. Questions match the model's business domain
8. Questions progress in complexity (basic → intermediate → hard)

## Severity

- Missing description → `warning`
- Thin description (under 10 words) → `warning`
- Blank meta context value (calculation_logic, interpretation) → `warning`
