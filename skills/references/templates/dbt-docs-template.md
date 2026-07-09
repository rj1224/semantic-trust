# dbt Model Documentation — Template & Example

Target: dbt-core 1.12+

## Template

```yaml
version: 2                                               ## Optional since dbt 1.5 — include for clarity

models:
  - name: <table_name>                                    ## Required — must match the dbt model filename (without .sql)
    description: |-                                       ## Required — multi-line business description
      <Concise business context for the table.>
      - Source: database `<database_name>`, schema `<schema_level>` (raw/core/mart)
      - Grain: One row = <grain statement>
      - Refresh: <refresh cadence>
      - Table path: "<database>.<schema>.<table_name>"

    config:                                               ## Required
      meta:                                               ## Required
        owner:                                            ## Required — non-empty list of team-code labels (free-text business labels, not emails)
          - ""                                            ## e.g. "Delivery Ops"; add one "- " line per owner
        requires_semantic_docs: false                     ## Required — boolean. Set true if this model needs semantic model + metrics + few-shot docs.
        domain: ""                                        ## Required — e.g., Operations, Finance, Platform
        business_criticality: ""                          ## Required — Low|Medium|High
        refresh_frequency: ""                             ## Required — 5mins|Hourly|Daily|Weekly|Monthly
        data_classification: ""                           ## Required — Internal|Classified|Public
        technical_owner:                                  ## Required — non-empty list of valid team emails
          - ""                                            ## add one "- " line per additional owner
        never_full_refresh: false                         ## Optional — governance flag (boolean). Meta-only; does NOT change dbt behavior — use config.full_refresh on the model for actual control.
      tags:                                               ## Required — at config level; enables dbt tag selection
        - ""                                              ## e.g. "Delivery", "Operations"; add one "- " line per tag
      contract:                                           ## Optional — enable for constraint enforcement
        enforced: true

    columns:                                              ## Required — at least PK + key columns
      ## Primary Key Column(s)
      - name: <primary_key_column>                        ## Required
        description: "<business description> (PK)"        ## Required
        data_type: <data_type>                            ## Required — number, varchar, timestamp_ntz, boolean, etc.
        data_tests:                                       ## Required for PK — use data_tests (not tests)
          - not_null
          - unique

      ## Foreign Key Column(s)
      - name: <foreign_key_column>                        ## Required if FK exists
        description: "<description> (FK to <target_model>.<target_column>)"  ## Required
        data_type: <data_type>                            ## Required
        data_tests:                                       ## Recommended
          - not_null
          - relationships:
              to: ref('<target_model>')
              field: <target_column>

      ## Regular Columns
      - name: <column_name>                               ## Required
        description: "<business-friendly description>"    ## Required
        data_type: <data_type>                            ## Required
        data_tests:                                       ## Optional — add where relevant
          - not_null
          - accepted_values:
              values: ['<val1>', '<val2>']
```

## Validation rules

Validation rules live in `skills/references/validation/`. Load on demand — do not preload upfront.

| Gate | File | Coverage |
|------|------|----------|
| Structural `[S]` | `validation/structural.md` → "dbt docs" | 14 checks — key presence, `data_tests` not `tests`, boolean `requires_semantic_docs`, snake_case columns |
| Ownership `[O]` | `validation/ownership.md` → "dbt docs" | 2 checks — technical_owner non-empty valid emails, tags non-empty |
| Completeness `[D]` | `validation/completeness.md` → "dbt docs" | 3 checks — cross-file existence when `requires_semantic_docs: true` |
| Data Context `[C]` | `validation/context-scoring.md` → "dbt docs" | 7 checks — descriptions, grain, source, table path, column descriptions |
| Data Quality `[Q]` | `validation/quality-scoring.md` → "dbt docs" | 8 checks — PK/FK suffix rules, data_tests on PK, column coverage |

The email domain allowlist is read from `.semantic-trust.json` → `approved_email_domains` at runtime.

## Example

Domain: quick-commerce delivery operations (illustrative).

```yaml
version: 2

models:
  - name: fact_delivery_orders
    description: |-
      Fact table for all delivery orders from placement to completion.
      - Source: database `warehouse`, schema `mart`
      - Grain: One row = one delivery order
      - Refresh: daily
      - Table path: "warehouse.mart.fact_delivery_orders"

    config:
      meta:
        owner:
          - "Delivery Ops"
        requires_semantic_docs: true
        domain: "Delivery Operations"
        business_criticality: "High"
        refresh_frequency: "Daily"
        data_classification: "Internal"
        technical_owner:
          - ""
        never_full_refresh: false
      tags:
        - "Delivery"
        - "Operations"

    columns:
      - name: order_id
        description: "Unique identifier for each delivery order (PK)"
        data_type: number
        data_tests:
          - not_null
          - unique

      - name: rider_id
        description: "Identifier of the rider assigned to the order (FK to dim_riders.rider_id)"
        data_type: number
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_riders')
              field: rider_id

      - name: order_created_date
        description: "Date the order was placed by the customer"
        data_type: date
        data_tests:
          - not_null

      - name: order_status
        description: "Current status of the order — delivered, cancelled, pending, in_transit"
        data_type: varchar
        data_tests:
          - accepted_values:
              values: ['delivered', 'cancelled', 'pending', 'in_transit']

      - name: city_id
        description: "Identifier of the city where the order was placed"
        data_type: number

      - name: delivery_time_minutes
        description: "Time in minutes from order placement to delivery completion. NULL for undelivered orders."
        data_type: number
```
