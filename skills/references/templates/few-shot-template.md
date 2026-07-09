# Few-Shot Examples — Template & Example

**File format:** JSON with `.json` extension (e.g., `fact_delivery_orders.json`).
**Location:** `models/few_shot_examples/<domain>/<model_name>.json`

## Template

```json
{
  "examples": [
    {
      "question": "<Natural language question a business user would ask>",
      "sql": "<Valid SQL query that answers the question using fully qualified table names>",
      "tables": ["<schema.table_name>"],
      "difficulty": "<basic|intermediate|hard>",
      "description": "<Concise explanation of what the query does and any edge cases>"
    }
  ]
}
```

**Field rules:**
- `question` — plain business language; no SQL jargon.
- `sql` — valid SQL; use fully qualified table names (`<database>.<schema>.<table>`).
- `tables` — list of tables referenced in the query.
- `difficulty` — must be one of `basic`, `intermediate`, or `hard`.
- `description` — explains the query logic and any non-obvious decisions (NULL handling, date anchoring, etc.).
- Minimum 5 examples covering all three difficulty levels.

## Validation rules

Validation rules live in `skills/references/validation/`. Load on demand.

| Gate | File | Coverage |
|------|------|----------|
| Structural `[S]` | `validation/structural.md` → "Few-Shot" | 4 checks — valid JSON, examples array, required fields, difficulty enum |
| Data Context `[C]` | `validation/context-scoring.md` → "Few-Shot" | 8 checks — business-language questions, descriptions, variety, complexity progression |
| Data Quality `[Q]` | `validation/quality-scoring.md` → "Few-Shot" | 6 checks — valid SQL, fully-qualified table names, column accuracy, NULL handling, difficulty mix |

## Example

Domain: quick-commerce delivery operations (illustrative; table names are generic).

```json
{
  "examples": [
    {
      "question": "How many delivery orders were placed in the last 7 days?",
      "sql": "SELECT COUNT(DISTINCT order_id) AS total_orders FROM warehouse.mart.fact_delivery_orders WHERE order_created_date >= CURRENT_DATE - 7;",
      "tables": ["fact_delivery_orders"],
      "difficulty": "basic",
      "description": "Counts distinct orders created in the last 7 days using the order creation date column."
    },
    {
      "question": "What is the cancellation rate by city this month?",
      "sql": "WITH monthly_orders AS (SELECT city_id, COUNT(DISTINCT order_id) AS total_orders, COUNT(DISTINCT CASE WHEN order_status = 'cancelled' THEN order_id END) AS cancelled_orders FROM warehouse.mart.fact_delivery_orders WHERE order_created_date >= DATE_TRUNC('month', CURRENT_DATE) GROUP BY city_id) SELECT city_id, total_orders, cancelled_orders, ROUND(cancelled_orders * 100.0 / NULLIF(total_orders, 0), 2) AS cancellation_rate_pct FROM monthly_orders ORDER BY cancellation_rate_pct DESC;",
      "tables": ["fact_delivery_orders"],
      "difficulty": "intermediate",
      "description": "Computes month-to-date cancellation rate per city. Uses NULLIF to avoid division by zero and DATE_TRUNC for month anchoring."
    },
    {
      "question": "Which riders have the highest cancellation-to-delivery ratio over the last 30 days?",
      "sql": "WITH rider_stats AS (SELECT rider_id, COUNT(DISTINCT order_id) AS total_orders, COUNT(DISTINCT CASE WHEN order_status = 'cancelled' THEN order_id END) AS cancellations, COUNT(DISTINCT CASE WHEN order_status = 'delivered' THEN order_id END) AS deliveries FROM warehouse.mart.fact_delivery_orders WHERE order_created_date >= CURRENT_DATE - 30 GROUP BY rider_id) SELECT rider_id, total_orders, cancellations, deliveries, ROUND(cancellations * 1.0 / NULLIF(deliveries, 0), 4) AS cancel_to_delivery_ratio FROM rider_stats WHERE total_orders >= 10 ORDER BY cancel_to_delivery_ratio DESC LIMIT 20;",
      "tables": ["fact_delivery_orders"],
      "difficulty": "hard",
      "description": "Computes the cancellation-to-delivery ratio per rider over 30 days. Filters to riders with at least 10 orders to reduce noise from low-volume riders. Uses NULLIF to guard against zero deliveries."
    },
    {
      "question": "What is the daily order trend for the past 4 weeks?",
      "sql": "SELECT order_created_date, COUNT(DISTINCT order_id) AS daily_orders FROM warehouse.mart.fact_delivery_orders WHERE order_created_date >= CURRENT_DATE - 28 GROUP BY order_created_date ORDER BY order_created_date;",
      "tables": ["fact_delivery_orders"],
      "difficulty": "basic",
      "description": "Daily order count over the trailing 28 days, ordered chronologically to support trend visualization."
    },
    {
      "question": "Compare this week's orders to the same week last year by city.",
      "sql": "WITH this_week AS (SELECT city_id, COUNT(DISTINCT order_id) AS orders_this_week FROM warehouse.mart.fact_delivery_orders WHERE order_created_date BETWEEN DATE_TRUNC('week', CURRENT_DATE) AND CURRENT_DATE GROUP BY city_id), same_week_ly AS (SELECT city_id, COUNT(DISTINCT order_id) AS orders_ly FROM warehouse.mart.fact_delivery_orders WHERE order_created_date BETWEEN DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '52 weeks' AND CURRENT_DATE - INTERVAL '52 weeks' GROUP BY city_id) SELECT COALESCE(tw.city_id, ly.city_id) AS city_id, COALESCE(tw.orders_this_week, 0) AS orders_this_week, COALESCE(ly.orders_ly, 0) AS orders_same_week_ly, ROUND((COALESCE(tw.orders_this_week, 0) - COALESCE(ly.orders_ly, 0)) * 100.0 / NULLIF(COALESCE(ly.orders_ly, 0), 0), 1) AS yoy_growth_pct FROM this_week tw FULL OUTER JOIN same_week_ly ly ON tw.city_id = ly.city_id ORDER BY yoy_growth_pct DESC NULLS LAST;",
      "tables": ["fact_delivery_orders"],
      "difficulty": "hard",
      "description": "Year-over-year comparison using CTEs and a FULL OUTER JOIN to retain cities that appear in only one period. COALESCE handles missing city records. NULLIF guards division by zero for new cities."
    }
  ]
}
```
