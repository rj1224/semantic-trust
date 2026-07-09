"""
trust/config.py — load optional project-level config from .semantic-trust.json.

Safe default: if file is missing or key is absent → empty list.
An empty approved_email_domains list means NO domain check is applied (not a failure).

Config file format (.semantic-trust.json):
    {"approved_email_domains": ["example.com", "corp.io"]}
"""
import json
import os


def load_config(project_dir: str) -> dict:
    """
    Read .semantic-trust.json from project_dir (if it exists).

    Returns a dict with at minimum:
        {"approved_email_domains": [...]}

    SAFE DEFAULT: missing file, empty file, or absent key → empty list.
    Never hardcodes any domain — the allowlist comes exclusively from the file.
    """
    config_path = os.path.join(project_dir, ".semantic-trust.json")
    raw: dict = {}
    if os.path.isfile(config_path):
        with open(config_path, "r") as fh:
            try:
                loaded = json.load(fh)
                if isinstance(loaded, dict):
                    raw = loaded
            except json.JSONDecodeError:
                pass

    return {
        "approved_email_domains": raw.get("approved_email_domains") or [],
    }
