"""
Tests for trust.ownership.check_owner — covers the fixed placeholder regex
and domain allowlist logic.
"""

from trust.ownership import check_owner


# ── Core spec tests (from task brief) ──────────────────────────────────────


def test_valid_email_with_hyphen_digits_is_accepted():
    """cp-da-1@example.com must NOT be rejected as a placeholder (prior regex bug)."""
    assert check_owner("cp-da-1@example.com", ["example.com"]) == []


def test_missing_owner_flagged():
    assert any(i.rule == "owner_missing" for i in check_owner("", []))


def test_none_owner_flagged():
    assert any(i.rule == "owner_missing" for i in check_owner(None, []))


def test_domain_enforced_only_when_allowlist_present():
    assert check_owner("x@other.com", []) == []  # no allowlist → pass
    assert any(
        i.rule == "owner_domain" for i in check_owner("x@other.com", ["example.com"])
    )


# ── Placeholder detection ────────────────────────────────────────────────


def test_placeholder_owner_flagged():
    assert any(i.rule == "owner_placeholder" for i in check_owner("owner", []))


def test_tbd_owner_flagged():
    assert any(i.rule == "owner_placeholder" for i in check_owner("tbd", []))


def test_todo_owner_flagged():
    assert any(i.rule == "owner_placeholder" for i in check_owner("todo", []))


def test_unknown_owner_flagged():
    assert any(i.rule == "owner_placeholder" for i in check_owner("unknown", []))


def test_placeholder_case_insensitive():
    assert any(i.rule == "owner_placeholder" for i in check_owner("PLACEHOLDER", []))
    assert any(i.rule == "owner_placeholder" for i in check_owner("TBD", []))


def test_non_placeholder_hyphenated_not_rejected():
    """Emails with hyphens and digits in local-part are valid, not placeholders."""
    assert check_owner("data-team-1@corp.io", ["corp.io"]) == []
    assert check_owner("cp-da-1@example.com", []) == []


# ── Invalid email format ─────────────────────────────────────────────────


def test_bare_string_not_email_flagged():
    """A non-email string (no @) that isn't a recognised placeholder -> invalid email."""
    issues = check_owner("not-an-email", [])
    assert any(i.rule == "owner_invalid_email" for i in issues)


def test_valid_email_format_accepted():
    assert check_owner("team@example.com", []) == []


# ── Domain check ────────────────────────────────────────────────────────


def test_domain_in_allowlist_accepted():
    assert check_owner("user@allowed.com", ["allowed.com"]) == []


def test_domain_not_in_allowlist_flagged():
    issues = check_owner("user@other.com", ["allowed.com"])
    assert any(i.rule == "owner_domain" for i in issues)


def test_multiple_domains_in_allowlist():
    assert check_owner("user@second.com", ["first.com", "second.com"]) == []


# ── Advisory issues must surface in ModelReport (regression guard) ──────────


def test_score_model_surfaces_advisory_owner_domain_issue(tmp_path):
    """
    score_model must append advisory owner_domain issues to ModelReport.issues
    even though they don't block the ownership gate.

    Prior bug: check_owner results were only used to compute the gate boolean;
    non-blocking advisory issues were silently discarded.
    """
    import json
    from trust.scorer import score_model
    from trust.normalized import NormalizedModel, NormalizedMetric

    # Write a config that restricts to corp.io — otherdomain.com will trigger owner_domain
    (tmp_path / ".semantic-trust.json").write_text(
        json.dumps({"approved_email_domains": ["corp.io"]})
    )

    sm = NormalizedModel(
        name="test_model",
        source_file="test_model.yml",
        spec="latest",
        entities=[{"name": "id", "type": "primary"}],
        dimensions=[{"name": "created_at", "type": "time", "is_time": True}],
        measures=[],
        has_time_dimension=True,
    )
    metric = NormalizedMetric(
        name="test_metric",
        owner_model="test_model",
        source_file="test_metric.yml",
        description="a metric",
        type="simple",
        definition_norm="measure: revenue",
        owner="user@otherdomain.com",
    )
    rep = score_model(sm, [metric], collisions=[], project_dir=str(tmp_path))

    # Gate must still pass (advisory-not-blocking semantics preserved)
    assert rep.gates["ownership"] is True, (
        "owner_domain must NOT block the ownership gate"
    )

    # Advisory issue must appear in ModelReport.issues
    assert _has_advisory(rep, "owner_domain"), (
        f"owner_domain advisory issue not found in ModelReport.issues; "
        f"got rules: {[i.rule for i in rep.issues]}"
    )


def _has_advisory(rep, rule: str) -> bool:
    """Helper: check ModelReport issues list for a given rule name."""
    return any(i.rule == rule for i in rep.issues)


def test_score_model_surfaces_advisory_owner_invalid_email_issue():
    """
    A bare team-name owner (non-email) emits owner_invalid_email advisory
    and must appear in ModelReport.issues without blocking the gate.
    """
    from trust.scorer import score_model
    from trust.normalized import NormalizedModel, NormalizedMetric

    sm = NormalizedModel(
        name="test_model2",
        source_file="test_model2.yml",
        spec="latest",
        entities=[{"name": "id", "type": "primary"}],
        dimensions=[{"name": "created_at", "type": "time", "is_time": True}],
        measures=[],
        has_time_dimension=True,
    )
    metric = NormalizedMetric(
        name="test_metric2",
        owner_model="test_model2",
        source_file="test_metric2.yml",
        description="a metric",
        type="simple",
        definition_norm="measure: revenue",
        owner="data-team",  # bare team name: advisory owner_invalid_email
    )
    rep = score_model(sm, [metric], collisions=[], project_dir=".")

    assert rep.gates["ownership"] is True, (
        "owner_invalid_email must NOT block the ownership gate"
    )
    assert any(i.rule == "owner_invalid_email" for i in rep.issues), (
        f"owner_invalid_email advisory not in ModelReport.issues; got: {[i.rule for i in rep.issues]}"
    )
