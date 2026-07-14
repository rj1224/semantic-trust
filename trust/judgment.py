"""
Judgment combination + guardrail (Task 3.1d).

apply_judgment(report: ModelReport, judgment: dict) -> ModelReport

Takes the deterministic ModelReport (read-only) produced by scorer.py and an LLM
judgment payload (per eval/judge.md Step 6) and returns a NEW ModelReport that:
  - adds document_quality per DocumentReport for each key in judgment["documents"]
  - appends provenance="llm_judge" advisory issues to the matching DocumentReport

GUARDRAIL — the function enforces a strict read-only contract on the deterministic
output.  Any key in the payload that would touch trust_score, band, gates, context,
quality, or any provenance="deterministic" issue is silently ignored.  Only
"documents" is read; everything else (e.g. "override_gates") is ignored.

Two distinct scores stay distinct:
  - trust_score / band  : deterministic (unchanged)
  - document_quality    : advisory, per DocumentReport (from judgment)
"""

from __future__ import annotations

import copy
from typing import Any

from trust.report import DocumentReport, Issue, ModelReport


def apply_judgment(report: ModelReport, judgment: dict[str, Any]) -> ModelReport:
    """
    Combine a deterministic ModelReport with an LLM judgment payload.

    Parameters
    ----------
    report:
        The deterministic ModelReport from score_model().  Treated as read-only;
        the caller's object is never mutated.
    judgment:
        Dict produced by the LLM following eval/judge.md Step 6.  Only the
        "documents" key is consumed; all other keys are ignored (guardrail).

        Expected shape::

            {
              "documents": {
                "<doc_type>": {
                  "quality": <int 0-100>,
                  "issues": [
                    {
                      "severity": "warning"|"info"|"critical",
                      "dimension": "<string>",
                      "rule":      "<string>",
                      "message":   "<string>",
                      "location":  "<string>"
                    },
                    ...
                  ]
                },
                ...
              }
            }

    Returns
    -------
    ModelReport
        A deep copy of the input report with document_quality and llm_judge issues
        attached to the relevant DocumentReports.  trust_score, band, gates, context,
        quality, and all deterministic issues are identical to the input.
    """
    # Deep-copy so the caller's report is never mutated (guardrail: immutability)
    new_report: ModelReport = copy.deepcopy(report)

    # GUARDRAIL: only read "documents"; ignore everything else in judgment
    doc_judgments: dict[str, Any] = judgment.get("documents", {})

    for doc_type, payload in doc_judgments.items():
        if doc_type not in new_report.documents:
            # Unknown doc_type from LLM — silently ignore
            continue

        doc: DocumentReport = new_report.documents[doc_type]

        # Attach advisory document_quality score (separate from deterministic score)
        # Clamp to [0, 100]; skip gracefully if quality is absent or not convertible.
        quality_score = payload.get("quality")
        if quality_score is not None:
            try:
                doc.document_quality = max(0, min(100, int(quality_score)))
            except (ValueError, TypeError):
                pass  # non-int/None — leave document_quality unset

        # Append llm_judge advisory issues (tagged provenance="llm_judge")
        for raw in payload.get("issues", []):
            doc.issues.append(
                Issue(
                    severity=raw.get("severity", "info"),
                    dimension=raw.get("dimension", ""),
                    rule=raw.get("rule", ""),
                    message=raw.get("message", ""),
                    location=raw.get("location", ""),
                    provenance="llm_judge",
                )
            )

    return new_report
