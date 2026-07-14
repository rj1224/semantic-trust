# tests/test_scorer.py
# score_model now returns a ModelReport (not a dict) — use attribute access.
# to_dict() is tested in test_report.py; here we test the scorer logic via attributes.
from trust.normalized import NormalizedModel, NormalizedMetric
from trust.scorer import score_model

GOOD_SM = NormalizedModel(
    name="orders",
    source_file="orders.yml",
    spec="legacy",
    entities=[{"name": "order_id", "type": "primary"}],
    dimensions=[
        {"name": "ordered_at", "type": "time", "is_time": True},
        {"name": "status", "type": "categorical", "is_time": False},
    ],
    measures=[{"name": "order_total", "agg": "sum", "expr": "amount"}],
    has_time_dimension=True,
)
GOOD_METRIC = NormalizedMetric(
    name="qcommerce_total_revenue",
    type="simple",
    definition_norm='{"type":"simple","type_params":{"measure":"order_total"}}',
    description="Sum of all order amounts.",
    owner="data-team",
    source_file="orders.yml",
)


def test_well_documented_model_scores_A():
    r = score_model(GOOD_SM, [GOOD_METRIC], [])
    assert r.band == "A" and all(r.gates.values())


def test_missing_owner_fails_ownership_gate_caps_F():
    m = NormalizedMetric(
        name=GOOD_METRIC.name,
        type=GOOD_METRIC.type,
        definition_norm=GOOD_METRIC.definition_norm,
        description=GOOD_METRIC.description,
        owner=None,
        source_file=GOOD_METRIC.source_file,
    )
    r = score_model(GOOD_SM, [m], [])
    assert r.gates["ownership"] is False and r.band == "F"


def test_missing_description_fails_completeness_gate():
    m = NormalizedMetric(
        name=GOOD_METRIC.name,
        type=GOOD_METRIC.type,
        definition_norm=GOOD_METRIC.definition_norm,
        description="",
        owner=GOOD_METRIC.owner,
        source_file=GOOD_METRIC.source_file,
    )
    r = score_model(GOOD_SM, [m], [])
    assert r.gates["completeness"] is False and r.band == "F"


def test_missing_time_dimension_fails_structural_gate():
    sm_no_time = NormalizedModel(
        name="orders",
        source_file="orders.yml",
        spec="legacy",
        entities=[{"name": "order_id", "type": "primary"}],
        dimensions=[{"name": "status", "type": "categorical", "is_time": False}],
        measures=[{"name": "order_total", "agg": "sum", "expr": "amount"}],
        has_time_dimension=False,
    )
    r = score_model(sm_no_time, [GOOD_METRIC], [])
    assert r.gates["structural"] is False and r.band == "F"


def test_uniqueness_collision_fails_gate():
    col = [{"kind": "formula", "a": "qcommerce_total_revenue", "b": "rev", "files": []}]
    r = score_model(GOOD_SM, [GOOD_METRIC], col)
    assert r.gates["uniqueness"] is False and r.band == "F"


def test_latest_spec_model_scores_same_as_legacy():
    # scorer is spec-agnostic: NormalizedModel with spec="latest" scores identically.
    sm_latest = NormalizedModel(
        name="orders",
        source_file="orders.yml",
        spec="latest",
        entities=GOOD_SM.entities,
        dimensions=GOOD_SM.dimensions,
        measures=GOOD_SM.measures,
        has_time_dimension=True,
    )
    r = score_model(sm_latest, [GOOD_METRIC], [])
    assert r.band == "A"
