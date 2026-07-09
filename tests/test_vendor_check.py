import os
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_script_present_and_executable():
    assert os.access(ROOT / "scripts/check_vendor_updates.sh", os.X_OK)


def test_version_sha_extractable():
    txt = (ROOT / "vendor/dbt-agent-skills/VERSION").read_text()
    assert re.search(r"commit:\s*[0-9a-f]{40}", txt)
