# Naming Conventions

All naming rules for tables, columns, keys, semantic models, and metrics. These are enforced during document generation and validated in the naming compliance section of the validation report.

## Table Naming

| Type | Pattern | Examples |
|------|---------|----------|
| Fact Table | `fact_[business_event]` | `fact_orders`, `fact_transactions`, `fact_clicks` |
| Dimension Table | `dim_[entity]` | `dim_customer`, `dim_product`, `dim_date` |
| Mart | `mart_[business_area]_[cadence]` | `mart_sales_summary`, `mart_customer_360` |
| Staging | `stg_[source]_[table]` | `stg_postgres_users`, `stg_kafka_events` |
| Intermediate | `int_[description]` | `int_order_details`, `int_driver_aggregates` |

### Rules
- All table names use **snake_case**
- Names describe the business entity, not technical implementation
- No abbreviations unless widely understood (id, sku, tz)
- Fact tables represent business events or transactions
- Dimension tables represent entities (people, places, things)
- Marts represent pre-aggregated business-domain views

## Key Naming

| Type | Pattern | Examples |
|------|---------|----------|
| Primary Key (Fact/Dim) | `[table_name]_id` | `order_id`, `customer_id` |
| Foreign Key | Same as referenced primary key | `customer_id`, `product_id` |
| Natural Key | `[composite_name]_id` | `order_customer_id` |

### Rules
- Primary keys are named after the entity they identify
- Foreign keys use the EXACT same name as the primary key they reference
- Surrogate keys use `_id` suffix
- Natural/composite keys concatenate component names

## Column Naming

| Type | Pattern | Examples |
|------|---------|----------|
| Measures | `[descriptive_name]` | `order_amount`, `quantity_sold`, `discount_value` |
| Dimensions | `[descriptive_name]` | `order_status`, `product_category`, `customer_segment` |
| Timestamps | `[event]_at` | `created_at`, `updated_at`, `resolved_at` |
| Booleans | `is_[condition]` or `has_[condition]` | `is_active`, `has_vehicle`, `is_food_order` |
| Counts | `[entity]_count` | `order_count`, `ticket_count` |
| Amounts | `[description]_amount` or `[description]_value` | `total_amount`, `discount_value` |

### Rules
- All column names use **snake_case**
- No abbreviations unless widely understood (id, sku)
- Timestamps use UTC by default; include a timezone suffix only if the project standardizes on a named timezone
- Boolean columns start with `is_` or `has_`
- Avoid generic names like `value`, `type`, `status` without a prefix

## Semantic Model Naming

| Element | Convention | Example |
|---------|-----------|---------|
| Model Name | `business_domain` (snake_case, plural) | `orders`, `customers`, `inventory`, `tickets` |
| Entity Name | `singular_noun` (snake_case) | `order`, `customer`, `product`, `ticket_id` |
| Dimension Name | `descriptive_attribute` (snake_case) | `customer_name`, `order_status`, `product_category` |
| Measure Name | `metric_description` (snake_case) | `order_amount`, `quantity_sold`, `discount_applied` |

### Rules
- Semantic model names represent the business domain, not the underlying table
- Entity names are singular — they represent one instance
- Dimension names describe the attribute, not the column
- Measure names describe what is being measured
- All names are snake_case, no spaces

## Metric Naming

| Metric Type | Convention | Example |
|-------------|-----------|---------|
| Simple | `total_[measure]` or `[measure]_count` | `total_revenue`, `order_count` |
| Ratio | `[numerator]_per_[denominator]` | `revenue_per_customer`, `items_per_order` |
| Conversion | `[start]_to_[end]_rate` | `lead_to_customer_rate`, `trial_to_paid_rate` |
| Cumulative | `cumulative_[measure]` or `[measure]_to_date` | `cumulative_revenue`, `year_to_date_signups` |
| Derived | `net_[measure]` or descriptive name | `net_revenue`, `customer_lifetime_value` |

### Rules
- Metric names follow the type-specific convention above
- Names are snake_case, no spaces
- Names should be self-documenting — reading the name tells you what it measures
- Avoid redundant prefixes like `metric_` or `kpi_`
- Labels (display names) use Title Case with spaces: "Total Revenue", "Items Per Order"

## Validation

During validation, naming compliance is checked as a separate section in the report. Violations are flagged but do not reduce the trust score — they are pass/fail with specific violations listed. The naming compliance section checks:

1. **Model name** matches the expected pattern for its type (fact_*, dim_*, mart_*)
2. **All column names** are snake_case
3. **Semantic model name** follows the business_domain convention
4. **Measure names** follow the metric_description convention
5. **Metric names** follow the type-specific convention
