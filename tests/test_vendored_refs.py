import os, re
V = "vendor/dbt-agent-skills"

def test_vendored_files_present():
    for f in ("latest-spec.md", "legacy-spec.md", "time-spine.md", "best-practices.md", "NOTICE", "VERSION"):
        assert os.path.exists(os.path.join(V, f)), f

def test_version_pins_a_commit():
    txt = open(os.path.join(V, "VERSION")).read()
    assert re.search(r"commit:\s*[0-9a-f]{40}", txt), "VERSION must pin a full 40-char commit SHA"
    assert "Apache-2.0" in txt

def test_notice_attributes_dbt_labs():
    txt = open(os.path.join(V, "NOTICE")).read()
    assert "dbt-labs" in txt and "Apache License 2.0" in txt

def test_latest_spec_has_correct_grammar_markers():
    txt = open(os.path.join(V, "latest-spec.md")).read()
    # sanity: the vendored latest grammar is the model-annotation form, not the wrong one
    assert "semantic_model:" in txt and "enabled: true" in txt
    assert "dimension:" in txt  # nested dimension blocks on columns
