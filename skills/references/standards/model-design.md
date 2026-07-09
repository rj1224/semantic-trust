# Model Design Frameworks

Decision trees, interface contracts, and readiness criteria for designing data models. Use these frameworks when classifying a model type, assessing readiness for the semantic layer, or determining where a new model fits in the data architecture.

Target: dbt-core 1.12+ | Source: dbt best practices 2025

## 1. Data Architecture Layers

```
Raw/Landing → Staging → Intermediate → Core (Facts, Dimensions) → Mart
                                              ↓
                                    Interface Contract
                                              ↓
                                    Semantic Models → Metrics
```

| Layer | Purpose | Materialization | Naming |
|-------|---------|----------------|--------|
| Staging | Clean raw data: rename columns, cast types, filter | `view` (default) or `incremental` for large sources | `stg_<source>_<table>` |
| Intermediate | Business logic transformations, join staging models | `ephemeral` (default) or `view` | `int_<description>` |
| Core - Fact | Business events/transactions (one row = one event) | `table` or `incremental` | `fact_<business_event>` |
| Core - Dimension | Business entities with descriptive attributes | `table` | `dim_<entity>` |
| Mart | Pre-aggregated business-domain views combining facts + dims | `table` or `incremental` | `mart_<business_area>` |

### Staging Layer Rules (dbt best practice)
- One staging model per source table
- Only rename, cast, and filter — no business logic
- Always materialized as `view` unless source has billions of rows
- Apply `data_tests` for source data quality (not_null on PKs, unique)
- This layer produces the "atoms" from which all other models are built

### Intermediate Layer Rules
- Stack transformations with clear purpose — each CTE or model should have a reason
- Use `ephemeral` materialization (no physical table) unless debugging requires `view`
- Not exposed to end users — only consumed by downstream models
- Can be skipped for simple transformations

## 2. Model Type Decision Tree

Use this when the build-dbt-model skill needs to classify a query into the right model type.

```
START: I need to create a new reporting model
  |
  ├─→ Am I modeling a BUSINESS EVENT or TRANSACTION?
  |   (Something that happened at a point in time)
  |   Examples: Sales, Orders, Clicks, Logins, Payments, Shipments
  |   |
  |   YES → FACT TABLE
  |   |   • Contains measurements (amounts, quantities, counts)
  |   |   • Has foreign keys to dimensions
  |   |   • Each row = one occurrence of the event
  |   |   • Naming: fact_<business_event>
  |   |   • Materialization: table or incremental
  |   |
  |   NO → Continue
  |
  ├─→ Am I modeling a BUSINESS ENTITY or DESCRIPTIVE ATTRIBUTES?
  |   (Something with relatively stable attributes)
  |   Examples: Customers, Products, Stores, Employees, Drivers
  |   |
  |   YES → DIMENSION TABLE
  |   |   • Contains descriptive attributes
  |   |   • Slowly changes over time (SCD strategy)
  |   |   • Each row = one entity instance
  |   |   • Naming: dim_<entity>
  |   |   • Materialization: table
  |   |
  |   NO → Continue
  |
  ├─→ Am I creating a BUSINESS-ORIENTED VIEW for specific analysis?
  |   (Combining facts + dimensions for easier consumption)
  |   Examples: Monthly sales summary, Customer 360, Product performance
  |   |
  |   YES → Is this for a SPECIFIC business use case?
  |   |   |
  |   |   YES → MART
  |   |   |   • Denormalized for performance
  |   |   |   • Combines facts + dimensions
  |   |   |   • Pre-aggregated or flattened
  |   |   |   • Naming: mart_<business_area>
  |   |   |   • Materialization: table or incremental
  |   |   |
  |   |   NO → Reconsider: Should users query facts + dims directly?
  |   |        OR is this really a semantic model? (not a reporting model)
  |
  ├─→ Am I cleaning/renaming RAW SOURCE data?
  |   |
  |   YES → STAGING MODEL
  |   |   • One model per source table
  |   |   • Rename, cast, filter only — no business logic
  |   |   • Naming: stg_<source>_<table>
  |   |   • Materialization: view
  |   |
  |   NO → Continue
  |
  └─→ Am I applying BUSINESS LOGIC to combine staging models?
      |
      YES → INTERMEDIATE MODEL
      |   • Transformation CTEs with clear purpose
      |   • Not exposed to end users
      |   • Naming: int_<description>
      |   • Materialization: ephemeral
      |
      UNCLEAR? Ask:
      • Does it measure something? → Fact
      • Does it describe something? → Dimension
      • Does it combine for easier analysis? → Mart
      • Is it a business abstraction? → Semantic Model (not a reporting model)
```

## 3. Interface Contract Checklist

Before moving from the reporting layer to the semantic layer, verify the model is semantic-ready. This checklist maps to the trust score dimensions.

```
□ METADATA COMPLETE [maps to: Ownership + Data Context]
  □ Table-level description with business purpose
  □ Every column has business-friendly description
  □ Grain statement documented ("One row = ...")
  □ Primary keys clearly identified
  □ Foreign keys and relationships documented
  □ Owner/contact information provided (valid email, not <TODO>)

□ DOCUMENTATION CLEAR [maps to: Data Context]
  □ Business logic explained in plain language
  □ Calculations and derivations documented
  □ Source lineage visible
  □ Update frequency documented

□ SCHEMA STABLE [informational — manual check]
  □ Breaking changes avoided or versioned
  □ Backward compatibility maintained
  □ Consider using dbt model contracts (config.contract.enforced: true)
    for critical downstream-facing models

□ QUALITY VALIDATED [maps to: Data Quality]
  □ Primary key uniqueness enforced (data_tests: not_null + unique)
  □ Referential integrity validated (FK data_tests: relationships)
  □ Data freshness within SLA
  □ Null handling documented
  □ Categorical columns have accepted_values where applicable

CRITICAL: If ANY item fails → fix before creating semantic models
```

## 4. Semantic Model Readiness Criteria

| Requirement | Why It Matters | Self-Check Question |
|-------------|----------------|---------------------|
| Clear Grain | Need to know what one row represents to build entities | Can I explain in one sentence what a row represents? |
| Business-Friendly Names | Reduces translation effort for semantic layer | Would a business user understand this column name? |
| Documented Measures | Need to know additivity for correct aggregation | Have I identified which measures are additive, semi-additive, non-additive? |
| Explicit Relationships | Enables joining across semantic models | Are all FK relationships documented with cardinality? |
| Stable Schema | Prevents breaking downstream metrics | Is this schema finalized and tested? |
| Quality Guarantees | Ensures trustworthy data | Are all data_tests passing? |

## 5. Metric & Semantic Model Design

Metric type decision trees, entity identification, and semantic model routing are in a dedicated file: `references/standards/metric-design.md`. This separation allows the metric design frameworks to be consumed independently (e.g., metric-backwards workflow) without loading the full model design context.

## 6. dbt Model Contracts (dbt-core 1.12+)

For critical models that are consumed downstream (by semantic models, BI tools, other teams):

```yaml
models:
  - name: fact_orders
    config:
      contract:
        enforced: true       # Enables preflight schema validation
      materialized: table
    columns:
      - name: order_id
        data_type: number     # Required when contract is enforced
        data_tests:
          - not_null
          - unique
```

When to enforce contracts:
- Models used as source for semantic models (critical path)
- Models consumed by other teams (public interface)
- Models driving executive dashboards (high visibility)

When to enforce with lighter touch:
- Staging models — enforce contracts on column names and data types once the source schema is stable. Skip enforcement only during active development when the source schema is still changing.
- Intermediate models — enforce contracts when the intermediate model is consumed by multiple downstream models. Skip enforcement for single-use intermediates.

When NOT to enforce:
- Models still in active development (any layer) — enable contracts once the schema stabilizes

Sources:
- [How we structure our dbt projects | dbt](https://docs.getdbt.com/best-practices/how-we-structure/1-guide-overview)
- [Model contracts | dbt](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
- [Staging Models Best Practices | dbt](https://www.getdbt.com/blog/staging-models-best-practices-and-limiting-view-runs)
