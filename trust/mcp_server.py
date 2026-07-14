"""
MCP server for the semantic-trust deterministic engine (AD-1).
Exposes two MCP tools over the mcp Python SDK:
  - score_semantic_model: runs the full trust scorer and returns a JSON report.
  - scaffold_semantic_model: reads manifest.json and returns a latest-spec skeleton.

Launched by: uvx --from <pkg-or-path> semantic-trust-mcp
declared in `.mcp.json` under mcpServers.

The CLI (trust/cli.py) is retained for local dev only; skills must use these MCP tools.
"""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types as mcp_types

from trust.cli import build_report, build_report_object
from trust.manifest_scaffold import load_manifest, model_columns, scaffold_semantic_model

try:
    _SERVER_VERSION = _pkg_version("semantic-trust")
except PackageNotFoundError:  # running from a source tree with no install metadata
    _SERVER_VERSION = "0+unknown"


# --- Handler functions (testable without a running server) ---

def handle_score_semantic_model(project_dir: str, model: str) -> dict:
    """Score a semantic model and return the trust report."""
    return build_report(project_dir, model)


def handle_validate_semantic_model(
    project_dir: str,
    model: str,
    judgment_payload: dict | None = None,
) -> dict:
    """
    Validate a semantic model and optionally apply an LLM judgment payload server-side.

    Builds the deterministic report via _build_report_object().  If judgment_payload
    is provided, applies it via trust.judgment.apply_judgment() and returns the unified
    report (.to_dict()).  If omitted or None, returns the deterministic report unchanged.

    The guardrail is enforced server-side: apply_judgment() silently ignores any payload
    keys that would touch trust_score, band, gates, context, quality, or deterministic
    issues — only the "documents" key is consumed.
    """
    result = build_report_object(project_dir, model)
    if isinstance(result, dict):
        # error path (model not found) — return as-is
        return result
    if judgment_payload is None:
        return result.to_dict()
    from trust.judgment import apply_judgment
    unified = apply_judgment(result, judgment_payload)
    return unified.to_dict()


def handle_scaffold_semantic_model(project_dir: str, model: str) -> dict:
    """Load manifest and return a latest-spec skeleton for the model."""
    try:
        manifest = load_manifest(project_dir)
    except (OSError, KeyError, ValueError) as exc:
        return {"error": f"could not read manifest.json: {exc}"}
    cols = model_columns(manifest, model)
    if not cols:
        return {"error": f"model '{model}' not found in manifest.json"}
    return scaffold_semantic_model(model, cols)


# --- MCP server wiring ---

def _make_server() -> Server:
    server = Server("semantic-trust", version=_SERVER_VERSION)

    @server.list_tools()
    async def list_tools() -> list[mcp_types.Tool]:
        return [
            mcp_types.Tool(
                name="score_semantic_model",
                description=(
                    "Score a dbt semantic model against the trust rubric "
                    "(context + quality + gates -> A-F band). "
                    "Returns a two-level unified deterministic report: "
                    "{model, trust_score, band, context, quality, "
                    "gates (structural/ownership/completeness/uniqueness/joinability), "
                    "documents (semantic_model/metrics/dbt_docs/few_shot per-artifact breakdown), "
                    "issues (list of {severity, dimension, rule, message, location, provenance}), "
                    "warnings (list[str]), unattributed_metrics (int), compile_ok (bool)}. "
                    "Judgment (LLM quality scores) is applied server-side via validate_semantic_model — "
                    "this tool returns only the deterministic report."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_dir": {
                            "type": "string",
                            "description": "Absolute path to the dbt project root.",
                        },
                        "model": {
                            "type": "string",
                            "description": "Name of the semantic model to score.",
                        },
                    },
                    "required": ["project_dir", "model"],
                },
            ),
            mcp_types.Tool(
                name="scaffold_semantic_model",
                description=(
                    "Generate a latest-spec MetricFlow semantic-model skeleton "
                    "from the dbt manifest.json for a given model. "
                    "Requires dbt parse to have been run (target/manifest.json must exist). "
                    "Returns a column-grounded skeleton; the LLM fills semantics."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_dir": {
                            "type": "string",
                            "description": "Absolute path to the dbt project root.",
                        },
                        "model": {
                            "type": "string",
                            "description": "Name of the dbt model (SQL model, not semantic model).",
                        },
                    },
                    "required": ["project_dir", "model"],
                },
            ),
            mcp_types.Tool(
                name="validate_semantic_model",
                description=(
                    "Validate a dbt semantic model and optionally apply an LLM judgment payload "
                    "server-side to produce a unified report. "
                    "Args: project_dir (str) — absolute path to dbt project root; "
                    "model (str) — semantic model name; "
                    "judgment_payload (dict, optional) — LLM judgment payload following the "
                    "eval/judge.md Step 6 shape: {\"documents\": {\"<doc_type>\": "
                    "{\"quality\": <0-100>, \"issues\": [...]}}}. "
                    "Returns the two-level deterministic report (same shape as score_semantic_model) "
                    "when judgment_payload is omitted or None. "
                    "Returns the unified report — identical deterministic fields plus document_quality "
                    "and llm_judge advisory issues per DocumentReport — when judgment_payload is given. "
                    "Guardrail enforced server-side: payload keys other than 'documents' (e.g. "
                    "override_gates, trust_score, band) are silently ignored; deterministic gates, "
                    "trust_score, band, context, quality, and provenance=deterministic issues are "
                    "never modified by the payload."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_dir": {
                            "type": "string",
                            "description": "Absolute path to the dbt project root.",
                        },
                        "model": {
                            "type": "string",
                            "description": "Name of the semantic model to validate.",
                        },
                        "judgment_payload": {
                            "type": "object",
                            "description": (
                                "Optional LLM judgment payload (eval/judge.md Step 6 shape). "
                                "Only the 'documents' key is consumed; all other keys are ignored."
                            ),
                        },
                    },
                    "required": ["project_dir", "model"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
        import json as _json
        if name == "score_semantic_model":
            result = handle_score_semantic_model(
                arguments["project_dir"], arguments["model"]
            )
        elif name == "scaffold_semantic_model":
            result = handle_scaffold_semantic_model(
                arguments["project_dir"], arguments["model"]
            )
        elif name == "validate_semantic_model":
            result = handle_validate_semantic_model(
                arguments["project_dir"],
                arguments["model"],
                judgment_payload=arguments.get("judgment_payload"),
            )
        else:
            result = {"error": f"unknown tool: {name}"}
        return [mcp_types.TextContent(type="text", text=_json.dumps(result, indent=2))]

    return server


def main():
    """Entry point for the semantic-trust-mcp console script (AD-1)."""
    import asyncio

    async def _run():
        server = _make_server()
        options = server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, options)

    asyncio.run(_run())


if __name__ == "__main__":
    main()
