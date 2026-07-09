---
description: Score and certify a dbt Semantic Layer model — trust bands, gates, and dbt-parse certification.
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, Skill, AskUserQuestion]
argument-hint: <model_name>
---

Validate and score the dbt Semantic Layer documentation for the model the user names (or ask which model if unspecified).

Use the **validate-semantics** skill: assert the dbt project root, run the version-aware compile gate (`dbt parse` universal; `mf validate-configs` legacy-only), call the `score_semantic_model` MCP tool, run the judgment protocol, and render the two-level trust report.

This is natural-language-triggerable too — "validate my semantic model" / "score my dbt docs" activate the same skill without this command.
