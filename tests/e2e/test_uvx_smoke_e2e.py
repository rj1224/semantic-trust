"""
E2E smoke test: uv build + uvx MCP initialize handshake (Task 5, Phase 4).

Proves that:
  1. `uv build` produces a wheel excluding tests/ and eval/.
  2. `uvx --from <wheel> semantic-trust-mcp` starts the stdio MCP server and
     completes a JSON-RPC initialize handshake, returning a result that
     identifies the server as "semantic-trust".

The MCP SDK (>=1.0) uses newline-delimited JSON over stdio — no Content-Length
headers.  One line in → one (or more) lines out, each a valid JSON-RPC message.

Skipped when `uv` is not on PATH (CI without uv, offline sandboxes).
"""

import glob
import json
import shutil
import subprocess

import pytest

ROOT = __import__("pathlib").Path(__file__).parents[2]


def _has_uv() -> bool:
    return shutil.which("uv") is not None


pytestmark = pytest.mark.skipif(not _has_uv(), reason="needs uv/uvx")


def _latest_wheel() -> str | None:
    ws = sorted(glob.glob(str(ROOT / "dist" / "semantic_trust-0.1.0-*.whl")))
    return ws[-1] if ws else None


def test_wheel_excludes_tests_and_eval():
    """Wheel must contain trust/ and must NOT contain tests/ or eval/."""
    import zipfile

    if _latest_wheel() is None:
        subprocess.run(["uv", "build"], cwd=ROOT, check=True, capture_output=True)
    wheel = _latest_wheel()
    assert wheel, "no wheel built after uv build"

    names = zipfile.ZipFile(wheel).namelist()
    assert any(n.startswith("trust/") for n in names), f"trust/ missing from wheel {wheel}"
    bad = [n for n in names if n.startswith("tests/") or n.startswith("eval/")]
    assert not bad, f"wheel contains test/eval artifacts: {bad}"


def test_build_and_mcp_initialize():
    """
    Build the wheel if absent, then send an MCP initialize request via uvx and
    assert a valid result naming semantic-trust.

    This is a REAL handshake check — not a process-exists check.
    """
    if _latest_wheel() is None:
        subprocess.run(["uv", "build"], cwd=ROOT, check=True, capture_output=True)
    wheel = _latest_wheel()
    assert wheel, "no wheel built"

    # Launch the MCP server via uvx from the local wheel.
    proc = subprocess.Popen(
        ["uvx", "--from", wheel, "semantic-trust-mcp"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke", "version": "0"},
        },
    }
    try:
        out, err = proc.communicate(json.dumps(init) + "\n", timeout=60)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        pytest.fail(f"MCP server timed out. stderr={err!r}")

    # Must contain a JSON-RPC result identifying the server as semantic-trust.
    assert '"result"' in out and "semantic-trust" in out, (
        f"MCP initialize handshake failed.\nstdout={out!r}\nstderr={err!r}"
    )

    # Parse and validate the response structure.
    response = json.loads(out.strip().splitlines()[0])
    assert response.get("jsonrpc") == "2.0"
    assert response.get("id") == 1
    result = response.get("result", {})
    assert result.get("serverInfo", {}).get("name") == "semantic-trust", (
        f"serverInfo.name is not 'semantic-trust': {result}"
    )
