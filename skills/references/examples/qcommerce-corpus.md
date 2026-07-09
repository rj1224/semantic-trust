# Quick-Commerce Few-Shot Corpus

Target: dbt-core 1.12+ | Latest MetricFlow spec

Generic worked examples for the quick-commerce domain (orders, customers, delivery partners,
dark stores; GMV, AOV, delivery time). No proprietary or company-specific data.

Each example follows the full pipeline:
1. Source SQL (abbreviated)
2. dbt model stub
3. Semantic model YAML (latest spec — nested under `models:`)
4. Metrics YAML (simple inline; ratio/cumulative in top-level `metrics:`)
5. Expected compile gate result (`dbt parse` — universal; `mf validate-configs` — legacy-only, dbt ≤ 1.11)
6. Expected trust band from `score_semantic_model`

---

## Example 1 — SIMPLE metric: Total GMV

**Business question:** What is our total gross merchandise value (GMV) across all completed orders?

### Source SQL (abbreviated)

```sql
-- mart.fact_orders
-- grain: one row per order
SELECT
    order_id,
    customer_id,
    dark_store_id,
    order_placed_at::date          AS order_placed_date,
    order_status,                   -- 'completed' | 'cancelled' | 'failed'
    city,
    gmv_amount                      -- gross value of the order in local currency
FROM warehouse.orders
WHERE order_placed_at >= '2023-01-01'
```

### dbt model stub (`models/mart/fact_orders.sql`)

```sql
SELECT
    order_id,
    customer_id,
    dark_store_id,
    order_placed_at::date          AS order_placed_date,
    order_status,
    city,
    gmv_amount
FROM {{ ref('stg_orders') }}
```

### Semantic model + simple metric YAML

```yaml
# models/mart/fact_orders.yml
models:
  - name: fact_orders
    description: >
      Core order fact table for the quick-commerce platform.
      Source: warehouse, schema: mart.
      Grain: one row = one order.
      Refresh: daily.
    config:
      meta:
        business_owner:
          - "analytics@example.com"
        business_domain: "Commerce"
        technical_owner:
          - "data-eng@example.com"
        refresh_cadence: "daily"
        tags:
          - "Commerce"
          - "Orders"
    semantic_model:
      enabled: true
    agg_time_dimension: order_placed_date
    columns:
      - name: order_id
        entity:
          type: primary
          name: order
        description: "Unique identifier for each order"

      - name: customer_id
        entity:
          type: foreign
          name: customer
        description: "Customer who placed the order"

      - name: dark_store_id
        entity:
          type: foreign
          name: dark_store
        description: "Dark store that fulfilled the order"

      - name: order_placed_date
        granularity: day
        dimension:
          type: time
        description: "Calendar date the order was placed"

      - name: order_status
        dimension:
          type: categorical
        description: "Final status of the order — completed, cancelled, failed"

      - name: city
        dimension:
          type: categorical
        description: "City where the order was placed"

      - name: gmv_amount
        description: "Gross merchandise value of the order in local currency"

    metrics:
      - name: qcommerce_total_gmv
        description: "Total gross merchandise value across all orders"
        type: simple
        label: "Total GMV"
        agg: sum
        expr: gmv_amount
        config:
          meta:
            business_domain: "Commerce"
            business_owner:
              - "analytics@example.com"
            technical_owner:
              - "data-eng@example.com"
            freshness:
              refresh_cadence: "daily"
              data_latency: "T+1"
            technical_details:
              calculation_logic: "sum(gmv_amount)"
              source_semantic_model: "orders"
              interpretation: "Higher is better — total revenue generated from orders"
            governance:
              approved_by: "analytics@example.com"
              approval_date: "2026-01-15"
              last_modified: "2026-06-30"
              version: "1.0"

      - name: qcommerce_total_orders
        description: "Total number of orders placed"
        type: simple
        label: "Total Orders"
        agg: count
        expr: order_id
        config:
          meta:
            business_domain: "Commerce"
            business_owner:
              - "analytics@example.com"
            technical_owner:
              - "data-eng@example.com"
            freshness:
              refresh_cadence: "daily"
              data_latency: "T+1"
            technical_details:
              calculation_logic: "count(order_id)"
              source_semantic_model: "orders"
              interpretation: "Higher is better — volume of orders"
            governance:
              approved_by: "analytics@example.com"
              approval_date: "2026-01-15"
              last_modified: "2026-06-30"
              version: "1.0"
```

### Expected compile gate result

```
dbt parse
✓  Semantic model 'orders' — PASS
✓  Metric 'qcommerce_total_gmv' (simple) — PASS
✓  Metric 'qcommerce_total_orders' (simple) — PASS
```

> Note: for legacy-spec projects (dbt ≤ 1.11) you may additionally run `mf validate-configs` as an extra advisory gate. On dbt ≥ 1.12 (latest spec) `mf validate-configs` is not compatible — `dbt parse` is the sole compile gate.

### Expected trust band

`score_semantic_model` output:
- Structural [S]: PASS — `models:` top-level key, entities with `expr:`, time column with `granularity: day`, `gmv_amount` declared in `columns:`, simple metrics inline with `agg`/`expr`, no `type_params`, no `measures:` block
- Ownership [O]: PASS — `business_owner`, `technical_owner`, `business_domain`, `refresh_cadence`, `tags` all populated
- Joinability [J]: PASS — primary entity `order_id` present; FK entities declared
- Data Context [C]: PASS — descriptions at model, entity, column, and metric level
- Data Quality [Q]: PASS — `agg_time_dimension` set, time column present with `granularity`

**Trust band: GREEN**

---

## Example 2 — RATIO metric: Average Order Value (AOV)

**Business question:** What is the average value per completed order (AOV = GMV / orders)?

AOV references two metrics from the same semantic model (`orders`). Because it is a ratio
metric it goes in a separate top-level `metrics:` file rather than inline under the model.

### Metrics YAML (separate file)

```yaml
# models/mart/metrics/qcommerce_aov.yml
metrics:
  - name: qcommerce_aov
    description: >
      Average order value. Measures revenue efficiency per transaction.
      Calculated as total GMV divided by total order count.
      Higher AOV means customers are spending more per order.
    type: ratio
    label: "Average Order Value (AOV)"
    numerator:
      name: qcommerce_total_gmv
    denominator:
      name: qcommerce_total_orders
    config:
      meta:
        business_domain: "Commerce"
        business_owner:
          - "analytics@example.com"
        technical_owner:
          - "data-eng@example.com"
        freshness:
          refresh_cadence: "daily"
          data_latency: "T+1"
        technical_details:
          calculation_logic: "sum(gmv_amount) / count(order_id)"
          source_semantic_model: "orders"
          interpretation: "Higher is generally better — indicates higher spend per transaction"
        governance:
          approved_by: "analytics@example.com"
          approval_date: "2026-01-15"
          last_modified: "2026-06-30"
          version: "1.0"
```

### Key spec points

- `type: ratio` uses direct `numerator:` and `denominator:` keys at the metric level (no `type_params:` wrapper).
- Both fields reference **metric names** (not measure/column names).
- No `agg:` or `expr:` at the ratio level — those live on the referenced simple metrics.
- Ratio metrics are always in a top-level `metrics:` file, never inline under a model.

### Expected compile gate result

```
dbt parse
✓  Metric 'qcommerce_aov' (ratio) — PASS
     numerator  → 'qcommerce_total_gmv' resolved
     denominator → 'qcommerce_total_orders' resolved
```

> Note: for legacy-spec projects (dbt ≤ 1.11) you may additionally run `mf validate-configs` as an extra advisory gate. On dbt ≥ 1.12 `dbt parse` is the sole compile gate.

### Expected trust band

`score_semantic_model` output for the ratio metric file:
- Structural [S]: PASS — `metrics:` top-level key, `type: ratio`, direct `numerator:`/`denominator:` keys with `name`; no `type_params:` wrapper, no inline `agg`/`expr`
- Ownership [O]: PASS — all required ownership fields populated
- Data Context [C]: PASS — description, label, calculation_logic, source_semantic_model, interpretation all present
- Data Quality [Q]: PASS — governance dates and version set

**Trust band: GREEN**

---

## Example 3 — CUMULATIVE metric: Rolling 7-Day GMV

**Business question:** What is our rolling 7-day GMV — the sum of GMV over the trailing 7 days?

A cumulative metric wraps an existing metric and applies a window. It lives in a top-level
`metrics:` file and uses `input_metric` (referencing the base metric name) plus `window`
for the window definition (dbt-core 1.12+ latest spec).

### Metrics YAML (separate file)

```yaml
# models/mart/metrics/qcommerce_rolling_7d_gmv.yml
metrics:
  - name: qcommerce_rolling_7d_gmv
    description: >
      Rolling 7-day gross merchandise value. Smooths daily volatility by
      summing GMV over the trailing 7-day window. Useful for spotting
      week-on-week growth trends without single-day noise.
    type: cumulative
    label: "Rolling 7-Day GMV"
    input_metric: qcommerce_total_gmv
    window: 7d
    config:
      meta:
        business_domain: "Commerce"
        business_owner:
          - "analytics@example.com"
        technical_owner:
          - "data-eng@example.com"
        freshness:
          refresh_cadence: "daily"
          data_latency: "T+1"
        technical_details:
          calculation_logic: "sum(gmv_amount) over trailing 7 days"
          source_semantic_model: "orders"
          interpretation: "Upward trend over time is better — indicates sustained revenue growth"
        governance:
          approved_by: "analytics@example.com"
          approval_date: "2026-01-15"
          last_modified: "2026-06-30"
          version: "1.0"
```

### Key spec points

- `type: cumulative` in dbt-core 1.12+ uses `input_metric: <metric_name>` — references an existing
  metric (not a raw measure name from a semantic model).
- `window` is a direct top-level key on the metric (not nested under `type_params.cumulative_type_params`).
- Window format is `Nd` / `Nw` / `Nm` (e.g., `7d`, `1m`). The old `N days` string form is legacy.
- Do NOT use `type_params.measure` or `cumulative_type_params.window` — those are the pre-1.12 forms.
- The base metric (`qcommerce_total_gmv`) must already be defined (Example 1).
- No `agg:` or `expr:` at the cumulative level.

### Expected compile gate result

```
dbt parse
✓  Metric 'qcommerce_rolling_7d_gmv' (cumulative) — PASS
     input_metric → 'qcommerce_total_gmv' resolved
     window       → 7d
```

> Note: for legacy-spec projects (dbt ≤ 1.11) you may additionally run `mf validate-configs` as an extra advisory gate. On dbt ≥ 1.12 `dbt parse` is the sole compile gate.

### Expected trust band

`score_semantic_model` output for the cumulative metric file:
- Structural [S]: PASS — `type: cumulative`, `input_metric`, `window` present as direct keys; deprecated `type_params.measure` and `cumulative_type_params` absent
- Ownership [O]: PASS — all required ownership fields populated
- Data Context [C]: PASS — description, label, calculation_logic, source_semantic_model, interpretation all present
- Data Quality [Q]: PASS — governance dates and version set

**Trust band: GREEN**

---

## Spec compliance summary

| Check | Status |
|---|---|
| dbt-core version label | 1.12+ (all examples) |
| Top-level key | `models:` for semantic model + inline metrics; `metrics:` for ratio/cumulative |
| Simple metric shape | `agg` + `expr` inline, no `type_params`, no `measures:` block |
| Ratio metric shape | direct `numerator:` / `denominator:` keys (no `type_params:` wrapper) |
| Entities/dimensions | per-column nested `entity:` / `dimension:` blocks; no flat `entities:` list; no `semantic_type` key |
| Cumulative metric shape | `input_metric: <metric_name>` + `window: Nd` as direct keys (1.12+ spec) |
| Column declarations | All `expr:` column refs declared in `columns:` block (incl. `gmv_amount`) |
| Time dimension | `granularity: day` at column level (NOT `type_params.time_granularity`) |
| Deprecated forms | None — `type_params.measure`, `cumulative_type_params`, `type_params.window`, `type_params.time_granularity`, standalone `measures:` all absent |
