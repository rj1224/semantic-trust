import json
from trust.manifest_scaffold import (
    load_manifest,
    model_columns,
    classify,
    scaffold_semantic_model,
)

MANIFEST = {
    "nodes": {
        "model.shop.fct_orders": {
            "resource_type": "model",
            "name": "fct_orders",
            "columns": {
                "order_id": {"name": "order_id", "data_type": "VARCHAR"},
                "ordered_at": {"name": "ordered_at", "data_type": "TIMESTAMP"},
                "amount": {"name": "amount", "data_type": "NUMERIC"},
            },
        }
    }
}


def test_model_columns_extracts_name_and_type():
    cols = model_columns(MANIFEST, "fct_orders")
    assert {c["name"] for c in cols} == {"order_id", "ordered_at", "amount"}


def test_classify():
    assert classify("TIMESTAMP") == "time"
    assert classify("NUMERIC") == "numeric"
    assert classify("VARCHAR") == "categorical"


def test_scaffold_keeps_real_columns_and_marks_time_dim():
    sk = scaffold_semantic_model("orders", model_columns(MANIFEST, "fct_orders"))
    assert sk["model"] == "orders"
    assert {c["name"] for c in sk["columns"]} == {"order_id", "ordered_at", "amount"}
    assert sk["agg_time_dimension"] == "ordered_at"


def test_scaffold_emits_latest_spec_structure():
    # Latest spec (1.12+): columns carry entity:/dimension: blocks; no semantic_type key.
    sk = scaffold_semantic_model("orders", model_columns(MANIFEST, "fct_orders"))
    assert "columns" in sk
    assert sk["semantic_model"] == {"enabled": True}
    # every column must have entity:, dimension:, or _inferred (measure candidate)
    for c in sk["columns"]:
        assert "entity" in c or "dimension" in c or "_inferred" in c, (
            f"column {c['name']!r} has neither entity nor dimension block"
        )


def test_load_manifest_reads_target(tmp_path):
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps(MANIFEST))
    assert load_manifest(str(tmp_path))["nodes"]


def test_model_not_in_manifest_returns_empty():
    assert model_columns(MANIFEST, "nonexistent") == []


def test_scaffold_emits_correct_latest_grammar():
    cols = [
        {"name": "order_id", "data_type": "integer"},
        {"name": "ordered_at", "data_type": "timestamp"},
        {"name": "status", "data_type": "varchar"},
        {"name": "amount", "data_type": "numeric"},
    ]
    out = scaffold_semantic_model("fct_orders", cols)
    sm = out["semantic_model"]
    assert sm == {"enabled": True}  # only enabled under semantic_model
    assert out["agg_time_dimension"] == "ordered_at"  # model-level
    bycol = {c["name"]: c for c in out["columns"]}
    assert "semantic_type" not in bycol["ordered_at"]  # wrong-grammar key gone
    assert bycol["ordered_at"]["granularity"] == "day"  # column-level
    assert bycol["ordered_at"]["dimension"]["type"] == "time"
    assert bycol["status"]["dimension"]["type"] == "categorical"
    assert bycol["order_id"]["entity"]["type"] in (
        "primary",
        "unknown",
    )  # entity placeholder
    # numeric measure-candidate is surfaced for the LLM as a metric hint, not a dimension
    assert "amount" in out.get("_metric_candidates", [])
