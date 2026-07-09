"""Production-path helper: run the user's own `dbt parse` to (re)generate
target/semantic_manifest.json, then the engine reads it. Version-agnostic:
`dbt parse` works for both legacy (1.6-1.11) and latest (1.12+) specs.
(mf validate-configs is legacy-only — dbt-metricflow pins dbt-core <1.12 — so
dbt parse, not mf, is the universal compile gate.)"""
import os
import subprocess


def compile_manifest(project_dir: str, profiles_dir: str | None = None) -> dict:
    env = dict(os.environ)
    env["DBT_PROJECT_DIR"] = project_dir
    if profiles_dir:
        env["DBT_PROFILES_DIR"] = profiles_dir
    proc = subprocess.run(
        ["dbt", "parse"],
        cwd=project_dir, env=env,
        capture_output=True, text=True,
    )
    manifest_path = os.path.join(project_dir, "target", "semantic_manifest.json")
    ok = proc.returncode == 0 and os.path.exists(manifest_path)
    return {
        "ok": ok,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "manifest_path": manifest_path,
    }
