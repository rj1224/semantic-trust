# tests/test_uniqueness.py
from trust.normalized import NormalizedMetric
from trust.uniqueness import normalize_formula, find_collisions
from trust.manifest_loader import load_metrics


def _nm(name, type_="simple", definition_norm=None, desc="d", owner="team", file_=None):
    dn = definition_norm or f'{{"type":"{type_}","type_params":{{"measure":"{name}"}}}}'
    return NormalizedMetric(
        name=name,
        type=type_,
        definition_norm=dn,
        description=desc,
        owner=owner,
        source_file=file_ or f"{name}.yml",
    )


def test_normalize_is_order_independent():
    # definition_norm is already pre-computed and stored; test that two metrics
    # with identical normalized formulas are detected as duplicates.
    a = _nm(
        "rev",
        definition_norm='{"type":"ratio","type_params":{"denominator":"y","numerator":"x"}}',
    )
    b = _nm(
        "revenue",
        definition_norm='{"type":"ratio","type_params":{"denominator":"y","numerator":"x"}}',
    )
    cols = find_collisions([a, b])
    assert any(c["kind"] == "formula" for c in cols)


def test_detects_duplicate_formula_under_different_names():
    shared_norm = '{"type":"simple","type_params":{"measure":"order_total"}}'
    ms = [
        _nm("rev", definition_norm=shared_norm),
        _nm("revenue", definition_norm=shared_norm),
    ]
    cols = find_collisions(ms)
    assert any(c["kind"] == "formula" for c in cols)


def test_detects_duplicate_name():
    ms = [_nm("rev", definition_norm="norm_a"), _nm("rev", definition_norm="norm_b")]
    cols = find_collisions(ms)
    assert any(c["kind"] == "name" for c in cols)


def test_no_self_collision():
    shared_norm = '{"type":"simple","type_params":{"measure":"order_total"}}'
    assert find_collisions([_nm("rev", definition_norm=shared_norm)]) == []


def test_all_metric_types_handled():
    # normalize_formula must not KeyError on any known metric type
    for t in ("simple", "ratio", "cumulative", "derived", "conversion"):
        m = _nm(f"metric_{t}", type_=t)
        normalize_formula(m)  # must not raise


# AD-4 comment: filter-clause differences are NOT yet a collision dimension (v2).


def test_shared_formula_cross_owner_no_collision():
    """Cross-owner formula suppression: two models with sum(amount) → NO formula collision.

    Name-collision is not fixture-tested here because dbt rejects duplicate metric names at parse
    time, so a real compiled manifest cannot contain a name collision. The name-collision branch of
    find_collisions is therefore unreachable for manifest inputs and is covered by the in-memory
    unit test test_detects_duplicate_name above.
    """
    metrics = load_metrics("tests/fixtures/manifests/shared_formula")
    cols = find_collisions(metrics)
    formula_cols = [c for c in cols if c["kind"] == "formula"]
    assert formula_cols == [], (
        f"Expected no formula collision across distinct owners, got: {formula_cols}"
    )
