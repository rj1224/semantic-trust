"""Tests for trust.spec_detect — version gate + fixture-based spec detection."""
from trust.spec_detect import detect_spec, dbt_supports_latest

LATEST_FIXTURE = "tests/fixtures/manifests/qcommerce_latest"
LEGACY_FIXTURE = "tests/fixtures/manifests/qcommerce_legacy"


def test_dbt_version_gate():
    assert dbt_supports_latest("1.12.0") is True
    assert dbt_supports_latest("1.12.0-b3") is True
    assert dbt_supports_latest("1.11.11") is False
    assert dbt_supports_latest("1.9.0") is False


def test_detect_latest_from_manifest_fixture():
    assert detect_spec(LATEST_FIXTURE) == "latest"


def test_detect_legacy_from_manifest_fixture():
    assert detect_spec(LEGACY_FIXTURE) == "legacy"
