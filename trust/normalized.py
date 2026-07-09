"""Pure normalized dataclasses shared by the loader, gates, and scorer.
No imports from other trust modules — this breaks the loader↔uniqueness cycle."""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NormalizedModel:
    name: str
    source_file: str
    spec: str                          # provenance tag: "manifest"
    entities: list = field(default_factory=list)    # [{name, type}]
    dimensions: list = field(default_factory=list)  # [{name, type, is_time}]
    measures: list = field(default_factory=list)    # [{name, agg, expr}]
    has_time_dimension: bool = False


@dataclass
class NormalizedMetric:
    name: str
    type: str
    definition_norm: str               # canonical resolved formula string
    description: str
    owner: Optional[str]
    source_file: str
    owner_model: Optional[str] = None
