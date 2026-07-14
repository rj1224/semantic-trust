"""Discriminating tests for scripts/check_secrets.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).parents[1]

# Import the scanner directly so we can test the logic in-process.
sys.path.insert(0, str(ROOT / "scripts"))
from check_secrets import scan  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests — pattern matching
# ---------------------------------------------------------------------------


def test_fake_aws_key_is_flagged(tmp_path: Path) -> None:
    """A string that looks like an AWS access key must trigger a hit."""
    (tmp_path / "creds.py").write_text('key = "AKIAIOSFODNN7EXAMPLE"\n')  # secrets-ok
    hits = scan(tmp_path)
    assert hits, "Expected a hit for fake AWS key, got none"
    assert "AWS access key" in hits[0]


def test_clean_string_is_not_flagged(tmp_path: Path) -> None:
    """Ordinary source code with no secret patterns must produce zero hits."""
    (tmp_path / "clean.py").write_text(
        textwrap.dedent(
            """\
            def greet(name: str) -> str:
                return f"Hello, {name}!"
            """
        )
    )
    hits = scan(tmp_path)
    assert not hits, f"Expected zero hits for clean file, got: {hits}"


def test_secrets_ok_pragma_suppresses_hit(tmp_path: Path) -> None:
    """A line bearing the ``# secrets-ok`` pragma must not be flagged."""
    (tmp_path / "fixture.py").write_text('key = "AKIAIOSFODNN7EXAMPLE"  # secrets-ok\n')
    hits = scan(tmp_path)
    assert not hits, f"secrets-ok pragma should suppress hit, got: {hits}"


def test_repo_itself_is_clean() -> None:
    """The secrets scanner must exit 0 when run against this repo."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_secrets.py"), str(ROOT)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Secrets scan found hits in repo:\n{result.stderr}"
