"""
Manifest-grounded semantic-model scaffolding (AD-9).
Reads dbt manifest.json to extract real columns + data types, classifies them,
and emits a CORRECT latest-spec skeleton per ${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md.

Grammar: dbt Core 1.12+ / Fusion format.
  - semantic_model: {enabled: true} at model level
  - agg_time_dimension at model level
  - columns each carry entity: or dimension: block (never semantic_type)
  - column-level granularity for time dimensions
  - numeric columns emitted as _metric_candidates (simple-metric expr targets, not dims)

The LLM fills entity roles, descriptions, and which metrics matter.
Eliminates hallucinated column names — the most common generation failure.
Exposed as MCP tool scaffold_semantic_model in trust/mcp_server.py.
"""
import json
import os

_TIME_MARKERS = ("date", "timestamp", "datetime", "time")
_NUM_MARKERS = ("int", "float", "numeric", "decimal", "double", "number", "bigint")


def load_manifest(project_dir: str) -> dict:
    path = os.path.join(project_dir, "target", "manifest.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def model_columns(manifest: dict, model_name: str) -> list:
    """Return [{name, data_type}] for the named model node. Empty list if not found."""
    for node in manifest.get("nodes", {}).values():
        if node.get("resource_type") == "model" and node.get("name") == model_name:
            return [
                {"name": c.get("name", ""), "data_type": (c.get("data_type") or "")}
                for c in (node.get("columns") or {}).values()
            ]
    return []


def classify(data_type: str) -> str:
    """Classify a SQL data type string as time / numeric / categorical."""
    dt = (data_type or "").lower()
    if any(t in dt for t in _TIME_MARKERS):
        return "time"
    if any(n in dt for n in _NUM_MARKERS):
        return "numeric"
    return "categorical"


def scaffold_semantic_model(model_name: str, columns: list) -> dict:
    """Emit a CORRECT latest-spec skeleton (dbt Core 1.12+) from real manifest columns.
    Grammar per ${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md: semantic_model:{enabled:true};
    agg_time_dimension + columns + metrics at model level; entity:/dimension: blocks on
    columns; column-level granularity for time; NO semantic_type; numeric cols are
    metric candidates (simple-metric expr targets), not dimensions."""
    out_cols, time_dims, metric_candidates = [], [], []
    for c in columns:
        kind = classify(c["data_type"])
        entry = {"name": c["name"]}
        if kind == "time":
            entry["granularity"] = "day"                 # placeholder; author confirms
            entry["dimension"] = {"type": "time"}
            time_dims.append(c["name"])
        elif c["name"].endswith(("_id", "_key")):
            # ID/key columns are entity candidates regardless of numeric data type
            entry["entity"] = {"type": "unknown", "name": c["name"].rsplit("_", 1)[0]}
        elif kind == "numeric":
            metric_candidates.append(c["name"])          # -> simple metric expr; skip as dim
            entry["_inferred"] = "measure_candidate"      # hint; strip before final YAML
        else:
            entry["dimension"] = {"type": "categorical"}
        out_cols.append(entry)
    return {
        "model": model_name,
        "semantic_model": {"enabled": True},
        "agg_time_dimension": time_dims[0] if time_dims else None,
        "columns": out_cols,
        "_metric_candidates": metric_candidates,
        "_note": ("skeleton from dbt manifest; set entity types (primary/foreign), "
                  "descriptions, and simple metrics (agg/expr/label) per "
                  "${CLAUDE_PLUGIN_ROOT}/vendor/dbt-agent-skills/latest-spec.md before committing"),
    }
