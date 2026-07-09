"""End-to-end round-trip: scaffold_semantic_model output -> valid dbt parse.

Skips automatically when no dbt 1.12 binary is on PATH (keeps the hermetic
unit suite unaffected).

Proof chain:
1. Build a tiny dbt project in a temp dir (models/schema only, no semantic layer yet).
   Columns have explicit data_type: entries so manifest.json carries real types.
2. Run `dbt parse` to produce manifest.json; extract real columns from it.
3. Call scaffold_semantic_model with those real columns.
4. Render the scaffold skeleton to a minimal valid latest-spec orders.yml:
   - entity type:primary on the _id column
   - one simple metric (sum of the first metric_candidate) with a label
   - time dim + categorical dims kept
5. Write the scaffold-derived YAML into the project and run `dbt parse` again.
6. Assert parse SUCCEEDS and compiled semantic_manifest.json contains the
   semantic model AND the metric.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

import pytest
import yaml

from trust.manifest_scaffold import model_columns, scaffold_semantic_model
from trust.compile import compile_manifest


# ---------------------------------------------------------------------------
# Version guard — reuse exact pattern from test_compile_score_e2e.py
# ---------------------------------------------------------------------------

def _has_dbt_1_12() -> bool:
    """Return True only when the installed dbt-core major.minor is exactly 1.12."""
    if not shutil.which("dbt"):
        return False
    out = subprocess.run(
        ["dbt", "--version"], capture_output=True, text=True
    ).stdout
    import re
    return bool(re.search(r"installed:\s+1\.12\.", out))


pytestmark = pytest.mark.skipif(
    not _has_dbt_1_12(), reason="needs dbt-core 1.12+"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_tiny_project(root: str) -> None:
    """Write a minimal dbt+duckdb project under root (no semantic layer yet).

    File layout:
    - _time_spine.yml  : metricflow_time_spine config (kept throughout)
    - schema.yml       : fct_orders column data_types only (no semantic layer);
                         overwritten by the scaffold YAML in the second parse phase
    """
    proj = pathlib.Path(root)
    models = proj / "models"
    models.mkdir(parents=True)

    (proj / "dbt_project.yml").write_text(
        "name: scaffold_rt\nversion: '1.0.0'\nconfig-version: 2\n"
        "profile: scaffold_rt\nmodel-paths: [\"models\"]\n"
    )
    (proj / "profiles.yml").write_text(
        "scaffold_rt:\n  target: dev\n"
        "  outputs:\n    dev: {type: duckdb, path: dev.duckdb}\n"
    )
    (models / "metricflow_time_spine.sql").write_text(
        "select cast('2024-01-01' as date) + cast(i as integer) as date_day"
        " from range(0, 100) as t(i)"
    )
    (models / "fct_orders.sql").write_text(
        "select 1 as order_id,"
        " cast('2024-01-01' as timestamp) as ordered_at,"
        " 'placed' as status,"
        " 100.0 as amount"
    )
    # Time spine stays in its own file so overwriting schema.yml is safe
    (models / "_time_spine.yml").write_text(
        "models:\n"
        "  - name: metricflow_time_spine\n"
        "    time_spine:\n"
        "      standard_granularity_column: date_day\n"
        "    columns:\n"
        "      - name: date_day\n"
        "        granularity: day\n"
    )
    # Plain schema.yml: column data_type only, no semantic layer
    (models / "schema.yml").write_text(
        "models:\n"
        "  - name: fct_orders\n"
        "    columns:\n"
        "      - name: order_id\n"
        "        data_type: integer\n"
        "      - name: ordered_at\n"
        "        data_type: timestamp\n"
        "      - name: status\n"
        "        data_type: varchar\n"
        "      - name: amount\n"
        "        data_type: numeric\n"
    )


def _render_scaffold_to_yaml(scaffold: dict, metric_name: str = "total_amount") -> str:
    """Convert scaffold dict to a minimal valid latest-spec YAML string.

    Rules:
    - entity with type "unknown" on _id column -> promoted to type "primary"
    - first _metric_candidate -> one simple sum metric with a label
    - _inferred / internal keys stripped
    - granularity stays at column level (not nested under dimension:)
    """
    cols_yaml = []
    for c in scaffold["columns"]:
        col: dict = {"name": c["name"]}
        if "entity" in c:
            etype = c["entity"]["type"]
            if etype == "unknown":
                etype = "primary"
            col["entity"] = {"type": etype, "name": c["entity"]["name"]}
        elif "dimension" in c:
            col["dimension"] = c["dimension"]
            if "granularity" in c:
                col["granularity"] = c["granularity"]
        else:
            # _inferred measure_candidate — skip as column (appears as metric expr only)
            continue
        cols_yaml.append(col)

    metrics_yaml = []
    candidates = scaffold.get("_metric_candidates", [])
    if candidates:
        metrics_yaml.append({
            "name": metric_name,
            "type": "simple",
            "label": "Total Amount",
            "agg": "sum",
            "expr": candidates[0],
        })

    model_entry: dict = {
        "name": scaffold["model"],
        "semantic_model": {"enabled": True},
        "agg_time_dimension": scaffold["agg_time_dimension"],
        "columns": cols_yaml,
    }
    if metrics_yaml:
        model_entry["metrics"] = metrics_yaml

    return yaml.dump({"models": [model_entry]}, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_scaffold_roundtrip():
    """scaffold_semantic_model output round-trips through real dbt parse."""
    with tempfile.TemporaryDirectory() as tmp:
        project_dir = os.path.join(tmp, "project")
        os.makedirs(project_dir)

        # 1. Build tiny project (no semantic layer yet)
        _build_tiny_project(project_dir)

        # 2. First parse — produce manifest.json with real typed columns
        result1 = compile_manifest(project_dir, profiles_dir=project_dir)
        assert result1["ok"], (
            f"Initial dbt parse failed.\nstdout: {result1['stdout']}\nstderr: {result1['stderr']}"
        )

        # 3. Extract real columns from manifest (data_type populated from schema.yml)
        with open(os.path.join(project_dir, "target", "manifest.json")) as fh:
            manifest = json.load(fh)

        cols = model_columns(manifest, "fct_orders")
        assert cols, "No columns found for fct_orders in manifest"
        col_types = {c["name"]: c["data_type"] for c in cols}
        assert col_types.get("ordered_at") is not None, (
            f"ordered_at has no data_type; got: {col_types}"
        )

        # 4. Scaffold — produce correct latest-spec dict
        scaffold = scaffold_semantic_model("fct_orders", cols)
        assert scaffold["semantic_model"] == {"enabled": True}
        assert scaffold["agg_time_dimension"] is not None, (
            "No time dimension detected; check column data_types"
        )
        assert scaffold.get("_metric_candidates"), (
            "No metric candidates detected; check numeric column detection"
        )

        # 5. Render scaffold to valid latest-spec YAML
        orders_yml_content = _render_scaffold_to_yaml(
            scaffold, metric_name="scaffold_total_revenue"
        )

        # 6. Write scaffold-derived YAML into the project.
        #    fct_orders was the only entry in schema.yml; overwrite it with the
        #    full scaffold-derived semantic YAML so dbt sees a single definition.
        #    The time_spine stays in _time_spine.yml (untouched).
        scaffold_yml_path = os.path.join(project_dir, "models", "schema.yml")
        with open(scaffold_yml_path, "w") as fh:
            fh.write(orders_yml_content)

        # 7. Second parse — must succeed with scaffold-derived YAML
        result2 = compile_manifest(project_dir, profiles_dir=project_dir)
        assert result2["ok"], (
            f"dbt parse failed after writing scaffold YAML.\n"
            f"YAML written:\n{orders_yml_content}\n"
            f"stdout: {result2['stdout']}\nstderr: {result2['stderr']}"
        )

        # 8. Verify semantic_manifest.json contains the semantic model and metric
        sm_path = os.path.join(project_dir, "target", "semantic_manifest.json")
        assert os.path.exists(sm_path), "semantic_manifest.json not produced by dbt parse"
        with open(sm_path) as fh:
            semantic_manifest = json.load(fh)

        sem_models = semantic_manifest.get("semantic_models", [])
        sm_names = [m.get("name") for m in sem_models]
        assert "fct_orders" in sm_names, (
            f"fct_orders not found in semantic_manifest.semantic_models; got: {sm_names}"
        )

        metrics = semantic_manifest.get("metrics", [])
        metric_names = [m.get("name") for m in metrics]
        assert "scaffold_total_revenue" in metric_names, (
            f"scaffold_total_revenue metric not found in semantic_manifest; got: {metric_names}"
        )
