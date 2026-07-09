# Model Building Workflows

Step-by-step workflows for building fact tables, dimension tables, marts, semantic models, and metrics. Follow the relevant workflow when the build-dbt-model skill generates a new model.

Target: dbt-core 1.12+ | Source: dbt best practices 2025

---

## 1. Fact Table Workflow

Follow these steps when building a fact table (model type identified as `fact_*` by the decision tree in `model-design.md`).

### Step 1: Define the Business Event
- What business event am I modeling? (orders, transactions, clicks, shipments)
- What does one row represent? → Write a clear grain statement
- Output: `"One row = one order line item"` or `"One row = one support ticket"`

### Step 2: Identify Measures
For each numeric column that will be aggregated:
- Name: `order_amount`, `quantity_sold`, `discount_value`
- Data type: number, decimal, integer
- Additivity: additive (can sum across all dims), semi-additive (can't sum across time), non-additive (can't sum at all)
- Null handling: allow nulls? default to zero?

### Step 3: Identify Foreign Keys (Dimension References)
For each dimension this fact connects to:
- Which dimension table? (`dim_customer`, `dim_product`, `dim_date`)
- Foreign key field: `customer_id`, `product_id`
- Does the dimension exist? If not, create it first
- Relationship cardinality: typically many-to-one

Common fact dimensions: Time (always), Customer/User, Product/Item, Location, Status/Type

### Step 4: Identify Degenerate Dimensions
Descriptive fields that don't need a separate dimension table:
- Order number, invoice number, transaction ID
- These stay as regular columns in the fact table

### Step 5: Define Primary Key
Options:
- Surrogate key: `fact_id` (auto-generated hash)
- Natural key: combination of dimension FKs
- Composite key: `order_id || '-' || line_number`

In dbt, use `dbt_utils.generate_surrogate_key()` for hash-based surrogate keys.

### Step 6: Choose Materialization Strategy
- **`table`** — default for most fact tables, rebuilds fully each run
- **`incremental`** — for large, growing fact tables with billions of rows
  - Requires: `updated_at` timestamp or watermark column
  - Requires: `unique_key` for merge/upsert logic
  - Use `on_schema_change: 'append_new_columns'` for schema evolution

```yaml
{{ config(
    materialized='incremental',
    unique_key='<your_primary_key>',       -- e.g., 'order_id', or ['order_id', 'line_number'] for composite
    on_schema_change='append_new_columns'
) }}
```

### Step 7: Handle Late-Arriving Facts
- Accept and insert (most common)
- Document expected data latency
- For incremental models: ensure lookback window covers late arrivals

### Step 8: Build & Test
Write the `.sql` file following dbt conventions (CTEs, fully qualified names). Apply data_tests:
- `not_null` + `unique` on PK
- `not_null` on critical FKs
- `relationships` tests for FK integrity
- Row count checks where applicable
- `dbt_utils.expression_is_true` for business logic assertions

### Step 9: Complete Interface Contract
Before moving to semantic layer:
- Run the Interface Contract Checklist (from `model-design.md`)
- Ensure documentation is complete (dbt docs YAML)
- Request peer review

---

## 2. Dimension Table Workflow

Follow these steps when building a dimension table (model type identified as `dim_*`).

### Step 1: Define the Business Entity
- What business entity am I modeling? (customers, products, stores, drivers)
- What does one row represent? → `"One row = one customer"`
- Is this standalone or related to other dimensions?

### Step 2: Choose SCD Strategy
How to handle changes over time:

| Type | Behavior | When to Use | dbt Approach |
|------|----------|-------------|--------------|
| Type 0 | No changes tracked | Static reference data (country codes) | Standard model |
| Type 1 | Overwrite current value | Most attributes (email, name) | Standard model (default) |
| Type 2 | New row per change | Status changes, subscription tiers | `dbt snapshot` |
| Type 3 | Previous + current columns | Limited history needs | Standard model with extra columns |

dbt snapshots (for SCD Type 2) — dbt 1.9+ uses YAML snapshot config. The legacy Jinja `{% snapshot %}` block is deprecated and removed in a future major; new snapshots must be authored as YAML.

YAML snapshot config (canonical form for dbt-core 1.12+):

```yaml
## File location: snapshots/dim_customer_history.yml
##   (NOT under models/ — dbt has a separate snapshot-paths config; the default is "snapshots/")

snapshots:
  - name: dim_customer_history
    relation: ref('stg_customers')          ## or source('<source_name>', '<table>') for raw sources
    config:
      schema: snapshots                     ## target schema in the warehouse
      unique_key: customer_id               ## natural key on the source side
      strategy: timestamp                   ## or "check" if no reliable updated_at column
      updated_at: updated_at            ## required when strategy: timestamp
```

**Why YAML over the Jinja block:** the YAML form is parseable without a dbt run, supports configuration overrides via `dbt_project.yml`, and is the form going forward per the dbt-core 1.12+ spec. The Jinja form was deprecated before dbt-core 1.12+ and raises a deprecation warning; new code should use YAML.

**Migration note for existing Jinja snapshots:** rewrite the `{% snapshot %} … {% endsnapshot %}` block as the YAML form above, save under `snapshots/<name>.yml`, and delete the original `.sql` file. dbt will pick up the YAML config automatically. State is preserved across the migration (no historical data loss).

### Step 3: Define Primary Key Strategy
- Surrogate key (recommended): `customer_key` — stable across changes
- Natural key: `customer_id` — keep as separate column even with surrogate
- For SCD Type 2: surrogate key is unique per row, natural key + valid_from = composite business key

### Step 4: Identify Attributes
Group attributes logically:
- **Identifiers**: ids, codes
- **Descriptive**: names, descriptions
- **Categorical**: types, statuses, segments (add `accepted_values` data_tests)
- **Numeric**: scores, counts (non-additive)
- **Temporal**: created_date, modified_date

### Step 5: Define Hierarchies (if applicable)
- Geography: Country → State → City → Zip
- Product: Category → Subcategory → Product
- Organization: Company → Division → Department → Team
- Document all levels and roll-up paths

### Step 6: Handle Conformed Dimensions
If this dimension is used across multiple facts/domains:
- Use consistent naming and same keys across all facts
- Maintain as single source of truth
- Register as conformed dimension in catalog
- Examples: `dim_customer`, `dim_product`, `dim_date` (used everywhere)

### Step 7: Build & Test
- Materialization: `table` (dimensions are typically small enough for full refresh)
- data_tests: PK uniqueness, required fields not_null, categorical accepted_values
- For SCD Type 2: test natural_key + validity_period uniqueness

### Step 8: Complete Interface Contract
Same as fact table — run checklist, document, peer review.

---

## 3. Mart Workflow

Follow these steps when building a mart (model type identified as `mart_*`).

### Step 1: Identify Business Use Case
- What specific business analysis is this for?
- Who are the primary users?
- Why can't they use facts + dims directly?
- Valid reasons: performance (pre-join/aggregate), usability (simplify complex joins), consistency (one source for analysis)

### Step 2: Identify Source Models
- Which facts and dimensions to combine?
- Document join relationships: how tables connect, join keys, join types
- Use `ref()` for all upstream dbt models

### Step 3: Define Mart Grain
- Same as source fact (fully denormalized): `"One row = one order line with customer/product"`
- Aggregated (summarized): `"One row = one customer's monthly summary"`
- Snapshot (point-in-time): `"One row = one product's inventory as of date"`

### Step 4: Decide Denormalization Strategy
- **Full**: bring all dimension attributes — no joins needed for users, larger table
- **Partial**: bring commonly used attributes, keep dimension keys for optional joins (recommended)

### Step 5: Define Aggregations (if applicable)
For each aggregation: what GROUP BY dimensions, what aggregate functions
- Document additivity: can these aggregations be re-aggregated?
- Pre-compute complex business logic (derived flags, segmentation, scoring)

**Example — Monthly Sales Summary Mart:**
```sql
-- mart_monthly_sales_summary
-- Grain: one row per customer per month
-- Sources: fact_orders + dim_customers + dim_products

WITH orders AS (
    SELECT * FROM {{ ref('fact_orders') }}
),
customers AS (
    SELECT * FROM {{ ref('dim_customers') }}
),
monthly_agg AS (
    SELECT
        DATE_TRUNC('month', o.order_at) AS order_month,
        o.customer_id,
        c.customer_segment,
        c.city,
        COUNT(DISTINCT o.order_id) AS total_orders,
        SUM(o.order_amount) AS total_revenue,
        AVG(o.order_amount) AS avg_order_value,
        COUNT(DISTINCT o.product_id) AS unique_products_ordered
    FROM orders o
    LEFT JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY 1, 2, 3, 4
)
SELECT * FROM monthly_agg
```

### Step 6: Choose Refresh Strategy
- **Full refresh** (`table`): rebuild entirely — simple, best for small/medium marts
- **Incremental**: update only changed records — for large marts with stable history
- **Snapshot**: add new snapshot each run — for point-in-time analysis
- Document refresh frequency, dependencies, expected data latency

### Step 7: Build & Test
- data_tests: grain validation, expected row counts, aggregation correctness
- Compare to source facts (reconciliation): do mart totals match fact totals?
- Performance benchmark: ensure query times are acceptable

### Step 8: Complete Interface Contract
Same as fact/dim — run checklist, document, peer review.

---

## 4. Semantic Model Workflow

Follow when creating a semantic model after the reporting model is ready.

### Step 1: Identify Business Domain
- What business process are you modeling? (orders, support, supply)
- Who are the primary users?
- What questions do they need to answer?
- Output: domain name (e.g., "Supply", "Support", "Finance")

### Step 2: Verify Source Model Readiness
- Does the source model meet the Interface Contract? (check `model-design.md` Section 3)
- Is it semantic-ready? (clear grain, documented measures, explicit relationships)
- If NOT ready → fix the reporting model first, don't build on unstable foundations

### Step 3: Define Entities
Use the Entity Identification Decision Tree (`metric-design.md` Section 2):
- Identify primary entity (the main "thing" — one per semantic model)
- Identify foreign entities (related things with FK relationships)
- Document: name, type, description, expr (column or SQL expression)
- Remember: use `expr:` never `column:`

### Step 4: Define Dimensions
For each attribute users will slice/filter/group by:
- Name, type (`time` or `categorical` — NEVER `boolean`), label, description, expr
- Time dimensions MUST have column-level `granularity:` set (`type_params` time_granularity nesting is deprecated in dbt-core 1.12+)
- At least one time dimension required if measures exist
- Match `defaults.agg_time_dimension` to a time dimension name

### Step 5: Define Measures
For each numeric value that will be aggregated:
- Name, description, agg (sum/avg/count/count_distinct/min/max/sum_boolean/percentile), expr
- Document additivity (additive, semi-additive, non-additive)
- For semi-additive: use `non_additive_dimension` config
- Use `expr:` never `column:`

### Step 6: Define Relationships
For each foreign entity:
- `config.meta.relationship` with: model (referenced SM), type (cardinality), expr (join column)
- Ensure the referenced semantic model exists or is planned

### Step 7: Document & Validate
- Complete all config.meta fields (business_owner, technical_owner, business_domain, refresh_cadence, tags)
- Run the Semantic Model Checklist (`model-design.md` Section 3)
- Peer review with another analyst
- Business stakeholder validation

---

## 5. Metric Definition Workflow

Follow when creating metrics after the semantic model is ready.

### Step 1: Identify Business Question
- What does this metric answer? ("How much revenue?", "What's our CAC?")
- Is this a KPI or a supporting metric?
- Write it as a clear question in plain language

### Step 2: Determine Metric Type
Use the Metric Type Decision Tree (`metric-design.md` Section 1):
- Simple: direct aggregation of one measure
- Ratio: one metric / another metric
- Derived: expression combining multiple metrics
- Cumulative: running total over any ordered dimension (time, region, etc.)
- Conversion: stage-to-stage progression rate

### Step 3: Identify Source Semantic Model
- Which SM contains the measures needed?
- If multiple SMs → check if relationships exist between them
- Metric goes in the SAME file as its primary source SM (unless cross-SM)

### Step 4: Define Metric Formula
- Simple: `agg: <agg_fn>, expr: <column>` (no `type_params:` wrapper)
- Ratio: direct `numerator:`/`denominator:` keys (reference metrics; no type_params wrapper)
- Derived: `expr:` + `input_metrics:` list with aliases (NOT the legacy `metrics:` key under `type_params`)
- Cumulative: `input_metric: <metric_name>` + `window: <Nd>` as direct top-level metric keys — NOT under a `type_params` wrapper (dbt 1.12+ spec — changed from the measure+cumulative_type_params form used in dbt 1.9–1.11)

### Step 5: Define Grain & Dimensions
- Default time grain (from SM's agg_time_dimension)
- Available dimensions (from SM's dimensions list)
- Default filters (if any — e.g., status = 'completed')

### Step 6: Define Filters & Business Rules
- Default filters: use Jinja syntax `{{ Dimension('entity__dimension') }} = 'value'`
- Null handling: exclude or treat as zero?
- Division by zero: handle with NULLIF in source measures

### Step 7: Document Metadata
Required in `config.meta`:
- ownership: business_domain, business_owner, technical_owner
- freshness: refresh_cadence, data_latency
- technical_details: calculation_logic, source_semantic_model, interpretation
- governance: approved_by, approval_date, last_modified, version

### Step 8: Place in KPI Tree
- Parent metric (what does this roll up to?)
- Child metrics (what feeds into this?)
- Related metrics (logically connected)
- Document in `config.meta.relationship`

### Step 9: Validate
- Run the Metric Definition Checklist (`model-design.md`)
- Verify formula with sample data
- Business stakeholder approval
- Peer review

---

## 6. Quality Gates Summary

| Transition | Gate | Reference |
|-----------|------|-----------|
| Reporting → Semantic | Interface Contract | `model-design.md` Section 3 |
| Semantic → Metrics | SM Checklist + Validation | `model-design.md` Section 4 |
| Metrics → Published | Metric Quality Checklist | `model-design.md` Section 4 |

**Critical rule:** Never skip a gate. Building metrics on an incomplete semantic model, or a semantic model on an undocumented fact table, creates compounding quality debt.
