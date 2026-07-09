import glob
import re

LATEST_WRONG = re.compile(r"semantic_type\s*:")

# Wrong legacy tokens that must not appear in prose or tables of files labeled 1.12+/latest.
# These are dotted-path references or bare keys that indicate legacy MetricFlow grammar:
#   type_params.numerator  type_params.denominator  type_params.metrics  type_params.expr
# Also catches the bare `semantic_type` already in LATEST_WRONG, but we keep that separate
# for the template-only scan.
_WRONG_LEGACY_PROSE_TOKENS = re.compile(
    r"type_params\.(numerator|denominator|metrics|expr)\b"
)

# Legacy-only YAML keys that must not appear inside code blocks in the latest-spec
# sections of templates.  type_params: and measures: are legacy MetricFlow constructs
# removed in dbt 1.12+.  Prose mentions (e.g. "No type_params: wrapper") are
# intentional and excluded by only scanning fenced YAML code blocks.
#
# Pattern: a line inside a code block that starts with optional whitespace then the
# bare key (not inside a comment or backtick-quoted prose).
_LEGACY_KEY_IN_YAML = re.compile(r"^\s+(type_params|measures)\s*:", re.MULTILINE)


def _latest_yaml_blocks(text: str) -> str:
    """Return the concatenated content of fenced YAML code blocks found in the
    latest-spec portion of a template file.

    We stop at the first '## ... Legacy ...' section header so we don't scan the
    intentional legacy examples, which legitimately contain type_params/measures.
    If there is no legacy section, the whole file is scanned.
    """
    legacy_header = re.search(r"^##\s.*[Ll]egacy", text, re.MULTILINE)
    latest = text[: legacy_header.start()] if legacy_header else text

    # Extract content of ```yaml ... ``` fenced blocks only.
    blocks = re.findall(r"```yaml\n(.*?)```", latest, re.DOTALL)
    return "\n".join(blocks)


def test_no_wrong_latest_grammar_in_templates():
    offenders = []
    for f in glob.glob("skills/references/templates/*.md"):
        txt = open(f).read()
        if LATEST_WRONG.search(txt):
            offenders.append(f)
    assert offenders == [], f"wrong latest-grammar token 'semantic_type:' in {offenders}"


def test_no_legacy_only_tokens_in_latest_yaml_blocks():
    """Ensure type_params: and measures: don't appear inside YAML code blocks in
    the latest-spec sections of templates.

    These are legacy MetricFlow constructs (dbt 1.6–1.11) removed in dbt 1.12+.
    An agent following a template code block that contains them would produce
    invalid YAML against the latest spec.

    Scope: only fenced ```yaml blocks in the latest-spec portion of each file
    (before the first '## ... Legacy ...' header).  Prose text that mentions
    these keys in a "do NOT use" context is intentionally excluded.
    """
    offenders = []
    for f in glob.glob("skills/references/templates/*.md"):
        txt = open(f).read()
        yaml_src = _latest_yaml_blocks(txt)
        if _LEGACY_KEY_IN_YAML.search(yaml_src):
            offenders.append(f)
    assert offenders == [], (
        f"legacy-only YAML key(s) 'type_params:' or 'measures:' found inside "
        f"latest-spec YAML code blocks in: {offenders}"
    )


def test_templates_reference_vendored_spec():
    joined = "".join(open(f).read() for f in glob.glob("skills/references/templates/*.md"))
    assert "vendor/dbt-agent-skills/latest-spec.md" in joined


def _is_latest_labeled(text: str) -> bool:
    """Return True if the file declares a dbt-core 1.12+ / latest target."""
    return bool(re.search(r"dbt-core 1\.12\+|Target:.*latest", text, re.IGNORECASE))


def test_no_wrong_legacy_tokens_in_workflows_and_standards():
    """Scan prose+tables in workflows/*.md and standards/*.md for wrong legacy tokens.

    Files labeled dbt-core 1.12+ must not contain dotted legacy path references like
    type_params.numerator, type_params.denominator, type_params.metrics, type_params.expr.
    These indicate old MetricFlow grammar and would instruct agents to generate invalid YAML.

    This test would have caught the three files fixed in the FINAL-REVIEW pass:
      - skills/references/standards/metric-design.md
      - skills/references/workflows/model-building-workflows.md
      - skills/references/validation/structural.md
    """
    offenders = []
    scan_globs = [
        "skills/references/workflows/*.md",
        "skills/references/standards/*.md",
        "skills/references/validation/*.md",
    ]
    for pattern in scan_globs:
        for f in glob.glob(pattern):
            txt = open(f).read()
            if not _is_latest_labeled(txt):
                continue  # skip files not labeled latest / 1.12+
            # Stop before any legacy section to avoid false-positives on intentional legacy docs
            legacy_header = re.search(r"^##\s.*[Ll]egacy", txt, re.MULTILINE)
            scan_txt = txt[: legacy_header.start()] if legacy_header else txt
            if _WRONG_LEGACY_PROSE_TOKENS.search(scan_txt):
                offenders.append(f)
    assert offenders == [], (
        f"Wrong legacy token(s) (type_params.numerator/denominator/metrics/expr) found "
        f"in latest-labeled reference files: {offenders}"
    )
