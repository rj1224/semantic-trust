---
description: Build a dbt model plus its Semantic Layer definition, enforcing dbt 1.8+ contracts.
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, Skill, AskUserQuestion]
argument-hint: <model_name>
---

Build a dbt model and its Semantic Layer definition for the target the user names (or ask if unspecified).

Use the **build-dbt-model** skill: scaffold-first from the manifest, follow the correct grammar (vendored dbt-labs spec), and enforce dbt 1.8+ model contracts.

Also natural-language-triggerable — e.g. "build a dbt model for daily revenue".
