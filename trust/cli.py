"""
Local dev CLI for the trust scorer. NOT the skill-facing interface in production —
skills consume the MCP server (trust/mcp_server.py, AD-1).

Retained for: manual spot-checks during development, smoke tests, Task 3 wiring smoke.
"""
import json, sys
from trust.manifest_loader import load_models, load_metrics
from trust.uniqueness import find_collisions
from trust.joinability import check_joinability
from trust.scorer import score_model


def _metrics_for_model(sm, all_metrics):
    """
    Return metrics owned by this semantic model.

    Attribution is exact via each metric's owner_model field, stamped at load time:
    - Latest spec: STRUCTURAL — a simple metric is owned by the model it is nested
      under (semantic_model.metrics). No column/substring matching.
    - Legacy spec: the semantic_model that DEFINES the measure the metric references
      (type_params.measure → SM).
    Cross-model metrics (latest derived/ratio) have owner_model=None and match no model.
    """
    return [m for m in all_metrics if m.owner_model == sm.name]


def _orphan_collision_warnings(all_metrics: list, collisions: list) -> list[str]:
    """
    Build warning strings for collisions that involve at least one unattributed
    (owner_model=None) metric.

    Orphan metrics are excluded from any single model's gate, so a collision among
    them would otherwise pass clean-and-silent. This helper surfaces BOTH formula and
    name collisions that involve an orphan so they are visible in the report.

    Note: a name collision between two orphan metrics is unreachable via real dbt —
    dbt enforces unique metric names at parse time. This path is retained as
    defense-in-depth and is unit-tested directly in tests/test_cli.py.

    Args:
        all_metrics: full list of NormalizedMetric for the project.
        collisions:  output of find_collisions(all_metrics), each a dict with keys
                     {kind, a, b, files}.

    Returns:
        List of human-readable warning strings (may be empty).
    """
    unattributed_names = {m.name for m in all_metrics if m.owner_model is None}
    warnings: list[str] = []
    for c in collisions:
        kind = c.get("kind")
        if kind not in ("formula", "name"):
            continue
        label = "formula collision" if kind == "formula" else "name collision"
        if c.get("a") in unattributed_names:
            warnings.append(
                f"unattributed metric '{c['a']}' has {label} with '{c['b']}'"
            )
        elif c.get("b") in unattributed_names:
            warnings.append(
                f"unattributed metric '{c['b']}' has {label} with '{c['a']}'"
            )
    return warnings


def build_report_object(project_dir: str, model_name: str):
    """
    Build the fully-populated ModelReport object for *model_name*.

    Returns a ModelReport on success, or a dict {"model": ..., "error": ...} if the
    semantic model is not found. Callers that need the object for apply_judgment must
    check for the error dict first (isinstance check on dict).

    This is the shared implementation beneath build_report (dict) and the MCP
    validate_semantic_model handler (object).  Back-compat: build_report's dict
    contract is preserved by calling .to_dict() on the result.
    """
    from trust.report import ModelReport  # avoid circular at module level
    models = load_models(project_dir)
    sm = next((m for m in models if m.name == model_name), None)
    if sm is None:
        return {"model": model_name, "error": "semantic model not found in project"}
    all_metrics = load_metrics(project_dir)
    collisions = find_collisions(all_metrics)
    model_metrics = _metrics_for_model(sm, all_metrics)
    # Joinability needs ALL models — compute cross-model issues then filter to this model.
    all_j_issues = check_joinability(models)
    model_j_issues = [i for i in all_j_issues if i.location == sm.source_file]
    rep = score_model(
        sm, model_metrics, collisions,
        joinability_issues=model_j_issues,
        project_dir=project_dir,
    )
    unattributed = [m for m in all_metrics if m.owner_model is None]
    rep.warnings = _orphan_collision_warnings(all_metrics, collisions)
    rep.unattributed_metrics = len(unattributed)
    return rep


def build_report(project_dir: str, model_name: str) -> dict:
    """Return the deterministic trust report as a plain dict (back-compat public API)."""
    result = build_report_object(project_dir, model_name)
    if isinstance(result, dict):
        # error path — already a dict
        return result
    return result.to_dict()


def main_cli():
    if len(sys.argv) < 3:
        print("usage: python -m trust.cli <project_dir> <model_name>", file=sys.stderr)
        sys.exit(1)
    project_dir, model_name = sys.argv[1], sys.argv[2]
    print(json.dumps(build_report(project_dir, model_name), indent=2))


if __name__ == "__main__":
    main_cli()
