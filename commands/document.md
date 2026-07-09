---
description: Generate dbt Semantic Layer documentation (semantic model + metrics) for a dbt model, grounded in the compiled manifest.
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, Skill, AskUserQuestion]
argument-hint: <model_name>
---

Document the dbt Semantic Layer for the model the user names (or ask which model if unspecified).

Use the **document-semantics** skill: scaffold from the compiled dbt manifest (real columns, correct latest/legacy grammar per the vendored dbt-labs spec in `vendor/dbt-agent-skills/`), then produce the semantic model + metrics YAML.

Also natural-language-triggerable — e.g. "document the semantics for fct_orders".
