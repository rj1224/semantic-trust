# Semantic Model — Template, Checklist & Example

<!--
Grammar authority: ${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md (latest, dbt 1.12+) and
${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/legacy-spec.md (dbt 1.6–1.11).
This template shows ONLY DataStack's additive config.meta layer (owner, maturity) on top of
that grammar. For the full grammar reference, read the vendored guides directly.
-->

Target: dbt-core 1.12+ | Latest MetricFlow spec (models: nested)

**Latest spec shape:**
- Top-level key is `models:` with a nested `semantic_model:` block per entry (`enabled: true`).
- `agg_time_dimension:` is at the model level (NOT inside `semantic_model:`).
- Entities and dimensions are expressed as `entity:` / `dimension:` blocks nested under columns.
- `granularity:` goes at the column level for time dimensions (NOT inside the `dimension:` block).
- Simple metrics are defined under `metrics:` at model level with `agg` + `expr` + `label` inline (NO `measures:`, NO `type_params:`).
- The `semantic_type` field does not exist in this spec — use `entity:` or `dimension:` blocks instead.

**Metric file placement:**
Simple metrics (all measures from one model) live under the model's `metrics:` key in the same file. Cross-model metrics (derived/ratio/conversion combining multiple models) go in a separate top-level `metrics:` file under the same domain folder.

**Note on tags:** `tags` goes inside `config.meta` as business domain metadata — different from dbt docs where `tags` goes at `config` level.

## Template (Latest Spec — dbt 1.12+)

<!-- Note: descriptions at model, entity, metric, and dimension level are REQUIRED by the [C] Data Context gate. -->

```yaml
models:
  - name: <dbt_model_name>                              ## Required — must match the dbt model filename (without .sql)
    description: "<business description of the model>"  ## Required — checked by [C] Data Context gate
    semantic_model:
      enabled: true                                     ## Required

    agg_time_dimension: <default_time_dimension_name>   ## Required — must match a column with granularity: below

    config:                                             ## Required
      meta:                                             ## Required
        business_owner:                                 ## Required — non-empty list of valid team emails
          - ""                                          ## add one "- " line per business owner
        business_domain: ""                             ## Required — e.g., "Operations", "Finance"
        technical_owner:                                ## Required — non-empty list of valid team emails
          - ""                                          ## add one "- " line per technical owner
        refresh_cadence: ""                             ## Required — hourly|daily|weekly
        tags:                                           ## Required — at least one domain/workstream tag
          - ""                                          ## add one "- " line per tag

    columns:
      ## Primary Entity column
      - name: <pk_column_name>                          ## Required
        description: "<role of the entity>"             ## Required
        entity:
          type: primary                                 ## primary|foreign|unique|natural
          name: <entity_name>                           ## snake_case entity name

      ## Foreign Entity column (repeat for each FK)
      - name: <fk_column_name>                          ## Required
        description: "<role of the entity>"             ## Required
        entity:
          type: foreign
          name: <entity_name>

      ## Time Dimension column
      - name: <time_column_name>                        ## Required
        description: "<what this dimension represents>" ## Required
        granularity: <day|week|month|quarter|year>      ## Required — at column level, NOT inside dimension:
        dimension:
          type: time

      ## Categorical Dimension column (repeat for each)
      - name: <column_name>                             ## Required
        description: "<what this dimension represents>" ## Required
        dimension:
          type: categorical

    metrics:                                            ## Required if building metrics on this model
      ## Simple Metric — direct aggregation (inline, no measure indirection)
      - name: <metric_name>                             ## Required — unique, snake_case
        description: "<what this metric measures>"      ## Required
        type: simple                                    ## Required
        label: "<Display Name for BI Tools>"            ## Required
        agg: <sum|count|count_distinct|avg|min|max>     ## Required
        expr: <column_name_or_sql_expression>           ## Required
        config:                                         ## Required
          meta:                                         ## Required
            business_domain: ""                         ## Required
            business_owner:                             ## Required — non-empty list of valid team emails
              - ""
            technical_owner:                            ## Required — non-empty list of valid team emails
              - ""
            freshness:
              refresh_cadence: ""                       ## Required — hourly|daily|weekly
              data_latency: ""                          ## Required — e.g., "T+1", "daily"
            technical_details:
              calculation_logic: ""                     ## Required — formula or SQL
              source_semantic_model: ""                 ## Required — semantic model name
              interpretation: ""                        ## Optional — "higher/lower is better"
            governance:
              approved_by: ""                           ## Required — approver email
              approval_date: ""                         ## Required — YYYY-MM-DD
              last_modified: ""                         ## Required — YYYY-MM-DD
              version: ""                               ## Required — semver (e.g., "1.0")
```

## Validation rules

Validation rules for semantic-model documents live in `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/`. Load rules on demand — do not preload upfront.

| Gate | File | Coverage |
|------|------|----------|
| Structural `[S]` | `validation/structural.md` → "Semantic Model" | 21 checks — structure, key presence, entity:/dimension: blocks, categorical only, agg enums, time dim |
| Ownership `[O]` | `validation/ownership.md` → "Semantic Model" | 5 checks — non-empty owner lists, business_domain, refresh_cadence, tags |
| Joinability `[J]` | `validation/joinability.md` | FK orphan + fan-out disambiguation |
| Data Context `[C]` | `validation/context-scoring.md` → "Semantic Model" | 4 checks — descriptions at model/entity/metric/dimension level |
| Data Quality `[Q]` | `validation/quality-scoring.md` → "Semantic Model" | 4 checks — FK cardinality, agg_time_dimension, time dim presence, granularity |

The email domain allowlist is read from `.semantic-trust.json` → `approved_email_domains` at runtime.

## Example (Latest Spec)

Domain: quick-commerce delivery operations (illustrative; column names are generic).

```yaml
models:
  - name: fact_delivery_orders
    description: "Grain-level fact table for delivery orders — one row per order."
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
          - "Operations"

    columns:
      - name: order_id
        description: "Primary identifier for each delivery order"
        entity:
          type: primary
          name: order

      - name: rider_id
        description: "Rider assigned to deliver the order"
        entity:
          type: foreign
          name: rider

      - name: order_created_date
        description: "Date the order was placed"
        granularity: day
        dimension:
          type: time

      - name: order_status
        description: "Current status of the order — delivered, cancelled, pending"
        dimension:
          type: categorical

      - name: city_id
        description: "City where the order was placed"
        dimension:
          type: categorical

    metrics:
      - name: total_orders
        description: "Total number of delivery orders placed"
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
              interpretation: "Higher is better — more orders means more revenue"
            governance:
              approved_by: ""
              approval_date: ""
              last_modified: ""
              version: "1.0"
```

## Example (Legacy Spec — dbt 1.6 to 1.11)

See `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/legacy-spec.md` for full reference. In the legacy spec, semantic models are separate top-level resources with `semantic_models:`, `entities:`, `dimensions:` (with `type_params.time_granularity` for time dims), and `measures:` arrays. Metrics are at the top-level `metrics:` key and reference measures via `type_params.measure`.

```yaml
semantic_models:
  - name: delivery_orders
    model: ref('fact_delivery_orders')
    defaults:
      agg_time_dimension: ordered_at
    entities:
      - name: order
        type: primary
        expr: order_id
      - name: rider
        type: foreign
        expr: rider_id
    dimensions:
      - name: ordered_at
        type: time
        type_params:
          time_granularity: day
      - name: order_status
        type: categorical
      - name: city_id
        type: categorical
    measures:
      - name: order_count
        agg: sum
        expr: 1
      - name: total_revenue
        agg: sum
        expr: amount

metrics:
  - name: order_count
    type: simple
    label: Order Count
    type_params:
      measure: order_count
  - name: total_revenue
    type: simple
    label: Total Revenue
    type_params:
      measure: total_revenue
```
