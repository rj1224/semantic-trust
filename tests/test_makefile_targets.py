"""Smoke test: assert new Makefile targets and workflow file exist."""
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def _makefile_text() -> str:
    return (PROJECT_ROOT / "Makefile").read_text()


def test_ci_hermetic_target_defined():
    assert "ci-hermetic:" in _makefile_text()


def test_ci_dbt12_target_defined():
    assert "ci-dbt12:" in _makefile_text()


def test_vendor_check_target_defined():
    assert "vendor-check:" in _makefile_text()


def test_new_targets_in_phony():
    text = _makefile_text()
    phony_line = next(l for l in text.splitlines() if l.startswith(".PHONY:"))
    for target in ("ci-hermetic", "ci-dbt12", "vendor-check"):
        assert target in phony_line, f"{target} missing from .PHONY"


def test_ci_workflow_file_exists():
    workflow = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    assert workflow.exists(), "ci.yml workflow file not found"


def test_ci_workflow_has_two_jobs():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "hermetic" in workflow
    assert "dbt12" in workflow


def test_ci_workflow_marked_prepared():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "PREPARED" in workflow or "prepared" in workflow.lower()
