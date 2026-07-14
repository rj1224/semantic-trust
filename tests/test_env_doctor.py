from scripts.env_doctor import check, HARD


def test_check_reports_hard_requirements():
    rows = check()
    names = {n for n, _, _ in rows}
    assert HARD <= names  # every hard req is checked
    assert "python>=3.11" in names and "uv" in names and "pyyaml" in names


def test_python_and_pyyaml_present_in_this_env():
    rows = {n: ok for n, ok, _ in check()}
    assert rows["python>=3.11"] is True  # run under uv's 3.12
    assert rows["pyyaml"] is True  # installed via .[dev]
