import os
from unittest import mock
from trust import compile as compile_mod

def test_compile_ok_when_parse_succeeds_and_artifact_exists(tmp_path):
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "semantic_manifest.json").write_text("{}")
    fake = mock.Mock(returncode=0, stdout="ok", stderr="")
    with mock.patch("trust.compile.subprocess.run", return_value=fake):
        res = compile_mod.compile_manifest(str(tmp_path))
    assert res["ok"] is True
    assert res["manifest_path"].endswith("target/semantic_manifest.json")

def test_compile_not_ok_when_artifact_absent(tmp_path):
    fake = mock.Mock(returncode=0, stdout="", stderr="")
    with mock.patch("trust.compile.subprocess.run", return_value=fake):
        res = compile_mod.compile_manifest(str(tmp_path))
    assert res["ok"] is False
