# Security Policy

## Reporting a Vulnerability

Please report security issues **privately** via GitHub's
[private vulnerability reporting](https://github.com/rj1224/semantic-trust/security/advisories/new)
(the repo's **Security → Report a vulnerability** button). Do not open a public issue for a
security report. We aim to acknowledge reports within 3 business days.

## Trust Boundary

`semantic-trust` operates on **your own dbt project** — understand this before running it:

- **It runs your dbt project.** The tool shells out to your local `dbt parse` over a project
  directory you supply (`project_dir`). The subprocess is invoked as an **argument list with
  `shell=False`**, so the shell-injection surface is limited — but `dbt parse` executes your
  dbt project's own macros and hooks, which is inherent to the tool's purpose. **Only run
  `semantic-trust` against dbt projects you trust.**
- **The engine reads compiled JSON, not untrusted YAML.** Scoring reads the compiled
  `target/semantic_manifest.json` that `dbt parse` emits; the engine never parses or executes
  raw project YAML.
- **The LLM-judgment layer is advisory.** Judgment findings are informational and cannot alter
  deterministic gate results, `trust_score`, or `band` — this guardrail is enforced server-side.

## Supported Versions

The latest published `semantic-trust` release on PyPI receives security fixes.
