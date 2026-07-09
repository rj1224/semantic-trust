"""
Within-project metric uniqueness gate.
Operates on NormalizedMetric (spec-agnostic) from trust.manifest_loader.

definition_norm is computed by trust.manifest_loader from the compiled dbt manifest
at load time — no circular import remains. This module only consumes pre-computed
NormalizedMetric instances; it does not parse raw YAML dicts.

Note: filter-clause differences are NOT yet a uniqueness dimension (v2).
"""
from trust.normalized import NormalizedMetric


def normalize_formula(metric: NormalizedMetric) -> str:
    """
    Return the pre-computed definition_norm already stored on the metric.
    The loader computed this at parse time (spec-agnostic). Exposed here as a
    stable public API so the scorer and harness can call it uniformly.
    """
    return metric.definition_norm


def find_collisions(metrics: list) -> list:
    """
    Detect name duplicates and formula duplicates across a list of NormalizedMetric.
    Returns list[dict{kind, a, b, files}].
    Self-collision: a metric is never compared against itself (by object identity).
    Two distinct entries with the same name in the same file ARE a name collision.
    """
    cols, by_name, by_formula = [], {}, {}
    for m in metrics:
        name_key = (m.name or "").lower()
        # Name collision — guard by object identity, not content equality
        if name_key in by_name and by_name[name_key] is not m:
            cols.append({
                "kind": "name",
                "a": by_name[name_key].name, "b": m.name,
                "files": [by_name[name_key].source_file, m.source_file],
            })
        by_name.setdefault(name_key, m)
        # Formula collision. Two metrics with an identical normalized formula are
        # NOT duplicates if they are owned by DIFFERENT models — e.g. two latest
        # simple metrics that each `sum(amount)` over their own table. A formula
        # collision is only real within the same owning model, or when at least
        # one side is unowned (owner_model=None: a cross-model/orphan metric whose
        # formula coincides with another's is genuinely suspect).
        f = normalize_formula(m)
        prior = by_formula.get(f)
        if prior is not None and prior is not m:
            both_owned_distinct = (
                prior.owner_model is not None
                and m.owner_model is not None
                and prior.owner_model != m.owner_model
            )
            if not both_owned_distinct:
                cols.append({
                    "kind": "formula",
                    "a": prior.name, "b": m.name,
                    "files": [prior.source_file, m.source_file],
                })
        by_formula.setdefault(f, m)
    return cols
