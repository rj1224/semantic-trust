"""Guard tests for skill YAML authoring discipline.

Rules:
- Any skill that mentions mf validate-configs or mf compile MUST also have
  dbt parse AND qualify mf as legacy-only.
- document-semantics and build-dbt-model MUST reference vendor/dbt-agent-skills.
"""
import re


def test_skills_use_dbt_parse_gate_not_mf_only():
    for f in (
        "skills/document-semantics/SKILL.md",
        "skills/build-dbt-model/SKILL.md",
        "skills/validate-semantics/SKILL.md",
    ):
        txt = open(f).read()
        if "mf validate-configs" in txt or "mf compile" in txt:
            assert "dbt parse" in txt, f"{f} gates on mf without dbt parse"
            assert re.search(r"legacy", txt, re.I), f"{f} mentions mf without legacy qualification"


def test_skills_reference_vendored_grammar():
    for f in ("skills/document-semantics/SKILL.md", "skills/build-dbt-model/SKILL.md"):
        assert "vendor/dbt-agent-skills" in open(f).read(), f


def test_corpus_no_semantic_type():
    """No semantic_type: key anywhere in the corpus — it is removed in latest spec."""
    txt = open("skills/references/examples/qcommerce-corpus.md").read()
    assert "semantic_type:" not in txt, "qcommerce-corpus.md contains forbidden 'semantic_type:'"


def test_corpus_no_defaults_agg_time_dimension():
    """agg_time_dimension must NOT be nested under defaults: in any latest-spec YAML."""
    import re
    txt = open("skills/references/examples/qcommerce-corpus.md").read()
    # Only check the latest-spec sections (stop before any legacy section)
    legacy_header = re.search(r"^##\s.*[Ll]egacy", txt, re.MULTILINE)
    latest_txt = txt[: legacy_header.start()] if legacy_header else txt
    # Look for the nesting pattern: defaults:\n  agg_time_dimension (with any indentation)
    assert not re.search(r"defaults:\s*\n\s+agg_time_dimension", latest_txt), \
        "qcommerce-corpus.md nests agg_time_dimension under defaults: (should be model-level key)"


def test_corpus_no_type_params_in_latest_ratio():
    """Ratio metrics in latest-spec sections must use direct numerator/denominator, not type_params."""
    import re
    txt = open("skills/references/examples/qcommerce-corpus.md").read()
    # Find the latest-spec ratio example section (Example 2) — stop before any legacy section
    legacy_header = re.search(r"^##\s.*[Ll]egacy", txt, re.MULTILINE)
    latest_txt = txt[: legacy_header.start()] if legacy_header else txt
    # Extract YAML blocks in latest section
    yaml_blocks = re.findall(r"```yaml\n(.*?)```", latest_txt, re.DOTALL)
    for block in yaml_blocks:
        # Check if this block contains a ratio metric
        if "type: ratio" in block:
            assert "type_params:" not in block, \
                "Ratio metric in latest-spec section uses forbidden type_params: wrapper"


def test_corpus_no_flat_entities_list():
    """No flat entities: list under semantic_model: in latest-spec YAML blocks."""
    import re
    txt = open("skills/references/examples/qcommerce-corpus.md").read()
    legacy_header = re.search(r"^##\s.*[Ll]egacy", txt, re.MULTILINE)
    latest_txt = txt[: legacy_header.start()] if legacy_header else txt
    yaml_blocks = re.findall(r"```yaml\n(.*?)```", latest_txt, re.DOTALL)
    for block in yaml_blocks:
        # A flat entities: list (indented top-level list under semantic_model) is wrong
        # Pattern: line that is just "      entities:" at the semantic_model nesting level
        # The per-column entity: blocks (indented under a column) are fine
        if re.search(r"^\s{6,8}entities:\s*$", block, re.MULTILINE):
            raise AssertionError(
                "Flat 'entities:' list found in latest-spec YAML block (should be per-column entity: blocks)"
            )
