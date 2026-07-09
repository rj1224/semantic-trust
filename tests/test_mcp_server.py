# tests/test_mcp_server.py
# Calls the tool handler functions directly — no server boot needed (AD-1 note).
import json
from trust.mcp_server import handle_score_semantic_model, handle_scaffold_semantic_model
import pytest

LEGACY_FIX = "tests/fixtures/manifests/qcommerce_legacy"

def test_score_tool_returns_band_and_gates():
    result = handle_score_semantic_model(LEGACY_FIX, "orders")
    assert result["band"] in {"A", "B", "C", "D", "F"}
    assert {"structural", "ownership", "completeness", "uniqueness", "joinability"} <= set(result["gates"].keys())


def test_score_tool_returns_two_level_report():
    """MCP score tool must return the full two-level unified report (Task 3.1e)."""
    result = handle_score_semantic_model(LEGACY_FIX, "orders")
    # Model-level keys
    assert "trust_score" in result
    assert "band" in result
    assert "gates" in result
    # Per-document breakdown
    assert "documents" in result
    assert set(result["documents"].keys()) >= {"semantic_model", "metrics"}
    # Provenance-tagged issues list
    assert "issues" in result
    assert isinstance(result["issues"], list)


def test_score_tool_is_deterministic():
    """MCP score tool must produce identical output on repeated calls (no LLM in path)."""
    a = handle_score_semantic_model(LEGACY_FIX, "orders")
    b = handle_score_semantic_model(LEGACY_FIX, "orders")
    assert a == b


def test_score_tool_joinability_wired():
    """MCP score tool must surface joinability failures from cross-model checks."""
    from pathlib import Path
    joinbreak = str(Path(__file__).parent / "fixtures" / "manifests" / "qcommerce_joinbreak")
    result = handle_score_semantic_model(joinbreak, "orders")
    assert result["gates"]["joinability"] is False

def test_score_tool_unknown_model_returns_error():
    result = handle_score_semantic_model(LEGACY_FIX, "missing")
    assert "error" in result

def test_scaffold_tool_returns_columns(tmp_path):
    import json as _json
    manifest = {"nodes": {"model.shop.fct_orders": {
        "resource_type": "model", "name": "fct_orders",
        "columns": {
            "order_id":   {"name": "order_id",   "data_type": "VARCHAR"},
            "ordered_at": {"name": "ordered_at", "data_type": "TIMESTAMP"},
            "amount":     {"name": "amount",     "data_type": "NUMERIC"},
        }
    }}}
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(_json.dumps(manifest))
    result = handle_scaffold_semantic_model(str(tmp_path), "fct_orders")
    assert result["model"] == "fct_orders"
    assert {c["name"] for c in result["columns"]} == {"order_id", "ordered_at", "amount"}
    assert result["agg_time_dimension"] == "ordered_at"

def test_scaffold_tool_missing_manifest_returns_error(tmp_path):
    result = handle_scaffold_semantic_model(str(tmp_path), "fct_orders")
    assert "error" in result

def test_score_tool_multi_model_attribution():
    """MCP handler must correctly attribute metrics in a multi-model project with distinct column names."""
    from pathlib import Path
    fix = str(Path(__file__).parent / "fixtures" / "manifests" / "multi_model_latest")
    result_orders = handle_score_semantic_model(fix, "orders")
    result_refunds = handle_score_semantic_model(fix, "refunds")
    assert "error" not in result_orders
    assert "error" not in result_refunds
    # Both should return valid band ratings
    assert result_orders["band"] in {"A", "B", "C", "D", "F"}
    assert result_refunds["band"] in {"A", "B", "C", "D", "F"}
    # Neither model should have the other's metrics cause gate failures
    # (structural gate must pass for both — both have time dim and entity)
    assert result_orders["gates"]["structural"] is True
    assert result_refunds["gates"]["structural"] is True


# --- validate_semantic_model tool tests (Task 3.1g) ---

from trust.mcp_server import handle_validate_semantic_model


def test_validate_tool_no_payload_returns_deterministic_report():
    """validate_semantic_model with no judgment_payload returns the same deterministic report as score_semantic_model."""
    det = handle_score_semantic_model(LEGACY_FIX, "orders")
    result = handle_validate_semantic_model(LEGACY_FIX, "orders")
    assert result == det


def test_validate_tool_with_payload_adds_document_quality():
    """validate_semantic_model with a judgment_payload returns a unified report with document_quality set."""
    payload = {
        "documents": {
            "metrics": {
                "quality": 72,
                "issues": [
                    {
                        "severity": "warning",
                        "dimension": "data_context",
                        "rule": "description_vague",
                        "message": "description restates the formula",
                        "location": "metrics[0].description",
                    }
                ],
            }
        }
    }
    result = handle_validate_semantic_model(LEGACY_FIX, "orders", judgment_payload=payload)
    assert result["documents"]["metrics"]["document_quality"] == 72
    llm_issues = [
        i for i in result["documents"]["metrics"]["issues"]
        if i["provenance"] == "llm_judge"
    ]
    assert len(llm_issues) == 1
    assert llm_issues[0]["rule"] == "description_vague"


def test_validate_tool_guardrail_payload_cannot_override_gates():
    """validate_semantic_model enforces the guardrail: a payload trying to flip gates is silently ignored."""
    det = handle_score_semantic_model(LEGACY_FIX, "orders")
    malicious_payload = {
        "override_gates": {"structural": False, "ownership": False},
        "trust_score": 0,
        "band": "F",
        "documents": {},
    }
    result = handle_validate_semantic_model(LEGACY_FIX, "orders", judgment_payload=malicious_payload)
    # Deterministic gates, trust_score, and band are identical to the det report
    assert result["gates"] == det["gates"]
    assert result["trust_score"] == det["trust_score"]
    assert result["band"] == det["band"]
    assert result["context"] == det["context"]
    assert result["quality"] == det["quality"]


def test_validate_tool_none_payload_is_same_as_no_payload():
    """Passing judgment_payload=None is identical to omitting it."""
    no_payload = handle_validate_semantic_model(LEGACY_FIX, "orders")
    explicit_none = handle_validate_semantic_model(LEGACY_FIX, "orders", judgment_payload=None)
    assert no_payload == explicit_none
