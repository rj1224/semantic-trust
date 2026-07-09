---
name: document-semantics
description: >
  Use when the user wants to generate or improve dbt semantic-layer documentation for an
  existing model. Triggers: "document this model", "generate dbt docs", "create semantic
  model", "write metrics YAML", "add few-shot examples", "improve documentation",
  "score my docs", "document my model", "I have metrics ready for this model".
version: 1.0.0
---

# Document a dbt Model

You are helping the user generate complete semantic-layer documentation for an existing dbt model. This skill uses a scaffold-first workflow: the dbt manifest grounds every column name and data type before the LLM fills semantics, eliminating hallucinated column names.

This skill has 6 steps. Follow them in order. Do not skip any step.

**Grammar reference:** All semantic-model and metric YAML in this skill follows the canonical grammar documented in `vendor/dbt-agent-skills/latest-spec.md` (dbt Core 1.12+ / Fusion) and `vendor/dbt-agent-skills/legacy-spec.md` (dbt Core 1.6–1.11). Do not invent grammar variants not present in those files.

## When NOT to Use

- User wants to **build a new model from a SQL query** — use `build-dbt-model` skill instead.
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

## Step 2: Scaffold from Manifest (AD-9)

Verify the manifest exists, then call the `scaffold_semantic_model` MCP tool to get a deterministic column skeleton from the dbt manifest.

**Check for manifest:**

```bash
ls target/manifest.json
```

**If absent:** stop and instruct:

> `target/manifest.json` not found. Run `dbt parse` first to generate the manifest, then re-run this skill.

**If present:** call the MCP tool:

```
tool: semantic-trust__scaffold_semantic_model
inputs:
  project_dir: <absolute path to the CWD>
  model: <model_name>
```

The tool returns a latest-spec skeleton (per `vendor/dbt-agent-skills/latest-spec.md`):
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
  "_note": "skeleton from dbt manifest; set entity types (primary/foreign), descriptions, and simple metrics (agg/expr/label) per vendor/dbt-agent-skills/latest-spec.md before committing"
}
```

Note: the scaffold uses nested `entity:` / `dimension:` blocks per the latest spec. There is no `semantic_type` key — that is a legacy/incorrect form. Numeric columns appear in `_metric_candidates` (not as dimensions).

**If the tool returns `{"error": ...}`:** report the error verbatim. The model was not found in the manifest — confirm the model name with the user.

Present a brief summary to the user:
- Model: `<model_name>`
- Columns found: `<count>` (`<time_count>` time, `<numeric_count>` numeric, `<categorical_count>` categorical)
- Suggested `agg_time_dimension`: `<value>`

---

## Step 3: Gather Requirements

### 3a. Check for Existing Documentation

Scan the dbt project for existing files:
```
models/docs/**/<model_name>.yml
models/semantics/**/*<model_name>*.yml
models/few_shot_examples/**/*<model_name>*.json
```

**If existing docs found:**

> Found existing docs for `<model_name>`.
>
> Would you like to:
> (a) **Improve** existing docs — keep what is there, fill gaps, fix issues
> (b) **Regenerate** from scratch — replace everything
> (c) **Just validate** — score without changes (jumps to Step 5)

Wait for the user to respond with (a), (b), or (c) before proceeding.

- **(a) Improve:** load existing content as the base. Identify gaps against the templates. Make targeted edits only. Then proceed to 3b.
- **(b) Regenerate:** proceed to 3b as if no docs exist.
- **(c) Validate:** jump to Step 5 with existing files.

**If no existing docs found:** proceed to 3b.

### 3b. Choose Documents

Ask the user which documents to generate:
- **All documents** (recommended) — dbt docs + semantic model + metrics + few-shot
- **dbt docs only** — column-level documentation
- **dbt docs + semantic model** — adds semantic layer definitions and metrics
- **dbt docs + few-shot** — adds query training examples

Wait for the user to respond before proceeding. The user's choice determines which templates to load.

Rules:
- Metrics require a semantic model. If the user wants metrics without a semantic model, generate the semantic model first.
- Metrics are defined inline in the semantic model file (latest spec — see `skills/references/templates/semantic-model-template.md`).
- Few-shot examples can be generated independently.

**`requires_semantic_docs` flag:**
- If the user selects any option that includes a semantic model: set `config.meta.requires_semantic_docs: true` in the dbt doc. Do not ask.
- If the user selects **dbt docs only**: ask — "Does this model require semantic documentation in the future? (true/false)"
- If the user selects **dbt docs + few-shot**: ask the same question.

---

## Step 4: Generate Documents and Write to Project

### 4a. Load Templates

Read the relevant templates from `skills/references/templates/` in the project where this skill is installed:
- `semantic-model-template.md` — for semantic models and their inline simple metrics
- `metrics-template.md` — for cross-model derived/ratio/conversion metrics
- `dbt-docs-template.md` — for dbt model documentation
- `few-shot-template.md` — for few-shot JSON examples

The templates emit the **latest MetricFlow spec** per `vendor/dbt-agent-skills/latest-spec.md`: `models:` nested with a `semantic_model:` key. Simple metrics are defined inline under `semantic_model.metrics` with `agg` + `expr` directly (no `type_params:` wrapper, no `measures:` block).

### 4b. Generate

Using the scaffold from Step 2 as the column-name ground truth, generate each document:

**Semantic model (latest spec):**
- Map each column from the scaffold to its semantic role.
- `time` columns → add as time dimensions with `granularity: day` (author confirms).
- `categorical` columns → add as categorical dimensions.
- `numeric` columns → candidates for inline simple metrics (ask the user which ones to expose as metrics).
- Use `expr:` for all column references — never `column:`.
- Fill entity types (primary/foreign) from the scaffold; identify the primary key column.
- Fill all `config.meta` ownership fields. If not provided by the user, generate with blank defaults (`""`); never use `<TODO>` or `<REPLACE>` placeholders.
- Simple metrics go inline under `semantic_model.metrics`. Each metric has `agg`, `expr`, and full `config.meta` (ownership, freshness, technical_details, governance).

**dbt docs:**
- Use `data_tests:` not `tests:` (dbt 1.8+).
- Identify PK column and add `not_null` + `unique` tests.
- Identify FK columns and add `relationships:` tests.
- All `config.meta` ownership fields must be present (blank if unknown).

**Few-shot:**
- Generate as a `.json` file.
- Minimum 5 examples covering `basic`, `intermediate`, and `hard` difficulty.
- Use fully qualified table names in SQL.
- Business-language questions — no SQL jargon in the `question` field.

### 4c. Write Files

Write files directly to the dbt project (CWD):
- dbt docs → `models/docs/<mart|dim|fact>/<model_name>.yml`
- Semantic model + inline metrics → `models/semantics/<domain>/<model_name>.yml`
- Cross-model metrics (derived/ratio only) → `models/semantics/<domain>/<metric_name>.yml`
- Few-shot → `models/few_shot_examples/<domain>/<model_name>.json`

Determine dbt docs subfolder from model name:
- `mart_*` → `models/docs/mart/`
- `dim_*` → `models/docs/dim/`
- `fact_*` → `models/docs/fact/`
- Other → ask the user

Ask the user for the semantics and few-shot domain subfolder (e.g., `operations/`, `finance/`).

**Do NOT present files to the user yet. Proceed immediately to Step 5.**

---

## Step 5: Compile Gate — Version-Aware Validation

Run the appropriate compile gate before trust scoring. This is a hard gate.

### 5a. Universal hard gate — `dbt parse`

Run `dbt parse` unconditionally. This is the authoritative compile gate for both legacy (dbt ≤ 1.11) and latest (dbt ≥ 1.12 / Fusion) spec projects.

```bash
dbt parse
```

**If the command exits non-zero:** stop and report the error verbatim:

> Compile gate failed — `dbt parse` returned errors:
> `<exact error output>`
>
> Fix the YAML/semantic-model errors before trust scoring can proceed.

Do not call `score_semantic_model` until `dbt parse` passes. Return to Step 4 to fix the generated YAML.

### 5b. Legacy-only extra gate — `mf validate-configs` (optional)

Determine the dbt-core minor version:

```bash
dbt --version
```

- **dbt-core < 1.12 (legacy spec):** optionally run `mf validate-configs` as an additional semantic-query validation layer. This tests whether MetricFlow can execute queries — a check `dbt parse` does not cover for legacy projects. If it exits non-zero, report the error as a warning and ask the user whether to proceed.
- **dbt-core ≥ 1.12 (latest spec):** **do not run `mf validate-configs`**. The `dbt-metricflow` package pins `dbt-core < 1.12` and is structurally incompatible with latest-spec projects. See `vendor/dbt-agent-skills/latest-spec.md` § Validation for authoritative validation requirements.

**If `dbt parse` exits zero:** proceed to Step 6 regardless of the `mf validate-configs` result.

---

## Step 6: Trust Score — `score_semantic_model`

Call the `score_semantic_model` MCP tool to get the deterministic trust report.

```
tool: semantic-trust__score_semantic_model
inputs:
  project_dir: <absolute path to the CWD>
  model: <model_name>
```

The tool returns a two-level report (model + per-document). Render it to the user:

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

Then show per-document breakdown from the report.

Also remind the user: "Run `git diff` in your dbt project to review the generated files."

### Revalidation and Fix Loop

After presenting the report, give the user these options:

**(a) "Done"**
End the flow.

**(b) "Fix [specific issues]"**
Apply fixes to the files in place. After fixing: re-run from Step 5 (compile gate) and re-present.

**(c) "Revalidate"**
User has edited files externally. Re-run from Step 5 and re-present.

**(d) "Add another document type"**
Return to Step 3b to select additional documents, then restart from Step 4.

**(e) "Raise a PR"**
Available at any point — the user does not need a specific score first.

```bash
git checkout -b docs/<model_name>
git add <all generated/modified files>
git commit -m "docs(<model_name>): add documentation suite — trust score <score> (<band>)"
git push -u origin docs/<model_name>
gh pr create \
  --title "docs(<model_name>): documentation suite" \
  --body "$(cat <<'EOF'
## Summary
- **Trust Score:** <score> (<band>)
- **Documents:** <list of document types generated>
- **Issues:** <critical> critical, <warning> warnings

## Files
<list all file paths>

Generated by semantic-trust/document-semantics
EOF
)"
```

Present the PR URL to the user.

---

## Validation Rule Sources

Load rules on demand — do not preload all files upfront.

| Gate / Dimension | Rule file |
|---|---|
| Structural `[S]` | `skills/references/validation/structural.md` |
| Ownership `[O]` | `skills/references/validation/ownership.md` |
| Completeness `[D]` | `skills/references/validation/completeness.md` |
| Uniqueness `[U]` | `skills/references/validation/uniqueness.md` |
| Joinability `[J]` | `skills/references/validation/joinability.md` |
| Data Context `[C]` | `skills/references/validation/context-scoring.md` |
| Data Quality `[Q]` | `skills/references/validation/quality-scoring.md` |
| Severity mapping | `skills/references/validation/severity-matrix.md` |
| Score formula + bands | `skills/references/validation/scoring-formula.md` |

The email domain allowlist is read from `.semantic-trust.json` → `approved_email_domains` at runtime. No domain is hardcoded in this skill.

---

## What This Skill Does NOT Do

- Does not build a new model from SQL — use `build-dbt-model` skill for that.
- Does not validate existing docs without generating — use `validate-semantics` skill for that.
- Does not run without `dbt_project.yml` in CWD — Step 1 is a hard gate.
- Does not run `score_semantic_model` until `dbt parse` passes — Step 5a is the universal hard gate.
- Does not run `mf validate-configs` on latest-spec projects (dbt ≥ 1.12) — `dbt-metricflow` pins `dbt-core < 1.12` and is structurally incompatible.
- Does not generate column names from training data — all column names come from the manifest scaffold (Step 2).
