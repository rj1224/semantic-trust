"""
Report dataclasses for the two-level deterministic trust output (Task 3.1a).

Two levels:
  - DocumentReport: per-artifact breakdown (semantic_model, metrics, dbt_docs, few_shot).
  - ModelReport: model-level aggregation with per-document dict + provenance-tagged issues.

Band cutoffs: A≥90 / B≥80 / C≥70 / D≥55 / F (engine values; supersedes v5 spec bands).
All issues carry provenance="deterministic" — no LLM involvement at this layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Issue:
    """A single finding from a deterministic check."""

    severity: str  # "critical" | "warning" | "info"
    dimension: str  # e.g. "structural", "completeness", "uniqueness"
    rule: str  # machine-readable rule identifier
    message: str  # human-readable message
    location: str  # source_file or "<model>" etc.
    provenance: str = "deterministic"

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "dimension": self.dimension,
            "rule": self.rule,
            "message": self.message,
            "location": self.location,
            "provenance": self.provenance,
        }


@dataclass
class DocumentReport:
    """
    Per-artifact quality breakdown.

    doc_type:         "semantic_model" | "metrics" | "dbt_docs" | "few_shot"
    status:           "pass" | "fail" | "absent"
    score:            0-100 float when present; None when absent (never fabricate 0 for missing artifact)
    mechanical:       raw mechanical ratio (0-100) before gate application; None when absent
    issues:           provenance-tagged findings for this artifact
    document_quality: advisory LLM quality score (0-100); None until apply_judgment() attaches it.
                      Separate from the deterministic score — never blended into trust_score.
    """

    doc_type: str
    status: str
    score: Optional[float]
    mechanical: Optional[float]
    issues: list[Issue] = field(default_factory=list)
    document_quality: Optional[int] = field(default=None)

    def to_dict(self) -> dict:
        d = {
            "doc_type": self.doc_type,
            "status": self.status,
            "score": self.score,
            "mechanical": self.mechanical,
            "issues": [i.to_dict() for i in self.issues],
        }
        if self.document_quality is not None:
            d["document_quality"] = self.document_quality
        return d


@dataclass
class ModelReport:
    """
    Two-level trust report for a single semantic model.

    trust_score:        weighted composite (context×0.6 + quality×0.4), 0-100
    band:               A/B/C/D/F; capped to F when any gate fails
    context:            context sub-score (0-100)
    quality:            quality sub-score (0-100)
    gates:              binary gate dict {"structural","ownership","completeness","uniqueness"}
    documents:          per-artifact DocumentReport keyed by doc_type
    issues:             model-level issues (gate failures, cross-doc findings)
    warnings:           non-blocking advisory strings (e.g. unattributed metrics)
    unattributed_metrics: count of metrics with no owning model across the project
    compile_ok:         placeholder for future compile-gate; always True at this layer
    model:              the NormalizedModel that was scored
    """

    model: object
    compile_ok: bool
    gates: dict[str, bool]
    trust_score: float
    band: str
    context: float
    quality: float
    documents: dict[str, DocumentReport]
    issues: list[Issue]
    warnings: list[str]
    unattributed_metrics: int

    def to_dict(self) -> dict:
        return {
            "model": self.model.name
            if hasattr(self.model, "name")
            else str(self.model),
            "compile_ok": self.compile_ok,
            "gates": self.gates,
            "trust_score": self.trust_score,
            "band": self.band,
            "context": self.context,
            "quality": self.quality,
            "documents": {k: v.to_dict() for k, v in self.documents.items()},
            "issues": [i.to_dict() for i in self.issues],
            "warnings": self.warnings,
            "unattributed_metrics": self.unattributed_metrics,
        }
