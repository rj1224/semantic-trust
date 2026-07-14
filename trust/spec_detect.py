"""Detect which Semantic Layer spec a project uses, and whether the dbt version
supports the latest spec — to route the version-aware validation gate.
Latest spec = dbt Core 1.12+ / Fusion; legacy = 1.6-1.11."""

import json
import os
import re


def dbt_supports_latest(version_str: str) -> bool:
    """Return True iff dbt-core version >= 1.12 (latest/Fusion spec)."""
    m = re.match(r"\s*(\d+)\.(\d+)", version_str or "")
    if not m:
        return False
    major, minor = int(m.group(1)), int(m.group(2))
    return (major, minor) >= (1, 12)


def detect_spec(project_dir: str) -> str:
    """Prefer the compiled semantic_manifest.json (authoritative).

    Latest metrics carry type_params.metric_aggregation_params;
    legacy semantic models carry populated measures lists.

    Returns: "legacy" | "latest" | "unknown"
    """
    path = os.path.join(project_dir, "target", "semantic_manifest.json")
    if not os.path.exists(path):
        return "unknown"
    with open(path, encoding="utf-8") as f:
        m = json.load(f)
    sms = m.get("semantic_models") or []
    mets = m.get("metrics") or []
    if any((sm.get("measures") or []) for sm in sms):
        return "legacy"
    for met in mets:
        tp = met.get("type_params") or {}
        if tp.get("metric_aggregation_params"):
            return "latest"
    return "latest" if sms else "unknown"
