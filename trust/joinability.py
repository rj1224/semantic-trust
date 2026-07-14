"""
Cross-model joinability gate [J] (Task 3.1b).

Produces Issue(severity="warning", provenance="deterministic") for:
  - joinability_orphan : an entity name appears on exactly one model
                         (cannot participate in a join).
  - joinability_parity : the same *conceptual* join partner resolves to
                         different entity names across models — detected
                         when entity names share a common stem but differ
                         in suffix (e.g. "customer" vs "customer_id") while
                         being used as join-compatible types (primary/foreign).

Orphan detection strategy
--------------------------
We implement the orphan check directly over NormalizedModel.entities dicts
({name, type}) — the equivalent of MetricFlow's CommonEntitysRule algorithm
but without the overhead of building MetricFlow's internal object graph.

Parity detection strategy
--------------------------
MetricFlow has no built-in cross-model name-parity check.  We implement it:
  1. Normalise each entity name to a *stem* (strip trailing `_id`, `_key`).
  2. Group entity names by stem across all models.
  3. When a stem maps to more than one distinct entity name, the names
     are mismatched join-partner candidates — flag joinability_parity.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from trust.report import Issue

if TYPE_CHECKING:
    pass

# Types that represent "one end" of a join (primary key side).
_PRIMARY_TYPES = {"primary", "natural"}
# Types that reference the primary side (foreign key side).
_FOREIGN_TYPES = {"foreign"}
# Both sides together — entities of other types (e.g. "unique") are skipped.
_JOIN_TYPES = _PRIMARY_TYPES | _FOREIGN_TYPES


def _stem(name: str) -> str:
    """Normalise an entity name to a stem by stripping common id-suffix patterns."""
    for suffix in ("_id", "_key", "_ref"):
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _orphan_issues(models: list) -> list[Issue]:
    """
    Flag entity names that appear on exactly one model.

    Logic mirrors CommonEntitysRule._map_semantic_model_entities but operates
    on NormalizedModel.entities dicts ({name, type}) instead of MetricFlow's
    internal Entity/SemanticModel objects.
    """
    # Map entity_name -> set of model names that declare it.
    entity_to_models: dict[str, set[str]] = defaultdict(set)

    for model in models:
        for e in model.entities or []:
            name = e.get("name", "")
            if not name:
                continue
            entity_to_models[name].add(model.name)

    # With only one model in the project there can be no join partners at all —
    # every entity is "orphaned" by definition.  Skip the check; it is
    # vacuously true and produces false positives on single-model projects.
    if len(models) < 2:
        return []

    issues: list[Issue] = []

    # Second pass — emit one Issue per (entity_name, model) pair that is orphaned.
    for model in models:
        for e in model.entities or []:
            name = e.get("name", "")
            if not name:
                continue
            if len(entity_to_models[name]) == 1:
                issues.append(
                    Issue(
                        severity="warning",
                        dimension="joinability",
                        rule="joinability_orphan",
                        message=(
                            f"Entity '{name}' on model '{model.name}' "
                            f"appears on no other model — it cannot "
                            f"participate in a join."
                        ),
                        location=model.source_file,
                        provenance="deterministic",
                    )
                )

    return issues


def _parity_issues(models: list) -> list[Issue]:
    """
    Flag entity name/stem mismatches that indicate broken join partners.

    Groups entity names by their normalised stem across all models.  When a
    stem maps to multiple distinct names, those names are mismatched join
    candidates — e.g. "customer" (primary) and "customer_id" (foreign)
    both stem to "customer" but differ in name, breaking MetricFlow joins.

    MetricFlow has no built-in rule for this — entirely our check.
    """
    # stem -> set of (entity_name, model_name, source_file, entity_type)
    stem_map: dict[str, list[dict]] = defaultdict(list)

    for model in models:
        for e in model.entities or []:
            name = e.get("name", "")
            etype = e.get("type", "")
            if not name or etype not in _JOIN_TYPES:
                continue
            s = _stem(name)
            stem_map[s].append(
                {
                    "name": name,
                    "type": etype,
                    "model": model.name,
                    "source_file": model.source_file,
                }
            )

    issues: list[Issue] = []

    for stem, entries in stem_map.items():
        distinct_names = {e["name"] for e in entries}
        if len(distinct_names) <= 1:
            continue  # all consistent — no mismatch

        # Multiple distinct names for the same stem across models: parity mismatch.
        names_str = ", ".join(sorted(distinct_names))
        models_str = ", ".join(sorted({e["model"] for e in entries}))

        # Emit one Issue per model that contributes a mismatched name.
        seen_model_name = set()
        for entry in entries:
            if entry["model"] in seen_model_name:
                continue
            seen_model_name.add(entry["model"])
            issues.append(
                Issue(
                    severity="warning",
                    dimension="joinability",
                    rule="joinability_parity",
                    message=(
                        f"Entity stem '{stem}' has mismatched names "
                        f"across models [{models_str}]: [{names_str}]. "
                        f"MetricFlow joins require exact name match — "
                        f"these will not join correctly."
                    ),
                    location=entry["source_file"],
                    provenance="deterministic",
                )
            )

    return issues


def check_joinability(models: list) -> list[Issue]:
    """
    Cross-model joinability check.  Consumes all NormalizedModels for the project.

    Returns:
      list[Issue] — empty means fully joinable.

    Checks performed:
      1. Orphan entities (joinability_orphan) — entity on only one model.
         Implements the equivalent of MetricFlow's CommonEntitysRule algorithm
         directly over NormalizedModel.entities.
      2. Name/type parity mismatches (joinability_parity) — same conceptual
         join partner has different entity names across models.
         MetricFlow has no built-in rule for this; we build it ourselves.
    """
    if not models:
        return []

    issues: list[Issue] = []
    issues.extend(_orphan_issues(models))
    issues.extend(_parity_issues(models))
    return issues
