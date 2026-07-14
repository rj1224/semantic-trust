"""
Deterministic trust scorer: context/quality sub-scores + binary gates -> A-F band.
Consumes NormalizedModel + NormalizedMetric (spec-agnostic).

Returns a ModelReport (two-level: model + per-document DocumentReport).
Every Issue carries provenance="deterministic".

Weights and band cutoffs are named constants — linked to spec §7
(docs/superpowers/specs/2026-06-26-datastack-dbt-semantic-authoring-design.md).

Band cutoffs: A≥90 / B≥80 / C≥70 / D≥55 / F (engine values; supersedes v5 spec bands).
"""

from trust.normalized import NormalizedModel, NormalizedMetric
from trust.report import Issue, DocumentReport, ModelReport
from trust.ownership import check_owner
from trust.config import load_config

# --- Named constants (AD-4: hoist weights + cutoffs; link to spec §7) ---
CONTEXT_WEIGHT = 0.60
QUALITY_WEIGHT = 0.40
# Band cutoffs: score >= cutoff -> band label. Ordered descending. F is the fallback.
# Note: these supersede the v5 spec's bands; authoritative values live here.
BAND_CUTOFFS = [(90, "A"), (80, "B"), (70, "C"), (55, "D")]

# Supported metric types (Quality gate checks these).
KNOWN_METRIC_TYPES = {"simple", "ratio", "cumulative", "derived", "conversion"}

# Rules that block the ownership gate (owner is wholly absent or a known placeholder).
# Advisory rules (owner_invalid_email, owner_domain) do NOT block the gate — they are
# appended to ModelReport.issues so callers can act on them without forcing F-band.
_GATE_BLOCKING_RULES: frozenset[str] = frozenset({"owner_missing", "owner_placeholder"})


def _band(score: float) -> str:
    for cut, label in BAND_CUTOFFS:
        if score >= cut:
            return label
    return "F"


def _score_semantic_model_doc(sm: NormalizedModel) -> DocumentReport:
    """
    Per-document breakdown for the semantic_model artifact.

    Mechanical checks: entities present, dimensions present, time dimension present.
    All three required for a structural pass.
    """
    issues: list[Issue] = []
    location = sm.source_file

    checks = [
        (
            bool(sm.entities),
            "structural",
            "entities_present",
            "semantic model must define at least one entity",
            "critical",
        ),
        (
            bool(sm.dimensions),
            "structural",
            "dimensions_present",
            "semantic model must define at least one dimension",
            "critical",
        ),
        (
            sm.has_time_dimension,
            "structural",
            "time_dimension_present",
            "semantic model must include a primary time dimension",
            "critical",
        ),
    ]

    pts = 0
    for passed, dimension, rule, message, severity in checks:
        if passed:
            pts += 1
        else:
            issues.append(
                Issue(
                    severity=severity,
                    dimension=dimension,
                    rule=rule,
                    message=message,
                    location=location,
                )
            )

    mechanical = round(100.0 * pts / len(checks), 1)
    status = "pass" if not issues else "fail"
    return DocumentReport(
        doc_type="semantic_model",
        status=status,
        score=mechanical,
        mechanical=mechanical,
        issues=issues,
    )


def _score_metrics_doc(metrics: list[NormalizedMetric]) -> DocumentReport:
    """
    Per-document breakdown for the metrics artifact.

    Absent when no metrics are provided — returns status="absent", score=None.
    Mechanical checks per metric: has description, type is known, definition_norm non-empty.
    Ownership check: every metric has an owner.
    """
    if not metrics:
        return DocumentReport(
            doc_type="metrics",
            status="absent",
            score=None,
            mechanical=None,
            issues=[],
        )

    issues: list[Issue] = []
    pts, total = 0, 0

    for m in metrics:
        location = m.source_file

        # Description
        total += 1
        if m.description:
            pts += 1
        else:
            issues.append(
                Issue(
                    severity="warning",
                    dimension="completeness",
                    rule="metric_description_missing",
                    message=f"metric '{m.name}' has no description",
                    location=location,
                )
            )

        # Known type
        total += 1
        if m.type in KNOWN_METRIC_TYPES:
            pts += 1
        else:
            issues.append(
                Issue(
                    severity="warning",
                    dimension="completeness",
                    rule="metric_type_unknown",
                    message=f"metric '{m.name}' has unknown type '{m.type}'",
                    location=location,
                )
            )

        # Definition non-empty
        total += 1
        if m.definition_norm:
            pts += 1
        else:
            issues.append(
                Issue(
                    severity="critical",
                    dimension="completeness",
                    rule="metric_definition_empty",
                    message=f"metric '{m.name}' has an empty or missing definition",
                    location=location,
                )
            )

        # Ownership
        total += 1
        if m.owner:
            pts += 1
        else:
            issues.append(
                Issue(
                    severity="warning",
                    dimension="ownership",
                    rule="metric_owner_missing",
                    message=f"metric '{m.name}' missing config.meta.owner",
                    location=location,
                )
            )

    mechanical = round(100.0 * pts / total, 1)
    status = "pass" if not issues else "fail"
    return DocumentReport(
        doc_type="metrics",
        status=status,
        score=mechanical,
        mechanical=mechanical,
        issues=issues,
    )


def _absent_doc(doc_type: str) -> DocumentReport:
    """Canonical absent document — status='absent', score=None, mechanical=None."""
    return DocumentReport(
        doc_type=doc_type,
        status="absent",
        score=None,
        mechanical=None,
        issues=[],
    )


def score_model(
    sm: NormalizedModel,
    metrics: list[NormalizedMetric],
    collisions: list[dict],
    joinability_issues: list | None = None,
    project_dir: str = ".",
) -> ModelReport:
    """
    Score a NormalizedModel + its NormalizedMetrics against the project-wide collisions.
    Returns a ModelReport (two-level: model-level + per-document DocumentReport).

    Gate logic and trust = context×0.6 + quality×0.4 are preserved from Phase 1.
    Band is capped to F when any gate fails.

    joinability_issues: pre-computed list[Issue] from check_joinability(all_models).
      Caller filters the full cross-model list and passes only issues that
      touch this model (i.e. issue.location == sm.source_file).  Pass None
      (default) to skip the joinability gate (backward-compatible).
    """
    model_issues: list[Issue] = []
    location = sm.source_file

    # --- Gates (binary) ---
    structural = bool(sm.entities and sm.has_time_dimension)
    _approved_domains = load_config(project_dir)["approved_email_domains"]

    # Ownership gate: fails only on owner_missing or owner_placeholder (gate-blocking).
    # owner_invalid_email / owner_domain are advisory — they do not block the gate
    # (preserves backward compat with bare team-name owners), but ARE collected and
    # appended to model_issues so callers can surface them. Collect all check_owner
    # results here so advisory issues are not silently discarded.
    _all_owner_issues: list[Issue] = []
    _ownership_gate_failed = False
    for _m in metrics:
        for _issue in check_owner(_m.owner, _approved_domains):
            _all_owner_issues.append(_issue)
            if _issue.rule in _GATE_BLOCKING_RULES:
                _ownership_gate_failed = True
    ownership = bool(metrics) and not _ownership_gate_failed
    completeness = bool(sm.dimensions) and all(m.description for m in metrics)
    metric_names = {m.name for m in metrics}
    uniqueness = not any(
        c["a"] in metric_names or c["b"] in metric_names for c in collisions
    )
    # Joinability gate: True when no joinability Issue touches this model's entities.
    # None (default) means gate is skipped / not evaluated — backward compatible.
    _j_issues = joinability_issues if joinability_issues is not None else []
    joinability = not any(i.location == sm.source_file for i in _j_issues)

    if not structural:
        model_issues.append(
            Issue(
                severity="critical",
                dimension="structural",
                rule="structural_gate_failed",
                message="semantic model needs entities and a primary time dimension",
                location=location,
            )
        )
    if not ownership:
        model_issues.append(
            Issue(
                severity="critical",
                dimension="ownership",
                rule="ownership_gate_failed",
                message="every metric needs config.meta.owner",
                location=location,
            )
        )
    if not completeness:
        model_issues.append(
            Issue(
                severity="warning",
                dimension="completeness",
                rule="completeness_gate_failed",
                message="metrics need descriptions; model needs dimensions",
                location=location,
            )
        )
    if not uniqueness:
        model_issues.append(
            Issue(
                severity="critical",
                dimension="uniqueness",
                rule="uniqueness_gate_failed",
                message="duplicate metric name/formula detected in project",
                location=location,
            )
        )
    if joinability_issues is not None and not joinability:
        model_issues.extend(_j_issues)

    # Append advisory ownership issues (owner_invalid_email, owner_domain) that were
    # NOT gate-blocking. These are surfaced to callers but do not affect the band.
    _advisory_issues = [
        i for i in _all_owner_issues if i.rule not in _GATE_BLOCKING_RULES
    ]
    model_issues.extend(_advisory_issues)

    # --- Sub-scores ---
    # Context: structural richness of the semantic model
    ctx_pts, ctx_total = 0, 0
    ctx_total += 1
    ctx_pts += 1 if sm.entities else 0
    ctx_total += 1
    ctx_pts += 1 if sm.dimensions else 0
    ctx_total += 1
    ctx_pts += 1 if sm.has_time_dimension else 0
    ctx_total += 1
    ctx_pts += 1 if all(m.description for m in metrics) else 0
    context = 100.0 * ctx_pts / ctx_total if ctx_total else 0.0

    # Quality: metric definition well-formedness
    q_pts, q_total = 0, 0
    for m in metrics:
        q_total += 2
        q_pts += 1 if m.type in KNOWN_METRIC_TYPES else 0
        q_pts += 1 if m.definition_norm else 0
    quality = 100.0 * q_pts / q_total if q_total else 0.0

    trust_score = context * CONTEXT_WEIGHT + quality * QUALITY_WEIGHT

    gates = {
        "structural": structural,
        "ownership": ownership,
        "completeness": completeness,
        "uniqueness": uniqueness,
        "joinability": joinability,
    }
    band = _band(trust_score) if all(gates.values()) else "F"

    # --- Per-document breakdown ---
    documents: dict[str, DocumentReport] = {
        "semantic_model": _score_semantic_model_doc(sm),
        "metrics": _score_metrics_doc(metrics),
        # dbt_docs and few_shot are always absent at this layer (no artifact yet)
        "dbt_docs": _absent_doc("dbt_docs"),
        "few_shot": _absent_doc("few_shot"),
    }

    return ModelReport(
        model=sm,
        compile_ok=True,
        gates=gates,
        trust_score=round(trust_score, 1),
        band=band,
        context=round(context, 1),
        quality=round(quality, 1),
        documents=documents,
        issues=model_issues,
        warnings=[],
        unattributed_metrics=0,
    )
