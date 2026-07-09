# tests/test_joinability.py
from trust.manifest_loader import load_models, load_metrics
from trust.joinability import check_joinability
from trust.uniqueness import find_collisions
from trust.scorer import score_model


def test_parity_mismatch_flagged():
    models = load_models("tests/fixtures/manifests/joinbreak")
    issues = check_joinability(models)
    assert any(i.rule == "joinability_parity" for i in issues)


def test_clean_project_no_joinability_issues():
    models = load_models("tests/fixtures/manifests/single_latest")
    assert check_joinability(models) == []


def test_orphan_or_parity_entity_flagged():
    models = load_models("tests/fixtures/manifests/joinbreak")
    issues = check_joinability(models)
    assert any(i.rule == "joinability_orphan" for i in issues)
    assert any(i.rule == "joinability_parity" for i in issues)


def test_joinability_issues_have_correct_fields():
    models = load_models("tests/fixtures/manifests/joinbreak")
    issues = check_joinability(models)
    for issue in issues:
        assert issue.severity == "warning"
        assert issue.provenance == "deterministic"
        assert issue.rule in {"joinability_parity", "joinability_orphan"}
        assert issue.location


def test_joinability_gate_wired_into_scorer():
    models = load_models("tests/fixtures/manifests/joinbreak")
    j_issues = check_joinability(models)
    sm = next(m for m in models if m.name == "fct_orders")
    model_j_issues = [i for i in j_issues if i.location == sm.source_file]
    metrics = load_metrics("tests/fixtures/manifests/joinbreak")
    model_metrics = [m for m in metrics if m.owner_model == sm.name]
    collisions = find_collisions(metrics)
    rep = score_model(sm, model_metrics, collisions, joinability_issues=model_j_issues)
    assert "joinability" in rep.gates
    assert rep.gates["joinability"] is False
    assert rep.band == "F"


def test_clean_project_joinability_gate_passes():
    models = load_models("tests/fixtures/manifests/single_latest")
    j_issues = check_joinability(models)
    assert j_issues == []
    sm = next(m for m in models if m.name == "fct_orders")
    metrics = load_metrics("tests/fixtures/manifests/single_latest")
    model_metrics = [m for m in metrics if m.owner_model == sm.name]
    collisions = find_collisions(metrics)
    rep = score_model(sm, model_metrics, collisions, joinability_issues=j_issues)
    assert rep.gates["joinability"] is True
