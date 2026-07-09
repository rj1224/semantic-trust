"""
Tests for trust/judgment.py — judgment combination + guardrail (Task 3.1d).

Guardrail contract:
  apply_judgment() accepts the deterministic ModelReport (read-only) and an LLM
  judgment payload (per judge.md) and returns a NEW ModelReport that:
    - adds document_quality per DocumentReport (from judgment["documents"])
    - appends provenance="llm_judge" advisory issues per DocumentReport
    - NEVER changes trust_score, band, gates, context, quality, or any
      provenance="deterministic" issue regardless of what the payload contains
"""
from trust.scorer import score_model
from trust.manifest_loader import load_models, load_metrics
from trust.uniqueness import find_collisions
from trust.judgment import apply_judgment


def _report():
    FIX = "tests/fixtures/manifests/qcommerce_latest"
    sm = next(m for m in load_models(FIX) if m.name == "orders")
    ms = load_metrics(FIX)
    return score_model(sm, [m for m in ms if m.owner_model == "orders"], find_collisions(ms))


def test_judgment_adds_quality_without_touching_trust():
    base = _report()
    before = (base.trust_score, base.band, dict(base.gates))
    out = apply_judgment(base, {"documents": {"metrics": {"quality": 62, "issues": [
        {"severity": "warning", "dimension": "data_context", "rule": "description_business_meaning",
         "message": "restates the formula", "location": "metrics[0].description"}]}}})
    assert (out.trust_score, out.band, dict(out.gates)) == before          # deterministic untouched
    assert out.documents["metrics"].to_dict().get("document_quality") == 62
    assert any(i["provenance"] == "llm_judge" for i in out.documents["metrics"].to_dict()["issues"])


def test_judgment_cannot_flip_a_gate():
    base = _report()
    out = apply_judgment(base, {"override_gates": {"uniqueness": False}, "documents": {}})  # malicious payload
    assert out.gates == base.gates                                          # ignored


def test_judgment_does_not_mutate_base_report():
    """apply_judgment must return a new object; the original is unchanged."""
    base = _report()
    base_trust = base.trust_score
    base_metrics_issues_count = len(base.documents["metrics"].issues)
    apply_judgment(base, {"documents": {"metrics": {"quality": 50, "issues": [
        {"severity": "info", "dimension": "data_context", "rule": "some_rule",
         "message": "advisory note", "location": "metrics[0]"}]}}})
    assert base.trust_score == base_trust
    assert len(base.documents["metrics"].issues) == base_metrics_issues_count


def test_judgment_no_documents_key_is_safe():
    """Payload with no 'documents' key must not raise — treat as empty."""
    base = _report()
    out = apply_judgment(base, {})
    assert out.trust_score == base.trust_score
    assert out.band == base.band


def test_judgment_unknown_doc_key_ignored():
    """LLM referencing a non-existent document name must not raise or corrupt."""
    base = _report()
    out = apply_judgment(base, {"documents": {"nonexistent_doc": {"quality": 99, "issues": []}}})
    assert out.trust_score == base.trust_score
    # known documents unchanged
    for key in base.documents:
        assert out.documents[key].to_dict().get("document_quality") is None


def test_judgment_deterministic_issues_provenance_unchanged():
    """Deterministic issues on the base report keep provenance='deterministic' after apply_judgment."""
    base = _report()
    # inject a synthetic deterministic issue onto the base (simulate scorer output)
    from trust.report import Issue
    synth = Issue(severity="warning", dimension="completeness", rule="test_rule",
                  message="test", location="x.yml", provenance="deterministic")
    base.issues.append(synth)
    out = apply_judgment(base, {"documents": {}})
    det_issues = [i for i in out.issues if i.provenance == "deterministic"]
    assert any(i.rule == "test_rule" for i in det_issues)


def test_quality_clamped_above_100():
    """LLM emitting quality > 100 must be clamped to 100."""
    base = _report()
    out = apply_judgment(base, {"documents": {"metrics": {"quality": 150, "issues": []}}})
    assert out.documents["metrics"].document_quality == 100


def test_quality_clamped_below_0():
    """LLM emitting negative quality must be clamped to 0."""
    base = _report()
    out = apply_judgment(base, {"documents": {"metrics": {"quality": -50, "issues": []}}})
    assert out.documents["metrics"].document_quality == 0


def test_quality_none_leaves_document_quality_unset():
    """Missing quality key must not crash and must leave document_quality as None."""
    base = _report()
    out = apply_judgment(base, {"documents": {"metrics": {"issues": []}}})
    assert out.documents["metrics"].document_quality is None


def test_quality_non_int_leaves_document_quality_unset():
    """Non-int/unconvertible quality must not crash; document_quality stays None."""
    base = _report()
    out = apply_judgment(base, {"documents": {"metrics": {"quality": "bad_value", "issues": []}}})
    assert out.documents["metrics"].document_quality is None


def test_deterministic_provenance_on_doc_issue_retained_after_llm_append():
    """A deterministic issue on a DocumentReport retains its provenance after apply_judgment
    appends an llm_judge issue to the same document (deep-copy guarantee)."""
    from trust.report import Issue
    base = _report()
    det_issue = Issue(severity="warning", dimension="completeness", rule="det_rule",
                      message="deterministic", location="metrics.yml", provenance="deterministic")
    base.documents["metrics"].issues.append(det_issue)
    out = apply_judgment(base, {"documents": {"metrics": {"quality": 70, "issues": [
        {"severity": "info", "dimension": "data_context", "rule": "llm_rule",
         "message": "advisory", "location": "metrics[0]"}]}}})
    doc_issues = out.documents["metrics"].issues
    det_issues = [i for i in doc_issues if i.provenance == "deterministic"]
    llm_issues = [i for i in doc_issues if i.provenance == "llm_judge"]
    assert any(i.rule == "det_rule" for i in det_issues), "deterministic issue lost"
    assert any(i.rule == "llm_rule" for i in llm_issues), "llm_judge issue missing"
