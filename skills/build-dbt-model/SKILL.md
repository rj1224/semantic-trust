---
name: build-dbt-model
description: >
  Bootstrap helper — use ONLY to scaffold a first dbt model + semantic definition from a raw
  SQL query when none exists yet, as a ramp into validation. Not the primary entry point: for
  scoring/certifying existing models use validate-semantics, and for production authoring
  prefer dbt-labs' own Semantic Layer agent skills. Triggers: "bootstrap a new dbt model from
  this SQL so I can validate it".
version: 1.0.0
---

# Build a dbt Model from SQL

You are helping the user create a proper dbt model from a SQL query, then generate full semantic-layer documentation for it. This skill uses a scaffold-first workflow: the dbt manifest grounds every column name and data type before the LLM fills semantics, eliminating hallucinated column names.

This skill has 7 steps. Follow them in order. Do not skip any step.

**Grammar reference:** All semantic-model and metric YAML in this skill follows the canonical grammar documented in `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md` (dbt Core 1.12+ / Fusion) and `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/legacy-spec.md` (dbt Core 1.6–1.11). Do not invent grammar variants not present in those files.

## When NOT to Use

- User wants to **document an existing model** without building from SQL — use `document-semantics` skill instead.
- User wants to **only validate/score existing docs** without generating — use `validate-semantics` skill instead.

---

## Step 1: Assert dbt Project Root (AD-2)

Before any file discovery, confirm that `dbt_project.yml` exists in the current working directory.

```bash
ls dbt_project.yml
```

**If the file is not found:** stop immediately and report:

> Error: `dbt_project.yml` not found in the current working directory.
> This skill must be run from the root of a dbt project.
> Navigate to your dbt project root and try again.

Do not proceed past this step until the check passes.

---

## Step 2: Gather the Raw SQL

### 2a. Receive the Query

Determine the input type from what the user has provided:
- File path → read the file to get the SQL query
- Inline SQL → use it directly
- Empty → ask the user to provide their SQL query or a file path

### 2b. Gather Model Intent

Ask the user for:

1. **Model name** — suggest based on naming conventions from `${CLAUDE_PLUGIN_ROOT}/skills/references/standards/naming-conventions.md`:
   - Must have a layer prefix: `mart_`, `fact_`, `dim_`, `stg_`, or `int_`
   - Use snake_case; describe the business entity or event
2. **Target layer** — staging / intermediate / mart / fact / dim
3. **Description** — what this model represents in plain business language
4. **Grain** — what one row represents ("One row = one order line item")
5. **Owner email** — required for ownership scoring

Use the model-type decision tree in `${CLAUDE_PLUGIN_ROOT}/skills/references/standards/model-design.md` (Section 2) to auto-suggest the layer if the user is unsure. Present your suggestion and get confirmation. Do NOT proceed until the user approves the model name and layer.

---

## Step 3: Author the dbt Model SQL

**The user's SQL query is the primary source of truth for the model logic.** Convert it into a proper dbt model file. Do not rewrite or reinterpret the business logic.

Read `${CLAUDE_PLUGIN_ROOT}/skills/references/standards/model-design.md` on demand — load Section 1 (Layers) and Section 6 (Contracts).
Read `${CLAUDE_PLUGIN_ROOT}/skills/references/workflows/model-building-workflows.md` — load the workflow section matching the model type:
- Fact → Section 1 | Dimension → Section 2 | Mart → Section 3

### 3a. Transform SQL to dbt

The conversion must:
1. **Preserve the original query logic exactly** — do not change business logic, filter conditions, join logic, or aggregation behavior
2. **Replace hardcoded table references** with `{{ ref('model_name') }}` for existing dbt models or `{{ source('source_name', 'table_name') }}` for raw sources
3. **Add a proper `{{ config() }}` block** with the materialization confirmed in Step 2b
4. **Add a header comment** with model name, description, grain, and owner
5. **Structure with CTEs** if the query does not already use them — use descriptive CTE names
6. **Use snake_case** for all column aliases
7. **Qualify column names** with table aliases in joins

### 3b. Add dbt 1.8+ Contract Block (differentiating value-add)

For every model that will serve as a source for semantic models (facts, dimensions, marts consumed downstream), include `contract.enforced: true` in the config block and specify `data_type` on every column in the corresponding YAML.

```yaml
models:
  - name: fact_orders
    config:
      contract:
        enforced: true
      materialized: table
    columns:
      - name: order_id
        data_type: varchar
        data_tests:
          - not_null
          - unique
      - name: order_amount
        data_type: numeric
      - name: customer_id
        data_type: varchar
        data_tests:
          - not_null
```

**Key constraint:** the `contract: {enforced: true}` block with column-level data types is a core value-add of this skill. Always include it for fact, dim, and mart models. For staging/intermediate models, include it once the source schema is stable.

### 3c. Show and Confirm

Present the generated SQL and YAML to the user. Ask for confirmation before writing.

Once approved, write:
- SQL: `models/<layer>/<model_name>.sql`
- YAML: `models/<layer>/<model_name>.yml` with `data_tests:` (not `tests:`) and the contract block

Use `data_tests:` not `tests:` throughout (dbt 1.8+).

---

## Step 4: Parse — `dbt parse`

Before the scaffold MCP tool can run, the dbt project must be parsed to generate `target/manifest.json`.

Instruct the user:

> Run `dbt parse` in your dbt project root to generate the manifest, then confirm it succeeded.

Wait for the user to confirm that:
1. `dbt parse` exited successfully
2. `target/manifest.json` exists

**If the manifest is absent after `dbt parse`:** stop and report:

> `target/manifest.json` not found after `dbt parse`. Check for parse errors in the output above, fix them, and re-run.

Do not proceed to Step 5 until the manifest exists.

---

## Step 5: Scaffold from Manifest (AD-9)

Call the `scaffold_semantic_model` MCP tool to get a deterministic column skeleton from the dbt manifest.

```
tool: semantic-trust__scaffold_semantic_model
inputs:
  project_dir: <absolute path to CWD>
  model: <model_name>
```

The tool returns a latest-spec skeleton (per `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md`):
```json
{
  "model": "<model_name>",
  "semantic_model": {"enabled": true},
  "agg_time_dimension": "<first_time_column_or_null>",
  "columns": [
    {"name": "<time_col>", "granularity": "day", "dimension": {"type": "time"}},
    {"name": "<id_col>", "entity": {"type": "unknown", "name": "<entity_name>"}},
    {"name": "<cat_col>", "dimension": {"type": "categorical"}},
    {"name": "<numeric_col>", "_inferred": "measure_candidate"}
  ],
  "_metric_candidates": ["<numeric_col>", ...],
  "_note": "skeleton from dbt manifest; set entity types (primary/foreign), descriptions, and simple metrics (agg/expr/label) per ${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md before committing"
}
```

Note: the scaffold uses nested `entity:` / `dimension:` blocks per the latest spec. There is no `semantic_type` key — that is a legacy/incorrect form. Numeric columns appear in `_metric_candidates` (not as dimensions).

**If the tool returns `{"error": ...}`:** report the error verbatim. The model was not found in the manifest — confirm the model name with the user and check that `dbt parse` ran after the model was written.

Present a brief summary to the user:
- Model: `<model_name>`
- Columns found: `<count>` (`<time_count>` time, `<numeric_count>` numeric, `<categorical_count>` categorical)
- Suggested `agg_time_dimension`: `<value>`

---

## Step 6: Fill Semantics and Write YAML

Using the scaffold from Step 5 as the column-name ground truth, fill the semantic model.

### 6a. Entity Roles

Use the Entity Identification Decision Tree from `${CLAUDE_PLUGIN_ROOT}/skills/references/standards/metric-design.md` (Section 2):
- Identify the primary entity (the main business object — one per semantic model)
- Identify foreign entities (related objects with FK relationships)
- Use `expr:` for all column references — never `column:`

### 6b. Dimension Classifications

- `time` columns → add as time dimensions with column-level `granularity: day`
- `categorical` columns → add as categorical dimensions
- Use `categorical` not `boolean` for boolean columns

### 6c. Metric Candidates

Ask the user which numeric columns to expose as metrics. For each selected:
- Propose a metric name following naming conventions (`total_<measure>`, `<measure>_count`, etc.)
- Confirm aggregation type (sum / count / avg / count_distinct)

**Simple metrics** (single SM) → define inline under `semantic_model.metrics` in the same YAML file.
**Cross-SM derived/ratio metrics** → separate file per `${CLAUDE_PLUGIN_ROOT}/skills/references/standards/metric-design.md` (Section 3).

Read the canonical cross-SM file-placement rule (Section 3 of metric-design.md): the criterion is cross-SM dependency, not metric complexity.

### 6d. Ownership Fields

Fill all `config.meta` ownership fields. If not provided by the user, generate with blank defaults (`""` for strings, `[]` for lists). Never use `<TODO>` or `<REPLACE>` placeholders.

### 6e. YAML Spec Rules (latest MetricFlow spec per `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md`)

- `models:` nested with `semantic_model:` key (`semantic_model: {enabled: true}`)
- Entities: inline `entity:` block on each column (not a top-level `entities:` list)
- Dimensions: inline `dimension:` block on each column (not a top-level `dimensions:` list)
- Simple metrics: `agg` + `expr` directly — no `type_params:` wrapper, no `measures:` block
- Use `expr:` not `column:` for all column references
- Use `data_tests:` not `tests:` (dbt 1.8+)
- Time dimensions must have column-level `granularity:` (not `type_params.time_granularity` — deprecated in dbt-core 1.12+)
- `agg_time_dimension` is a direct model-level key (not under `defaults:`)
- No `semantic_type` key on columns — that is a legacy/incorrect form

### 6f. Write Files and Compile Gate

Write:
- Semantic model + inline simple metrics → `models/semantics/<domain>/<model_name>.yml`
- Cross-model metrics → `models/semantics/<domain>/<metric_name>.yml`

Ask the user for the domain subfolder (e.g., `operations/`, `finance/`).

**Universal compile gate — `dbt parse`:**

Instruct the user:

> Run `dbt parse` to compile the semantic layer. Confirm it exits zero before proceeding to trust scoring.

Wait for the user to confirm `dbt parse` passed. If it fails, show the error and return to 6e to fix the YAML.

**Legacy-only extra gate — `mf validate-configs` (optional):**

Check the dbt-core version:
```bash
dbt --version
```

- **dbt-core < 1.12 (legacy spec):** optionally run `mf validate-configs` for additional semantic-query validation. If it exits non-zero, report as a warning and let the user decide whether to proceed.
- **dbt-core ≥ 1.12 (latest spec):** do not run `mf validate-configs`. The `dbt-metricflow` package pins `dbt-core < 1.12` and is structurally incompatible with latest-spec projects. See `${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md` § Validation.

---

## Step 7: Trust Score — `score_semantic_model`

Call the `score_semantic_model` MCP tool to get the deterministic trust report.

```
tool: semantic-trust__score_semantic_model
inputs:
  project_dir: <absolute path to CWD>
  model: <model_name>
```

Render the two-level trust report:

```
Model: <model_name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trust Score:  <trust_score>/100  (Band <band>)
  Context sub-score:  <context>/100  [weight: 60%]
  Quality sub-score:  <quality>/100  [weight: 40%]

CI Gates:
  structural:   <PASS|FAIL>
  ownership:    <PASS|FAIL>
  completeness: <PASS|FAIL>
  uniqueness:   <PASS|FAIL>
  joinability:  <PASS|FAIL>

Production-ready: <YES — all gates pass + band >= B | NO — see issues below>

Files written:
  <list all generated file paths>
```

Then show the per-document breakdown.

Also remind the user: "Run `git diff` in your dbt project to review all generated files."

### Revalidation and Fix Loop

After presenting the report, give the user these options:

**(a) "Done"**
End the flow.

**(b) "Fix [specific issues]"**
Apply fixes to the files in place. After fixing: re-run from Step 6f (dbt parse compile gate) and re-present the report.

**(c) "Revalidate"**
User has edited files externally. Re-run from Step 6f (dbt parse) and re-present.

**(d) "Raise a PR"**
Available at any point — the user does not need a specific score first.

```bash
git checkout -b build/<model_name>
git add models/<layer>/<model_name>.sql models/<layer>/<model_name>.yml models/semantics/<domain>/
git commit -m "feat(<model_name>): new dbt model + semantic-layer docs — trust score <score> (<band>)"
git push -u origin build/<model_name>
gh pr create \
  --title "feat(<model_name>): new dbt model + documentation" \
  --body "$(cat <<'EOF'
## Summary
- **Model:** `<model_name>` (<layer>, contract enforced)
- **Grain:** <grain statement>
- **Trust Score:** <score> (<band>)

## Files
<list all file paths — .sql, .yml, semantics YAML>

Generated by semantic-trust/build-dbt-model
EOF
)"
```

Present the PR URL to the user.

---

## Chains Into

- `document-semantics` — if the user wants to add few-shot examples or improve documentation further. Do not duplicate that skill's content; simply reference it.
- `validate-semantics` — if the user wants to re-score later without rebuilding from scratch.

---

## Validation Rule Sources

Load rules on demand — do not preload all files upfront.

| Gate / Dimension | Rule file |
|---|---|
| Structural `[S]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/structural.md` |
| Ownership `[O]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/ownership.md` |
| Completeness `[D]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/completeness.md` |
| Uniqueness `[U]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/uniqueness.md` |
| Joinability `[J]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/joinability.md` |
| Data Context `[C]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/context-scoring.md` |
| Data Quality `[Q]` | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/quality-scoring.md` |
| Severity mapping | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/severity-matrix.md` |
| Score formula + bands | `${CLAUDE_PLUGIN_ROOT}/skills/references/validation/scoring-formula.md` |

The email domain allowlist is read from `.semantic-trust.json` → `approved_email_domains` at runtime. No domain is hardcoded in this skill.

---

## What This Skill Does NOT Do

- Does not document an existing model without SQL input — use `document-semantics` skill for that.
- Does not validate without generating — use `validate-semantics` skill for that.
- Does not run without `dbt_project.yml` in CWD — Step 1 is a hard gate.
- Does not call `scaffold_semantic_model` before `dbt parse` — Step 4 is a hard gate.
- Does not score until `dbt parse` passes — Step 6f is the universal hard gate.
- Does not run `mf validate-configs` on latest-spec projects (dbt ≥ 1.12) — `dbt-metricflow` pins `dbt-core < 1.12` and is structurally incompatible.
- Does not generate column names from training data — all column names come from the manifest scaffold (Step 5).
