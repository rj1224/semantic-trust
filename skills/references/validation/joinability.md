# Joinability Validation Rules — `[J]` CI Gate

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

Verifies that semantic models in the project are correctly wired for joins: every entity referenced in metrics resolves to a declared entity in a semantic model, and entities intended to join across models share matching names and types.

Severity: **warning** — findings are reported and included in the CI gate result, but do not hard-block merge by default. Repeated warnings on the same entity signal a structural gap that should be resolved before the metric layer is considered production-ready.

## Rules

### `joinability_orphan`

**What it checks:** Every entity referenced by a metric's `entity_links` or used as a join key must be declared in at least one semantic model in the project. An entity referenced in a metric that has no matching declaration in any semantic model is an orphan.

**How it runs:** Collect all entity names declared across the project's semantic-model YAML files. For each metric, extract entity references. Flag any entity reference that does not appear in the collected set.

**Failure message format:**
```
[J] joinability_orphan: entity '<entity_name>' referenced in metric '<metric_name>' is not declared in any semantic model
```

**Remediation:** Add an `entities:` block to the appropriate semantic model declaring the entity with its correct `type` (`primary`, `foreign`, or `unique`). The entity name and type must be consistent with how it is used in the metric.

---

### `joinability_parity`

**What it checks:** When the same entity name appears in more than one semantic model (indicating those models are intended to join on that entity), the entity's `type` must match across all models. A mismatch in entity type (e.g., `primary` in one model vs `foreign` in another where both should be `foreign`) will cause silent join failures or unexpected fan-out at query time.

**How it runs:** Group all entity declarations by name across the project's semantic-model YAML files. For any entity name that appears in two or more models, compare the `type` field. Flag the name if any two models declare different types.

**Failure message format:**
```
[J] joinability_parity: entity '<entity_name>' has conflicting types across models: <model_a> declares '<type_a>', <model_b> declares '<type_b>'
```

**Remediation:** Decide the correct entity type for the join (typically one model holds `primary`, the others hold `foreign`). Update all semantic-model YAML files to use consistent names and types for shared join entities.

---

## Check Counts

### Semantic Model — 2 `[J]` checks
1. `joinability_orphan` — orphan entity detection (entities in metrics with no SM declaration)
2. `joinability_parity` — cross-model entity name/type consistency

### Metrics / dbt docs / Few-Shot — 0 `[J]` checks
Joinability is a semantic-model concern; metric entity references are validated via `joinability_orphan`.

## Notes for CI implementation

- Both checks are fully deterministic and operate on the project's YAML files on disk — no external service dependency
- Checks run after `dbt parse` passes (universal compile gate); orphan and parity checks assume the YAML is structurally valid
- For legacy-spec projects (dbt ≤ 1.11), `mf validate-configs` may also run as an advisory extra gate; it does not apply to latest-spec projects (dbt ≥ 1.12)
- Warnings accumulate across all semantic models in the project; the gate status is `fail` if any warning is raised
