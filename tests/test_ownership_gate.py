# tests/test_ownership_gate.py
from trust.manifest_loader import load_models, load_metrics
from trust.joinability import check_joinability
from trust.uniqueness import find_collisions
from trust.scorer import score_model


def test_no_owner_fails_ownership_gate_and_bands_F():
    """A metric with no owner fails ownership gate → band F."""
    models = load_models("tests/fixtures/manifests/no_owner")
    metrics = load_metrics("tests/fixtures/manifests/no_owner")
    sm = next(m for m in models if m.name == "fct_events")
    model_metrics = [m for m in metrics if m.owner_model == sm.name]
    j_issues = check_joinability(models)
    cols = find_collisions(metrics)
    rep = score_model(sm, model_metrics, cols, joinability_issues=j_issues)
    assert rep.gates["ownership"] is False
    assert rep.band == "F"
