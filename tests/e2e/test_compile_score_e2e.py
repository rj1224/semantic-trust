"""End-to-end smoke: real dbt 1.12 project through compile -> score.

Skips automatically when no dbt 1.12 binary is on PATH (keeps the hermetic
unit suite unaffected). Proves the whole chain works on a REAL dbt project:
compile_manifest runs `dbt parse` to produce the manifest, then build_report
scores it. Asserts a good semantic model scores non-F and a structurally-broken
one scores F.
"""
import shutil
import subprocess

import pytest

from trust.compile import compile_manifest
from trust.cli import build_report


def _has_dbt_1_12() -> bool:
    """Return True only when the installed dbt-core major.minor is exactly 1.12."""
    if not shutil.which("dbt"):
        return False
    out = subprocess.run(
        ["dbt", "--version"], capture_output=True, text=True
    ).stdout
    # Match "installed: 1.12." to avoid "1.12" matching inside "1.11.12".
    import re
    return bool(re.search(r"installed:\s+1\.12\.", out))


pytestmark = pytest.mark.skipif(
    not _has_dbt_1_12(), reason="needs dbt-core 1.12+"
)


def test_good_model_scores_above_broken():
    import os
    _here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    good = os.path.join(_here, "tests/fixtures/manifest_src/single_latest")
    broken = os.path.join(_here, "tests/fixtures/manifest_src/single_latest_broken")

    good_compile = compile_manifest(good, profiles_dir=good)
    assert good_compile["ok"], (
        f"Good fixture failed to compile.\n"
        f"stdout: {good_compile['stdout']}\n"
        f"stderr: {good_compile['stderr']}"
    )

    broken_compile = compile_manifest(broken, profiles_dir=broken)
    assert broken_compile["ok"], (
        f"Broken fixture failed to compile (it should parse OK, just warn).\n"
        f"stdout: {broken_compile['stdout']}\n"
        f"stderr: {broken_compile['stderr']}"
    )

    g = build_report(good, "fct_orders")
    b = build_report(broken, "fct_orders")

    assert g["gates"]["structural"] is True, (
        f"Good model should pass structural gate; got gates={g['gates']}"
    )
    assert g["band"] != "F", (
        f"Good model should not score F; got band={g['band']}"
    )

    assert b["gates"]["structural"] is False, (
        f"Broken model should fail structural gate; got gates={b['gates']}"
    )
    assert b["band"] == "F", (
        f"Broken model should score F; got band={b['band']}"
    )
