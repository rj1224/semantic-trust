# tests/test_cli.py
# AD-4: direct import, not subprocess — faster and avoids PATH/venv issues.
from pathlib import Path
from trust.cli import build_report, _orphan_collision_warnings
from trust.normalized import NormalizedMetric

LEGACY_FIX = str(Path(__file__).parent / "fixtures" / "manifests" / "qcommerce_legacy")


def test_build_report_returns_band_and_gates():
    rep = build_report(LEGACY_FIX, "orders")
    assert rep["model"] == "orders"
    assert rep["band"] in {"A", "B", "C", "D", "F"}
    assert {
        "structural",
        "ownership",
        "completeness",
        "uniqueness",
        "joinability",
    } <= set(rep["gates"].keys())


def test_build_report_unknown_model_returns_error():
    rep = build_report(LEGACY_FIX, "nonexistent_model")
    assert "error" in rep


def test_orphan_name_collision_surfaces_warning():
    """Pure unit test of _orphan_collision_warnings for the name-collision path.

    Two orphan (owner_model=None) metrics that share a name must produce a
    name-collision warning, not pass clean-and-silent.

    Note: this scenario is unreachable via real dbt — dbt enforces unique metric names
    at parse time, so a semantic_manifest.json with two metrics sharing a name can
    never be genuine `dbt parse` output. No fixture is used here. The logic is
    retained as defense-in-depth and is tested entirely in-memory.
    """
    # Construct two orphan metrics with the same name but distinct object identities.
    metric_a = NormalizedMetric(
        name="blended_rate",
        type="derived",
        definition_norm="total_order_amount / 2",
        description="Derived metric A.",
        owner=None,
        source_file="models/metrics.yml",
        owner_model=None,
    )
    metric_b = NormalizedMetric(
        name="blended_rate",
        type="derived",
        definition_norm="total_order_amount / 3",
        description="Derived metric B — duplicate name, also orphaned.",
        owner=None,
        source_file="models/metrics.yml",
        owner_model=None,
    )
    all_metrics = [metric_a, metric_b]
    # Collision dict as find_collisions would produce for a name collision.
    collisions = [
        {
            "kind": "name",
            "a": "blended_rate",
            "b": "blended_rate",
            "files": ["models/metrics.yml", "models/metrics.yml"],
        }
    ]
    warnings = _orphan_collision_warnings(all_metrics, collisions)
    assert any("blended_rate" in w and "name collision" in w for w in warnings), (
        f"expected a name-collision warning for blended_rate, got: {warnings}"
    )


def test_build_report_is_two_level_and_deterministic():
    LATEST_FIX = str(
        Path(__file__).parent / "fixtures" / "manifests" / "qcommerce_latest"
    )
    a = build_report(LATEST_FIX, "orders")
    b = build_report(LATEST_FIX, "orders")
    assert a == b  # reproducible
    assert (
        "documents" in a
        and "trust_score" in a
        and a["band"] in {"A", "B", "C", "D", "F"}
    )


def test_build_report_joinability_sees_all_models():
    """build_report must pass ALL models in the project to the joinability gate,
    not just the target model (so cross-model join checks are meaningful).
    The joinbreak fixture has a parity mismatch — gate must fail, not pass silently."""
    JOINBREAK_FIX = str(
        Path(__file__).parent / "fixtures" / "manifests" / "qcommerce_joinbreak"
    )
    rep = build_report(JOINBREAK_FIX, "orders")
    assert "joinability" in rep["gates"]
    # Joinability MUST fail — orders has a parity mismatch with payments
    assert rep["gates"]["joinability"] is False, (
        "joinability gate should be False for joinbreak fixture, "
        f"got gates={rep['gates']}"
    )


def test_build_report_two_level_mcp_shape():
    """MCP handler must return the same two-level dict as build_report."""
    from trust.mcp_server import handle_score_semantic_model

    LATEST_FIX = str(
        Path(__file__).parent / "fixtures" / "manifests" / "qcommerce_latest"
    )
    rep = handle_score_semantic_model(LATEST_FIX, "orders")
    assert "documents" in rep and "trust_score" in rep
    assert rep["band"] in {"A", "B", "C", "D", "F"}
