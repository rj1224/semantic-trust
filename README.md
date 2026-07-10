# semantic-trust

Score and certify dbt Semantic Layer models. The trust/quality layer on top of authoring.

---

## Why

dbt-labs' agent skills author semantic models — they scaffold YAML, wire measures, and generate metric definitions. `semantic-trust` picks up where authoring stops: it **scores** and **certifies** those models before they reach production.

Scoring runs five deterministic gates:

- **Structural** — required fields present, types correct, no dangling references.
- **Uniqueness** — no duplicate metric or dimension names across the project.
- **Joinability** — join paths resolve; foreign-key references match declared entities.
- **Ownership** — every model has an approved owner email (optionally domain-restricted).
- **Completeness** — descriptions, labels, and metric intent fields are populated.

On top of the gate results, an LLM-judgment pass evaluates description quality, naming clarity, and metric intent. The combined score maps to an **A–F trust band**. A model that clears all gates and passes LLM review earns an A; structural failures floor the score at F.

Certification adds a final compile check via `dbt parse`. A model that scores B or above and compiles cleanly is marked **certified** and safe to promote.

`semantic-trust` works on top of any dbt project — it reads the compiled `semantic_manifest.json` that `dbt parse` emits and requires no changes to your dbt project structure.

---

## Install

### Claude Code plugin

Add the marketplace and install the plugin:

```bash
claude plugin marketplace add rj1224/semantic-trust
claude plugin install semantic-trust@semantic-trust
```

The second command uses the format `<marketplace-name>@<plugin-name>`. You can also install via the `/plugin` menu inside a Claude Code session.

Once installed, the MCP server starts automatically — the plugin's `.mcp.json` launches it via `uvx --from semantic-trust semantic-trust-mcp`. No manual server step is needed.

### MCP server (standalone)

If you need to run the MCP server outside of the plugin:

```bash
uvx --from semantic-trust semantic-trust-mcp
```

This starts the `semantic-trust-mcp` stdio server, exposing three tools: `scaffold_semantic_model`, `score_semantic_model`, and `validate_semantic_model`.

---

## Quickstart

With the plugin installed, open a Claude Code session in your dbt project directory, then:

**Natural language:**

```
validate my semantic model
```

Claude routes this to the `validate-semantics` skill, which compiles your project, runs all five gates, applies LLM judgment, and returns a trust report with gate results, score, trust band, and any blocking issues.

**Slash commands:**

```
/semantic-trust:validate <model>    # full trust report for a specific model
/semantic-trust:document            # generate or improve semantic model descriptions
/semantic-trust:build               # scaffold a new semantic model from a dbt model
```

The trust report shows gate-by-gate pass/fail, the A–F band, and a recommendation (promote / fix-and-retry / escalate).

---

## dbt version support

`semantic-trust` supports both the legacy and the current dbt Semantic Layer spec:

| dbt Core version | Spec form | Notes |
|---|---|---|
| 1.6 – 1.11 | **Legacy** — top-level `semantic_models:` block + standalone `measures:` in `schema.yml` | `mf validate-configs` available as an additional validation pass |
| **1.12+** / Fusion | **Latest** — model-annotation form: semantic metadata lives inside `models:` blocks | `mf validate-configs` not supported (skipped automatically) |

`dbt parse` is the **universal compile gate** for both versions — `semantic-trust` always runs it first. `mf validate-configs` is a legacy-only bonus pass and is skipped automatically on 1.12+ projects.

The spec version is detected from `target/semantic_manifest.json` at runtime (the compiled output of `dbt parse`); no configuration is required.

---

## Not affiliated with dbt Labs

`semantic-trust` references the dbt ecosystem and is designed to work alongside dbt projects. It is **not** an official dbt product and is not affiliated with, endorsed by, or supported by dbt Labs, Inc.

The vendored content under `vendor/dbt-agent-skills/` consists of dbt-labs' public Semantic Layer spec guides, included under their Apache-2.0 license. See `vendor/dbt-agent-skills/NOTICE` for attribution and license terms. That content remains Apache-2.0; the rest of this project is MIT.

---

## Configuration

`semantic-trust` works with zero configuration. To enable the ownership gate's domain check, add a `.semantic-trust.json` file at your dbt project root:

```json
{
  "approved_email_domains": ["example.com"]
}
```

With `approved_email_domains` set, the ownership gate fails any model whose `owner.email` does not match one of the listed domains. Without this config key, the ownership gate only checks that an email is present.

No other configuration keys are required or supported in 0.1.0.

---

## License

This project is licensed under the **MIT License** — see the `LICENSE` file.

Vendored content under `vendor/dbt-agent-skills/` is licensed under the **Apache-2.0 License** — see `vendor/dbt-agent-skills/NOTICE` and `vendor/dbt-agent-skills/LICENSE`.
