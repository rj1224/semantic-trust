import pytest
from trust.manifest_loader import load_models, _read_semantic_manifest
from trust.manifest_loader import load_metrics  # noqa: E402

FIX = "tests/fixtures/manifests/single_latest"


def test_load_models_maps_manifest_to_normalized_model():
    models = load_models(FIX)
    assert len(models) == 1
    m = models[0]
    assert m.name == "fct_orders"
    assert m.source_file == "fct_orders"  # name is the identity/location key
    assert m.spec == "manifest"
    assert {e["name"] for e in m.entities} == {"order"}
    assert {d["name"] for d in m.dimensions} == {"ordered_at", "status"}
    assert m.has_time_dimension is True


def test_read_semantic_manifest_raises_when_absent(tmp_path):
    with pytest.raises(FileNotFoundError, match="dbt parse"):
        _read_semantic_manifest(str(tmp_path))


def test_load_models_sets_per_dimension_is_time():
    m = load_models(FIX)[0]
    by = {d["name"]: d["is_time"] for d in m.dimensions}
    assert by["ordered_at"] is True
    assert by["status"] is False


def test_load_models_maps_empty_measures_for_latest_inline():
    m = load_models(FIX)[0]
    assert m.measures == []


def test_definition_norm_identical_across_specs():
    latest = {m.name: m for m in load_metrics("tests/fixtures/manifests/single_latest")}
    legacy = {m.name: m for m in load_metrics("tests/fixtures/manifests/single_legacy")}
    a = latest["qcommerce_total_revenue"].definition_norm
    b = legacy["qcommerce_total_revenue"].definition_norm
    assert a == b and a != ""
    assert '"agg":"sum"' in a and '"expr":"amount"' in a


def test_legacy_owner_model_resolved_via_measure_lookup():
    by = {m.name: m for m in load_metrics("tests/fixtures/manifests/single_legacy")}
    assert by["qcommerce_total_revenue"].owner_model == "fct_orders"


class TestDefinitionNormAdvanced:
    PROJECT = "tests/fixtures/manifests/advanced_metrics"

    def test_cumulative_different_windows_have_different_norms(self):
        metrics = load_metrics(self.PROJECT)
        by_name = {m.name: m for m in metrics}
        assert (
            by_name["cumulative_revenue_3d"].definition_norm
            != by_name["cumulative_revenue_7d"].definition_norm
        )

    def test_cumulative_norm_contains_window(self):
        metrics = load_metrics(self.PROJECT)
        by_name = {m.name: m for m in metrics}
        assert "3" in by_name["cumulative_revenue_3d"].definition_norm
        assert "7" in by_name["cumulative_revenue_7d"].definition_norm

    def test_derived_identical_twins_collide(self):
        from trust.uniqueness import find_collisions

        metrics = load_metrics(self.PROJECT)
        collisions = find_collisions(metrics)
        formula_pairs = {
            frozenset([c["a"], c["b"]]) for c in collisions if c["kind"] == "formula"
        }
        assert frozenset({"net_margin", "net_margin_copy"}) in formula_pairs

    def test_ratio_norm_contains_num_denom(self):
        metrics = load_metrics(self.PROJECT)
        by_name = {m.name: m for m in metrics}
        norm = by_name["avg_order_value"].definition_norm
        assert "order_total" in norm
        assert "order_count" in norm
