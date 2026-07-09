# Metrics — Template & Example

<!--
Grammar authority: vendor/dbt-agent-skills/latest-spec.md (latest, dbt 1.12+) and
vendor/dbt-agent-skills/legacy-spec.md (dbt 1.6–1.11).
This template shows ONLY DataStack's additive config.meta layer on top of that grammar.
-->

Target: dbt-core 1.12+ | Latest MetricFlow spec

**Latest spec: simple metrics live inside the model.**
Simple metrics (all measures from one semantic model) are defined under `metrics:` at model level in the same file as the model — with `agg` and `expr` inline. There is no `type_params:` wrapper and no `measures:` block in the latest spec.

Cross-model advanced metrics (derived/ratio/conversion/cumulative combining multiple models) go in a top-level `metrics:` file. These use `input_metrics:` (derived), `numerator:`/`denominator:` (ratio), `input_metric:` (cumulative), or `entity:`+`base_metric:`+`conversion_metric:` (conversion) — no `type_params:` wrapper.

## Latest-Spec Simple Metric (nested under model)

Nested under `models[*].metrics` in the semantic model file:

```yaml
- name: <metric_name>                                   ## Required — unique, snake_case
  description: "<what this metric measures>"            ## Required
  type: simple                                          ## Required
  label: "<Display Name for BI Tools>"                  ## Required
  agg: <sum|count|count_distinct|avg|min|max>           ## Required — no type_params wrapper
  expr: <column_name_or_sql_expression>                 ## Required — column to aggregate
  filter: |                                             ## Optional
    {{ Dimension('<entity>__<dimension>') }} = '<value>'
  config:                                               ## Required
    meta:
      business_domain: ""                               ## Required
      business_owner:                                   ## Required — non-empty list of valid team emails
        - ""
      technical_owner:                                  ## Required — non-empty list of valid team emails
        - ""
      freshness:
        refresh_cadence: ""                             ## Required — hourly|daily|weekly
        data_latency: ""                                ## Required — expected delay (e.g., "T+1", "daily")
      technical_details:
        calculation_logic: ""                           ## Required — formula or SQL
        source_semantic_model: ""                       ## Required — semantic model name
        interpretation: ""                              ## Optional — "higher/lower is better"
        benchmark_target: ""                            ## Optional — target value
      governance:
        approved_by: ""                                 ## Required — approver email
        approval_date: ""                               ## Required — YYYY-MM-DD
        last_modified: ""                               ## Required — YYYY-MM-DD
        version: ""                                     ## Required — semver (e.g., "1.0")
```

## Cross-Model Metrics (top-level, separate file — Latest Spec)

In a standalone `metrics:` YAML file. No `type_params:` wrapper in the latest spec.

```yaml
metrics:
  ## Ratio Metric — numerator / denominator (references metric names, not measure names)
  - name: <metric_name>                                 ## Required
    description: "<what this ratio measures>"           ## Required
    type: ratio                                         ## Required
    label: "<Display Name>"                             ## Required
    numerator: <metric_name>                            ## Required — metric name string or dict
    denominator: <metric_name>                          ## Required — metric name string or dict
    config:                                             ## Required — same structure as simple metric
      meta: ...

  ## Ratio Metric with filter/alias (dict form)
  - name: <metric_name>
    type: ratio
    label: "<Display Name>"
    numerator:
      name: <metric_name>
      filter: |
        {{ Dimension('<entity>__<dim>') }} = '<value>'
      alias: <alias>
    denominator:
      name: <metric_name>
    config:
      meta: ...

  ## Derived Metric — expression combining other metrics (within same model, under model metrics:)
  ## For cross-model derived, also goes at top-level metrics:
  - name: <metric_name>                                 ## Required
    description: "<what this derived metric measures>"  ## Required
    type: derived                                       ## Required
    label: "<Display Name>"                             ## Required
    expr: "<math_expression_using_aliases>"             ## Required
    input_metrics:                                      ## Required — NOT type_params.metrics
      - name: <metric_name>
        alias: <alias_for_expr>                         ## Optional — defaults to metric name
        offset_window: <N> <day|week|month|year>        ## Optional — time offset
        filter: |                                       ## Optional
          {{ Dimension('<entity>__<dim>') }} = '<value>'
      - name: <metric_name>
        alias: <alias_for_expr>
    config:                                             ## Required — same structure as simple metric
      meta: ...

  ## Conversion Metric — funnel-style step-through rate
  - name: <metric_name>                                 ## Required
    description: "<what this conversion measures>"      ## Required
    type: conversion                                    ## Required
    label: "<Display Name>"                             ## Required
    entity: <entity_name>                               ## Required
    calculation: conversion_rate                        ## Optional — conversion_rate (default) or conversions
    base_metric:
      name: <base_metric_name>                          ## Required
    conversion_metric: <conversion_metric_name>         ## Required
    window: <N> <days|weeks>                            ## Optional
    config:                                             ## Required — same structure as simple metric
      meta: ...
```

## Cumulative Metric (top-level, latest spec)

```yaml
metrics:
  - name: <metric_name>__cumulative
    description: "Rolling <N>-<unit> cumulative total of <metric_name>."
    type: cumulative
    label: "<Human Readable Label>"
    input_metric: <source_metric_name>                  ## Required — metric name (not measure name)
    window: <1 month>                                   ## Optional — omit for all-time
    ## OR: grain_to_date: month                         ## Optional — cannot use with window
    config:
      meta:
        business_owner:
          - ""
        business_domain: ""
        technical_owner:
          - ""
        freshness:
          refresh_cadence: ""
          data_latency: ""
        technical_details:
          calculation_logic: ""
          source_semantic_model: ""
          interpretation: ""
        governance:
          approved_by: ""
          approval_date: ""
          last_modified: ""
          version: ""
        tags:
          - ""
```

## Validation rules

Validation rules live in `skills/references/validation/`. Load on demand.

| Gate | File | Coverage |
|------|------|----------|
| Structural `[S]` | `validation/structural.md` → "Metrics" | 23 checks — key presence, type enum, derived uses `input_metrics:` not `type_params.metrics:` |
| Ownership `[O]` | `validation/ownership.md` → "Metrics" | 4 checks — business_owner, technical_owner, business_domain, approved_by |
| Uniqueness `[U]` | `validation/uniqueness.md` | 3 checks — name, formula, definition equivalence |
| Data Context `[C]` | `validation/context-scoring.md` → "Metrics" | 7 checks — description, label, calculation_logic, source_semantic_model, interpretation, refresh_cadence, data_latency |
| Data Quality `[Q]` | `validation/quality-scoring.md` → "Metrics" | 6 checks — governance dates, version, derived aliases |

## Example

Domain: quick-commerce delivery operations (illustrative).

Nested simple metrics in the semantic model file:

```yaml
models:
  - name: fact_delivery_orders
    semantic_model:
      enabled: true

    agg_time_dimension: order_created_date

    config:
      meta:
        business_owner:
          - ""
        business_domain: "Delivery Operations"
        technical_owner:
          - ""
        refresh_cadence: "daily"
        tags:
          - "Delivery"

    columns:
      - name: order_id
        description: "Primary identifier for each delivery order"
        entity:
          type: primary
          name: order

      - name: order_created_date
        description: "Date the order was placed"
        granularity: day
        dimension:
          type: time

      - name: order_status
        description: "Current order status"
        dimension:
          type: categorical

    metrics:
      - name: total_orders
        description: "Total delivery orders placed"
        type: simple
        label: "Total Orders"
        agg: count
        expr: order_id
        config:
          meta:
            business_domain: "Delivery Operations"
            business_owner:
              - ""
            technical_owner:
              - ""
            freshness:
              refresh_cadence: "daily"
              data_latency: "T+1"
            technical_details:
              calculation_logic: "count(order_id)"
              source_semantic_model: "fact_delivery_orders"
              interpretation: "Higher is better"
            governance:
              approved_by: ""
              approval_date: ""
              last_modified: ""
              version: "1.0"

      - name: cancelled_orders
        description: "Total orders cancelled before delivery"
        type: simple
        label: "Cancelled Orders"
        agg: count
        expr: order_id
        filter: |
          {{ Dimension('order__order_status') }} = 'cancelled'
        config:
          meta:
            business_domain: "Delivery Operations"
            business_owner:
              - ""
            technical_owner:
              - ""
            freshness:
              refresh_cadence: "daily"
              data_latency: "T+1"
            technical_details:
              calculation_logic: "count(order_id) where order_status = 'cancelled'"
              source_semantic_model: "fact_delivery_orders"
              interpretation: "Lower is better — fewer cancellations means higher reliability"
            governance:
              approved_by: ""
              approval_date: ""
              last_modified: ""
              version: "1.0"
```
