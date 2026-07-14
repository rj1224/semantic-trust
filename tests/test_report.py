# tests/test_report.py
from trust.manifest_loader import load_models, load_metrics
from trust.uniqueness import find_collisions
from trust.scorer import score_model

FIX = "tests/fixtures/manifests/qcommerce_latest"


def test_report_has_model_and_per_document_levels():
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    metrics = load_metrics(FIX)
    rep = score_model(
        sm, [m for m in metrics if m.owner_model == "orders"], find_collisions(metrics)
    )
    d = rep.to_dict()
    # model level
    assert d["trust_score"] >= 0 and d["band"] in {"A", "B", "C", "D", "F"}
    assert set(d["gates"]) >= {"structural", "ownership", "completeness", "uniqueness"}
    # per-document level
    assert "semantic_model" in d["documents"] and "metrics" in d["documents"]
    assert d["documents"]["metrics"]["status"] in {"pass", "fail", "absent"}
    # provenance on every issue
    assert all(
        i["provenance"] == "deterministic"
        for doc in d["documents"].values()
        for i in doc["issues"]
    )


def test_absent_docs_are_absent_not_zero():
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    rep = score_model(sm, [], [])
    # few_shot/dbt_docs not present in this fixture → status absent, score None (not 0)
    assert (
        rep.documents["few_shot"].status == "absent"
        and rep.documents["few_shot"].score is None
    )


def test_model_report_has_trust_score_field():
    """ModelReport must expose trust_score (not 'score') at the model level."""
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    metrics = load_metrics(FIX)
    rep = score_model(
        sm, [m for m in metrics if m.owner_model == "orders"], find_collisions(metrics)
    )
    d = rep.to_dict()
    assert "trust_score" in d
    assert 0.0 <= d["trust_score"] <= 100.0


def test_document_report_mechanical_score_is_float_or_none():
    """DocumentReport.mechanical is a float in [0,100] for present docs, None for absent."""
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    metrics = load_metrics(FIX)
    rep = score_model(
        sm, [m for m in metrics if m.owner_model == "orders"], find_collisions(metrics)
    )
    d = rep.to_dict()
    for doc_type, doc in d["documents"].items():
        if doc["status"] == "absent":
            assert doc["mechanical"] is None, (
                f"{doc_type} should have mechanical=None when absent"
            )
        else:
            assert isinstance(doc["mechanical"], float), (
                f"{doc_type} mechanical should be float"
            )
            assert 0.0 <= doc["mechanical"] <= 100.0


def test_issues_have_all_required_fields():
    """Every Issue must carry severity, dimension, rule, message, location, provenance."""
    # Force some issues by omitting entities
    from trust.normalized import NormalizedModel

    bad_sm = NormalizedModel(
        name="orders",
        source_file="orders.yml",
        spec="latest",
        entities=[],  # triggers structural issue
        dimensions=[{"name": "ordered_at", "type": "time", "is_time": True}],
        measures=[],
        has_time_dimension=True,
    )
    rep = score_model(bad_sm, [], [])
    d = rep.to_dict()
    all_issues = [i for doc in d["documents"].values() for i in doc["issues"]]
    if all_issues:
        required = {
            "severity",
            "dimension",
            "rule",
            "message",
            "location",
            "provenance",
        }
        for issue in all_issues:
            assert required <= set(issue.keys()), f"Issue missing fields: {issue}"


def test_dbt_docs_absent_when_no_artifact():
    """dbt_docs doc type is absent (not zero) when no dbt docs content in fixture."""
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    metrics = load_metrics(FIX)
    rep = score_model(
        sm, [m for m in metrics if m.owner_model == "orders"], find_collisions(metrics)
    )
    assert rep.documents["dbt_docs"].status == "absent"
    assert rep.documents["dbt_docs"].score is None
