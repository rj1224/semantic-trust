---
name: validate-semantics
description: >
  Use when the user wants to validate or score existing dbt semantic-layer documentation.
  Triggers: "validate my docs", "score documentation", "check documentation
  quality", "run validation", "trust score for model", "are my docs
  production-ready", "check if docs pass CI gates". Reads existing files,
  runs checks, computes trust scores, and optionally fixes issues.
  Does NOT generate documents from scratch — use document-semantics for that.
version: 1.0.0
---

# Validate Documentation

You are helping the user validate and score existing dbt semantic-layer documentation for a specific model. This skill does NOT generate documents — it reads, scores, and optionally fixes existing files. Validation always operates at the model level — all documents for a model are validated together.

Follow this workflow strictly. The workflow has six steps, numbered below.

---

## Step 1: Assert dbt Project Root (AD-2)

Before any file discovery, confirm that `dbt_project.yml` exists in the current working directory.

```bash
ls dbt_project.yml
```

**If the file is not found:** stop immediately and report clearly:

> Error: `dbt_project.yml` not found in the current working directory.
> This skill must be run from the root of a dbt project.
> Navigate to your dbt project root and try again.

Do not attempt file discovery, validation, or scoring until this check passes.

---

## Step 2: Compile Gate — `dbt parse` (universal) + `mf validate-configs` (legacy only)

### 2a. Universal hard gate — `dbt parse`

Run `dbt parse` regardless of spec version. This is the universal compile gate: it works for both legacy (dbt ≤ 1.11) and latest (dbt ≥ 1.12 / Fusion) spec projects, and it produces `target/semantic_manifest.json` that the `score_semantic_model` MCP tool (Step 3) reads.

```bash
dbt parse
```

**If the command exits non-zero:** stop immediately and report the exact error verbatim:

> Compile gate failed — `dbt parse` returned errors:
> `<exact error output>`
>
> Fix the YAML/semantic-model errors before validation can proceed.
> Trust scoring is not performed when `dbt parse` fails.

**If the command exits zero:** `target/semantic_manifest.json` has been (re)written and is ready for scoring. Proceed to 2b.

### 2b. Legacy-only extra gate — `mf validate-configs`

Determine the dbt-core version to decide whether the optional `mf validate-configs` gate applies:

```bash
dbt --version
```

- **dbt-core minor < 1.12 (legacy spec, i.e. dbt ≤ 1.11):** optionally run `mf validate-configs` as an additional semantic-query validation layer. This gate tests whether MetricFlow can execute queries against the semantic models — a check `dbt parse` does not cover for legacy projects. If `mf validate-configs` exits non-zero, report the error as a warning and let the user decide whether to proceed.

  ```bash
  mf validate-configs
  ```

- **dbt-core minor ≥ 1.12 (latest spec / Fusion):** **do not run `mf validate-configs`**. The `dbt-metricflow` package pins `dbt-core < 1.12`, so it is structurally incompatible with latest-spec projects. Attempting to run it will fail with a version conflict. `dbt parse` is the authoritative and only compile gate for latest-spec projects. See `vendor/dbt-agent-skills/latest-spec.md` § Validation for the authoritative validation requirements for the latest spec.

**In both cases:** proceed to Step 3 after this step (do not block on the `mf validate-configs` result for legacy — it is advisory unless the user explicitly treats it as blocking).

---

## Step 3: Call `score_semantic_model` — Deterministic Two-Level Report

Call the `score_semantic_model` MCP tool with the current project directory and the model name.

```
tool: score_semantic_model
inputs:
  project_dir: <absolute path to the dbt project root>
  model: <model_name>
```

The tool returns the **deterministic two-level report** — the authoritative trust result. It is never overridden by later judgment steps. Record it as `deterministic_report`.

**Report shape:**
```json
{
  "model": "<model_name>",
  "compile_ok": true,
  "trust_score": <0-100>,
  "band": "<A|B|C|D|F>",
  "context": <0-100>,
  "quality": <0-100>,
  "gates": {
    "structural": <bool>,
    "ownership": <bool>,
    "completeness": <bool>,
    "uniqueness": <bool>,
    "joinability": <bool>
  },
  "documents": {
    "semantic_model": { "doc_type": "semantic_model", "status": "<pass|fail|absent>", "score": <float|null>, "mechanical": <float|null>, "issues": [...] },
    "metrics":        { "doc_type": "metrics",        "status": "<pass|fail|absent>", "score": <float|null>, "mechanical": <float|null>, "issues": [...] },
    "dbt_docs":       { "doc_type": "dbt_docs",       "status": "<pass|fail|absent>", "score": <float|null>, "mechanical": <float|null>, "issues": [...] },
    "few_shot":       { "doc_type": "few_shot",        "status": "<pass|fail|absent>", "score": <float|null>, "mechanical": <float|null>, "issues": [...] }
  },
  "issues": [...],
  "warnings": [...],
  "unattributed_metrics": <int>
}
```

**Score formula and band cutoffs** (source of truth: `skills/references/validation/scoring-formula.md`):
- `trust_score = context × 0.60 + quality × 0.40`
- A ≥ 90 / B ≥ 80 / C ≥ 70 / D ≥ 55 / F otherwise
- Band is capped to F when any gate fails

**If the tool returns `{"error": ...}`:** report it to the user and stop. The model was not found in the project.

---

## Step 4: Run the Judgment Protocol — Advisory Document-Quality Score

Read `eval/judge.md` from the project root for the full judgment protocol. Apply it to the generated semantic-layer YAML files for the model.

The judgment protocol produces a payload following the shape defined in `eval/judge.md` Step 6:

```json
{
  "documents": {
    "<doc_type>": {
      "quality": <int 0-100>,
      "issues": [
        {
          "severity": "warning",
          "dimension": "<dimension_name>",
          "rule": "<rule_id>",
          "message": "<human-readable finding>",
          "location": "<yaml_file_or_field_reference>"
        }
      ]
    }
  }
}
```

Valid `doc_type` values: `"semantic_model"`, `"metrics"`, `"dbt_docs"`, `"few_shot"`.

Record this payload as `judgment_payload`. It will be applied in Step 5.

**Key constraint:** the judgment protocol produces advisory findings only. It cannot override gates, `trust_score`, `band`, `context`, `quality`, or any deterministic issue. This is enforced by the engine in Step 5.

---

## Step 5: Apply Judgment — Unified Report

Call the `validate_semantic_model` MCP tool, passing the `judgment_payload` from Step 4 alongside the project directory and model name. This applies the judgment server-side and returns the unified report in one call.

```
tool: validate_semantic_model
inputs:
  project_dir: <absolute path to the dbt project root>
  model: <model_name>
  judgment_payload: <judgment_payload from Step 4>
```

The tool enforces the guardrail server-side:
- Only the `"documents"` key in the payload is read; all other keys (e.g. `override_gates`, `trust_score`, `band`) are silently ignored.
- `document_quality` per `DocumentReport` is set from the payload's `quality` field (clamped 0–100).
- Advisory issues from the payload are appended with `provenance="llm_judge"`.
- `trust_score`, `band`, `gates`, `context`, `quality`, and all `provenance="deterministic"` issues are **identical** to the deterministic report from Step 3.

Record the result as `unified_report`.

> Note: `validate_semantic_model` without a `judgment_payload` is equivalent to `score_semantic_model` — it returns the plain deterministic report. Either tool may be used in Step 3 for consistency; `score_semantic_model` is the canonical deterministic-only call.

---

## Step 6: Render the Two-Level Report

Present **both scores** clearly to the user. The two scores are separate and provenance-labeled — never blend them.

### Model-Level Summary

```
Model: <model_name>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Deterministic Trust Score:  <trust_score>/100  (Band <band>)
  Context sub-score:        <context>/100  [weight: 60%]
  Quality sub-score:        <quality>/100  [weight: 40%]
  Source: trust engine (provenance=deterministic)

CI Gates:
  structural:   <PASS|FAIL>
  ownership:    <PASS|FAIL>
  completeness: <PASS|FAIL>
  uniqueness:   <PASS|FAIL>
  joinability:  <PASS|FAIL>

Production-ready: <YES — all gates pass + band >= B | NO — see issues below>
```

### Per-Document Breakdown

For each document type in `unified_report.documents`:

```
<doc_type>: <status>  |  Mechanical score: <mechanical>/100
  Deterministic issues (provenance=deterministic):
    [<severity>] <dimension>/<rule>: <message>  @ <location>
  Advisory issues (provenance=llm_judge):
    [<severity>] <dimension>/<rule>: <message>  @ <location>
  Document quality (advisory): <document_quality>/100
    Source: LLM judge (provenance=llm_judge) — informational only
```

For absent documents (`status=absent`): show `score: N/A — document not found`.

### Score Provenance Labels

Always show which score comes from which source. Example phrasing:
- `Deterministic trust score: 78/100 (Band C) — computed by engine, reproducible`
- `Document quality (advisory): 65/100 — LLM assessment, informational only`

The deterministic trust score is the authoritative result for CI gates and production-readiness decisions.

---

## Revalidation and Fix Loop

After presenting the report, give the user these options:

**(a) "Done" / "Save report"**
- End the flow.

**(b) "Fix [specific issues]"**
- Apply fixes to the files in place in the dbt project.
- Examples: "add not_null data_tests to timestamps", "change tests: to data_tests:"
- After fixing: re-run from Step 2 (compile gate) and re-present the full report.

**(c) "Revalidate"**
- User has edited files externally.
- Re-run from Step 2 and re-present.

**(d) "Raise a PR"**
- Available at any point — the user does not need to reach a specific score first.
- Create a branch, commit modified files, raise a PR:

```bash
git checkout -b validate/<model_name>
git add <all modified files>
git commit -m "fix(<model_name>): validation fixes — trust score <before> → <after> (<band>)"
git push -u origin validate/<model_name>
gh pr create \
  --title "fix(<model_name>): documentation quality improvements" \
  --body "$(cat <<'EOF'
## Summary
- **Trust Score:** <before> → <after> (<band>)
- **What was fixed:** <from validation history>
- **Remaining issues:** <critical> critical, <warning> warnings, <info> info

## Files Modified
<list of files>
EOF
)"
```

Present the PR URL.

---

## Validation Rule Sources

Load rules on demand, not upfront. Reference these files for check definitions:

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
| Report schema | `skills/references/validation/report-schema.md` |

The email domain allowlist is read from `.semantic-trust.json` → `approved_email_domains` at runtime. No domain is hardcoded in this skill.

---

## What This Skill Does NOT Do

- Does not generate documentation from scratch — use the document-semantics skill for that.
- Does not override the deterministic trust score with LLM judgment — the guardrail in `apply_judgment` enforces this.
- Does not run without `dbt_project.yml` in CWD — Step 1 is a hard gate.
- Does not proceed past Step 2 if `dbt parse` fails — the universal compile gate is a hard gate.
- Does not run `mf validate-configs` on latest-spec projects (dbt ≥ 1.12) — `dbt-metricflow` pins `dbt-core < 1.12` and is structurally incompatible.
