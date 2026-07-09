"""
Tests for trust.config.load_config — safe defaults and JSON parsing.
"""
import json
import os
from trust.config import load_config


def test_missing_config_safe_default(tmp_path):
    """No config file → empty approved_email_domains (no domain check, not a failure)."""
    cfg = load_config(str(tmp_path))
    assert cfg["approved_email_domains"] == []


def test_config_with_domains_loaded(tmp_path):
    """Valid JSON with approved_email_domains → list returned correctly."""
    config_file = tmp_path / ".semantic-trust.json"
    config_file.write_text(json.dumps({"approved_email_domains": ["example.com", "corp.io"]}))
    cfg = load_config(str(tmp_path))
    assert cfg["approved_email_domains"] == ["example.com", "corp.io"]


def test_config_missing_key_returns_empty_list(tmp_path):
    """JSON present but key absent → safe default empty list."""
    config_file = tmp_path / ".semantic-trust.json"
    config_file.write_text(json.dumps({"some_other_key": "value"}))
    cfg = load_config(str(tmp_path))
    assert cfg["approved_email_domains"] == []


def test_config_empty_file_returns_empty_list(tmp_path):
    """Empty/invalid JSON file → safe default."""
    config_file = tmp_path / ".semantic-trust.json"
    config_file.write_text("")
    cfg = load_config(str(tmp_path))
    assert cfg["approved_email_domains"] == []


def test_no_hardcoded_domains(tmp_path):
    """load_config must never inject any domain when file is absent."""
    cfg = load_config(str(tmp_path))
    # Explicitly verify no domain leaks from implementation
    assert cfg["approved_email_domains"] == []
    assert len(cfg["approved_email_domains"]) == 0
