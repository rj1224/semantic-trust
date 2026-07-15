# Changelog

All notable changes to `semantic-trust` will be documented in this file.

---

## 0.1.2 — 2026-07-15

Positioning + hardening release. Validation is now the product's hero; authoring is preserved as a bootstrap helper.

### Changed

- **`validate-semantics` is the primary command.** Removed the `/semantic-trust:document` and `/semantic-trust:build` slash commands. The `document-semantics` and `build-dbt-model` skills remain in the repo, reframed as bootstrap helpers for cold-starting a first semantic model — for production authoring, prefer dbt-labs' own Semantic Layer agent skills.
- **README differentiation** — leads with the `mf validate-configs` structural gap (semantic-trust is currently the only tool that validates the dbt 1.12+/Fusion spec) and distinguishes semantic-trust from `dbt-project-evaluator` and `dbt-checkpoint`.

### Fixed

- **MCP `serverInfo.version`** now reports the installed package version instead of the `mcp` SDK version.
- Three `mypy` type errors in the trust engine.

### Internal

- **Quality gates** — `ruff` (lint + format) and `mypy` added to CI; Python 3.11 added to the CI matrix.
- **Security hardening** — all GitHub Actions SHA-pinned; least-privilege workflow permissions; Dependabot (uv + github-actions), CodeQL SAST, and `SECURITY.md` added.

---

## 0.1.1 — 2026-07-11

Launch-blocker fixes applied after initial PyPI release.

### Fixed

- **MCP launch command** — corrected from `uvx semantic-trust-mcp` to `uvx --from semantic-trust semantic-trust-mcp` in `.mcp.json`, README, and e2e references.
- **CI extras** — CI workflow now installs the `ci` extra (`pip install "semantic-trust[ci]"`) so `pytest`, `hypothesis`, and `pyyaml` are available in CI.
- **Skill runtime paths** — all bundled-file references in `skills/**/SKILL.md` prefixed with `${CLAUDE_PLUGIN_ROOT}/` so they resolve when the plugin's CWD is the user's dbt project, not the plugin root.
- **Marketplace manifest** — added `.claude-plugin/marketplace.json` and rewrote install docs to reflect the real two-step flow (`claude plugin marketplace add` + `claude plugin install`).
- **Apache-2.0 LICENSE** — added `vendor/dbt-agent-skills/LICENSE` for vendored dbt-labs Semantic Layer spec references (content remains Apache-2.0; project itself is MIT).
- **MCP dependency cap** — capped `mcp<2` in `pyproject.toml` runtime dependencies to prevent breaking changes from a major MCP SDK bump.

---

## 0.1.0 — 2026-07-01

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
