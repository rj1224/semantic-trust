# Changelog

All notable changes to `semantic-trust` will be documented in this file.

---

## 0.1.0 — 2026 (unreleased)

Initial packaging of `semantic-trust`.

### Added

- **Manifest-grounded trust scoring engine** — reads dbt's compiled `semantic_manifest.json`; supports both the legacy spec (dbt Core 1.6–1.11, top-level `semantic_models:` + `measures:`) and the latest spec (dbt Core 1.12+ / Fusion, model-annotation form).
- **Four deterministic gates** — structural, uniqueness, joinability, ownership — each returning a pass/fail signal with structured diagnostics.
- **LLM-judgment layer** — evaluates description quality, naming clarity, and metric intent on top of gate results.
- **A–F trust band** — combined score maps to a letter grade; certified status requires B or above plus a clean `dbt parse` compile.
- **MCP server (`semantic-trust-mcp`)** — stdio server exposing `scaffold_semantic_model`, `score_semantic_model`, and `validate_semantic_model` tools; launched via `uvx semantic-trust-mcp`.
- **Claude Code plugin** — `.claude-plugin/plugin.json` manifest bundling three skills (`document-semantics`, `build-dbt-model`, `validate-semantics`) and the `.mcp.json` server declaration.
- **Slash commands** — `/semantic-trust:validate`, `/semantic-trust:document`, `/semantic-trust:build`.
- **Version-aware validation gate** — `dbt parse` runs universally; `mf validate-configs` runs only on legacy (1.6–1.11) projects and is skipped automatically on 1.12+.
- **Vendored dbt-labs Semantic Layer spec references** — pinned under `vendor/dbt-agent-skills/` (Apache-2.0); see `vendor/dbt-agent-skills/NOTICE`.

### Migration / Breaking Changes

**Project config format changed: `.dbt-sl-authoring.yml` → `.semantic-trust.json`**

The project config file has been renamed and its format changed from YAML to JSON. If you have an existing `.dbt-sl-authoring.yml` in your dbt project root, it will be silently ignored — you must recreate it as `.semantic-trust.json`.

Before (YAML, no longer read):
```yaml
approved_email_domains:
  - example.com
```

After (JSON, new format):
```json
{
  "approved_email_domains": ["example.com"]
}
```

No other config keys exist in 0.1.0, so migration is a one-time file recreation.
