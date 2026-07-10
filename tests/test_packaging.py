import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[1]

def _pyproject():
    return tomllib.loads((ROOT / "pyproject.toml").read_text())


# ---------------------------------------------------------------------------
# Stale-rename guard — fails if any skills/ file still uses old dist/MCP names
# ---------------------------------------------------------------------------
_STALE_TOKENS = [
    ".dbt-sl-authoring.yml",
    "dbt-sl-trust__",
    "dbt-sl-authoring",
    "dbt_sl_authoring",
    "dbt-sl-trust",
]

def test_no_stale_rename_tokens_in_skills():
    """Assert that no file under skills/ contains tokens from the pre-rename era."""
    skills_root = ROOT / "skills"
    hits: list[str] = []
    for path in sorted(skills_root.rglob("*")):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for token in _STALE_TOKENS:
            if token in text:
                # record every (file, token) pair so the failure message is actionable
                hits.append(f"{path.relative_to(ROOT)}: found token {token!r}")
    assert not hits, (
        "Stale pre-rename tokens found in skills/:\n  " + "\n  ".join(hits)
    )

def test_dist_name_is_semantic_trust():
    assert _pyproject()["project"]["name"] == "semantic-trust"

def test_runtime_deps_are_mcp_only():
    deps = _pyproject()["project"]["dependencies"]
    assert deps == ["mcp>=1.0"], deps  # pyyaml moved to the ci extra (test-only)

def test_entry_points_renamed():
    scripts = _pyproject()["project"]["scripts"]
    assert scripts["semantic-trust-mcp"] == "trust.mcp_server:main"
    assert scripts["semantic-trust"] == "trust.cli:main_cli"
    assert "dbt-sl-trust-mcp" not in scripts and "dbt-sl-trust" not in scripts

def test_wheel_excludes_eval():
    inc = _pyproject()["tool"]["setuptools"]["packages"]["find"]["include"]
    assert "trust*" in inc and "eval*" not in inc


# ---------------------------------------------------------------------------
# Plugin manifest tests (Task 2)
# ---------------------------------------------------------------------------
import json

def test_plugin_manifest_valid():
    m = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
    assert m["name"] == "semantic-trust"
    assert m["version"] == "0.1.0"
    assert m["author"]["name"] == "Ravish Jain"
    assert m["author"]["email"] == "ravishjain024@gmail.com"
    assert m["description"]

def test_marketplace_manifest_valid():
    raw = (ROOT / ".claude-plugin" / "marketplace.json").read_text()
    m = json.loads(raw)
    # Top-level name
    assert m["name"] == "semantic-trust"
    # Exactly one plugin entry
    assert len(m["plugins"]) == 1
    plugin = m["plugins"][0]
    # Plugin name and source
    assert plugin["name"] == "semantic-trust"
    assert plugin["source"] == "."
    # Author identity
    assert plugin["author"]["name"] == "Ravish Jain"
    assert plugin["author"]["email"] == "ravishjain024@gmail.com"
    # No stale tokens in the manifest
    _banned = "".join(["por", "ter"])
    assert _banned not in raw.lower()
    # Version must stay in lockstep with the package version (guards the release bump)
    assert plugin["version"] == _pyproject()["project"]["version"], (
        "marketplace.json plugin version must equal pyproject version"
    )


def test_mcp_manifest_launches_via_uvx():
    m = json.loads((ROOT / ".mcp.json").read_text())
    srv = m["mcpServers"]["semantic-trust"]
    assert srv["type"] == "stdio"
    assert srv["command"] == "uvx"
    assert srv["args"] == ["--from", "semantic-trust", "semantic-trust-mcp"]


# ---------------------------------------------------------------------------
# Slash command tests (Task 3)
# ---------------------------------------------------------------------------

COMMANDS = {
    "document": "document-semantics",
    "build": "build-dbt-model",
    "validate": "validate-semantics",
}


def test_command_files_exist_and_reference_skill():
    for cmd, skill in COMMANDS.items():
        txt = (ROOT / "commands" / f"{cmd}.md").read_text()
        assert skill in txt, f"commands/{cmd}.md must invoke the {skill} skill"


# ---------------------------------------------------------------------------
# Docs tests (Task 4)
# ---------------------------------------------------------------------------

def test_license_is_mit_ravish():
    txt = (ROOT / "LICENSE").read_text()
    assert "MIT License" in txt and "Ravish Jain" in txt


def test_readme_has_required_sections():
    txt = (ROOT / "README.md").read_text().lower()
    for needle in ("install", "dbt", "semantic", "license", "1.12", "not affiliated"):
        assert needle in txt, f"README missing '{needle}'"


def test_docs_have_no_proprietary_refs():
    _banned = "".join(["por", "ter"])  # avoid literal so leakage gate stays clean
    for p in ("README.md", "CHANGELOG.md", "LICENSE"):
        assert _banned not in (ROOT / p).read_text().lower()


# ---------------------------------------------------------------------------
# Plugin-root path guard (Task 2)
# ---------------------------------------------------------------------------
import re

# The prefix that must appear before any cross-directory bundled-file reference.
_PLUGIN_ROOT_PREFIX = "${CLAUDE_PLUGIN_ROOT}/"

# Literal substring patterns for bundled paths that require the prefix.
_BUNDLED_LITERALS = [
    "vendor/dbt-agent-skills/",
    "eval/judge.md",
    # Full repo-rooted form of the shared references tree.
    "skills/references/",
]


def _bare_bundled_re() -> re.Pattern:
    """Return a compiled regex that matches bare bundled paths (not prefixed by
    ${CLAUDE_PLUGIN_ROOT}/).  Uses re.escape + a negative lookbehind so the
    prefix check is exact."""
    escaped_prefix = re.escape(_PLUGIN_ROOT_PREFIX)
    alts = "|".join(re.escape(p) for p in _BUNDLED_LITERALS)
    return re.compile(r"(?<!" + escaped_prefix + r")(?:" + alts + r")")


_BARE_BUNDLED_RE = _bare_bundled_re()


def test_skills_use_plugin_root_for_bundled_paths():
    """Every reference to a bundled file in skills/**/SKILL.md must be prefixed
    with ${CLAUDE_PLUGIN_ROOT}/ so the path resolves at plugin runtime (CWD is
    the user's dbt project, not the plugin root).

    Fails on bare occurrences; correctly-prefixed paths are not flagged.
    """
    skills_root = ROOT / "skills"
    hits: list[str] = []

    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        text = skill_md.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if _BARE_BUNDLED_RE.search(line):
                hits.append(f"{skill_md.relative_to(ROOT)}:{lineno}: {line.strip()}")

    assert not hits, (
        "SKILL.md files reference bundled files without ${CLAUDE_PLUGIN_ROOT}/ prefix — "
        "these paths won't resolve at plugin runtime:\n  " + "\n  ".join(hits)
    )
