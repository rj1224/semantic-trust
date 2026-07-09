# Metric Design Frameworks

Decision trees for metric types, entity identification, and semantic model routing. Use these frameworks when determining which metric type to create, defining entities for a semantic model, or deciding which semantic model a metric should belong to.

Target: dbt-core 1.12+ | Source: dbt best practices 2025

Related: `references/standards/model-design.md` covers the reporting layer (fact/dim/mart classification, interface contracts). This file covers the semantic layer.

## 1. Metric Type Decision Tree

Use this when determining which metric type to create.

```
START: I need to create a metric
  |
  ├─→ Direct aggregation of a SINGLE measure? (SUM, COUNT, AVG)
  |   YES → SIMPLE METRIC
  |   |   Examples: total_revenue = SUM(order_amount), order_count = COUNT(order_id)
  |   |   agg: <agg_fn>, expr: <column>   (no type_params: wrapper)
  |
  ├─→ One metric DIVIDED by another metric?
  |   YES → RATIO METRIC
  |   |   Examples: revenue_per_customer, items_per_order, margin_pct
  |   |   numerator: <metric_name>   ← direct top-level key (no type_params: wrapper)
  |   |   denominator: <metric_name> ← direct top-level key (no type_params: wrapper)
  |
  ├─→ Tracks PROGRESSION through stages/funnel?
  |   YES → CONVERSION METRIC
  |   |   Examples: lead_to_customer_rate, cart_to_purchase_rate
  |
  ├─→ Requires RUNNING TOTAL over any dimension?
  |   YES → CUMULATIVE METRIC
  |   |   Examples: cumulative_revenue, year_to_date_signups, running_total_by_region
  |   |   input_metric: <metric_name>   ← direct top-level key (dbt 1.12+ spec; NOT under type_params:)
  |   |   window: 90d                  ← direct top-level key (NOT cumulative_type_params)
  |   |   Note: Running totals are not limited to time dimensions — they can
  |   |   accumulate over any ordered dimension (e.g., by region, by category).
  |
  └─→ COMBINES multiple metrics with operations?
      YES → DERIVED METRIC
      |   Examples: net_revenue = gross - returns - discounts, CLV
      |   expr: "a - b"              ← direct top-level key (no type_params: wrapper)
      |   input_metrics: [{ name: ..., alias: a }]  ← direct top-level key
      |   NOTE: Use `input_metrics:` at metric level. `type_params` and `metrics:`-under-`type_params` are legacy (pre-1.12) forms.
```

## 2. Entity Identification Decision Tree

Use when defining entities for a semantic model.

```
START: What entities do I need?
  |
  ├─→ What is the PRIMARY business object this model is about?
  |   → PRIMARY ENTITY (type: primary)
  |   Examples: order, customer, ticket, driver
  |   Must have unique, non-null values in the expr column
  |
  ├─→ Are there OTHER business objects directly related via FK?
  |   → FOREIGN ENTITIES (type: foreign)
  |   For each: does another semantic model already define this entity?
  |     YES → reference it (config.meta.relationship with model, type, expr)
  |     NO → define as foreign entity, plan separate SM later
  |
  └─→ Are there line-item or child objects?
      → Decide based on: do users need to analyze at this grain separately?
      YES to both → separate entity
      NO → keep as measures/dimensions in primary entity
```

## 3. Which Semantic Model? Decision Tree

Use when a metric needs measures and you have to decide where it lives in the file structure.

```
START: Which semantic model should this metric use, and where does the metric live?
  |
  ├─→ ONLY uses measures from ONE semantic model?
  |   YES → use that single SM. Metric goes in the SAME file as the SM,
  |         regardless of metric type (simple, ratio, derived, cumulative).
  |         Complexity is NOT the criterion.
  |
  ├─→ Combines measures from MULTIPLE semantic models? (cross-SM)
  |   → Is there a relationship defined between them?
  |     YES → create the metric referencing both SMs; place in a SEPARATE
  |           metrics-only file (`<metric_name>.yml`) under the same
  |           domain folder. The metric is structurally joint between
  |           the SMs, so it shouldn't live "in" either one.
  |     NO  → define the relationship first, OR reconsider model boundaries
  |           (often a sign that the metric is poorly scoped).
  |
  └─→ Top-level business metric across multiple domains?
      → Same answer as the cross-SM case above: separate metrics-only file
        under the relevant domain folder, referencing the multiple SMs.
```

**Canonical rule (v0.5.0+):** the criterion for "same file vs separate file" is **cross-SM dependency**, not metric complexity. A complex single-SM metric (e.g., a derived metric combining three measures from one SM) still belongs in the SM's file. A simple cross-SM metric (e.g., a ratio of one measure from SM-A divided by one measure from SM-B) goes in a separate file.

## 4. Semantic Model Readiness Criteria

Before creating a semantic model, verify the source reporting model is ready:

| Requirement | Why It Matters | Self-Check Question |
|-------------|----------------|---------------------|
| Clear Grain | Need to know what one row represents to build entities | Can I explain in one sentence what a row represents? |
| Business-Friendly Names | Reduces translation effort for semantic layer | Would a business user understand this column name? |
| Documented Measures | Need to know additivity for correct aggregation | Have I identified which measures are additive, semi-additive, non-additive? |
| Explicit Relationships | Enables joining across semantic models | Are all FK relationships documented with cardinality? |
| Stable Schema | Prevents breaking downstream metrics | Is this schema finalized and tested? |
| Quality Guarantees | Ensures trustworthy data | Are all data_tests passing? |
| Interface Contract | All prerequisites checked | Does the model pass the Interface Contract Checklist in `model-design.md`? |
