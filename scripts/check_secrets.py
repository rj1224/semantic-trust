"""Generic secrets scanner — stdlib only.

Walk a directory tree and flag common secret patterns.
Supports a ``# secrets-ok`` pragma on a line to suppress that match.

Exit 0 when clean, exit 1 with FILE:LINE output on any hit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Each entry: (label, compiled regex)
_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "Private key header",
        re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ),
    (
        "Generic secret assignment",
        re.compile(
            r"""(?i)(password|secret|token|api_key|apikey|access_key)\s*=\s*['"][^'"]{16,}['"]"""
        ),
    ),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z\-]+")),
    ("GitHub PAT", re.compile(r"ghp_[0-9A-Za-z]{36}")),
]

# ---------------------------------------------------------------------------
# Directories / files to skip
# ---------------------------------------------------------------------------

_SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", "target", ".pytest_cache"}

# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _should_skip(path: Path) -> bool:
    return any(part in _SKIP_DIRS for part in path.parts)


def scan(root: Path) -> list[str]:
    """Return a list of 'FILE:LINE  label: snippet' strings for every hit."""
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or _should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "secrets-ok" in line:
                continue
            for label, pattern in _PATTERNS:
                if pattern.search(line):
                    snippet = line.strip()[:120]
                    hits.append(f"{path}:{lineno}  [{label}]  {snippet}")
    return hits


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]) if args else Path(".")
    hits = scan(root.resolve())
    if hits:
        print("SECRETS SCAN FAILED — potential secrets found:", file=sys.stderr)
        for h in hits:
            print(f"  {h}", file=sys.stderr)
        return 1
    print("secrets scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
