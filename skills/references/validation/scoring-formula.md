# Trust Score Formula & Grading

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

## Trust Score Formula

```
trust_score = (data_context × 0.60) + (data_quality × 0.40)
```

| Dimension | Weight | Tag | What it measures |
|-----------|--------|-----|------------------|
| Data Context | 60% | `[C]` | Descriptions, labels, interpretation, calculation logic — human-authored content that makes docs useful |
| Data Quality | 40% | `[Q]` | Relationships, tests, governance dates, version tracking — data integrity and auditability |

## Per-Document Score

```
document_score = (checks_passed / checks_total) × 100
```

Where `checks_passed` and `checks_total` count ALL scoreable checks (`[C]` + `[Q]`) for that document.

## Trust Dimension Score

```
dimension_score = (checks_passed_in_dimension / checks_total_in_dimension) × 100
```

Aggregated across ALL documents being validated.

## Grade Thresholds

| Grade | Score Range | Meaning |
|-------|-------------|---------|
| A | 90–100 | Production-ready. Rich descriptions, complete relationships, governance current. |
| B | 75–89 | Good quality. A few thin descriptions or missing interpretation fields. |
| C | 60–74 | Functional but needs content work — descriptions, labels, or governance gaps. |
| D | 45–59 | Significant content gaps. Not recommended for production use. |
| F | 0–44 | Major content issues. Requires rework. |

## Important Note

A document can have grade A on trust score but still fail CI gates (e.g., rich descriptions but blank ownership, or a duplicate metric). All gates must pass for production readiness. The trust score and CI gates are independent — both must be satisfactory.
