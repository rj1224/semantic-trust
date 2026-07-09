import importlib.util, os, shutil, sys

def _has_module(name): return importlib.util.find_spec(name) is not None
def _on_path(cmd): return shutil.which(cmd) is not None

HARD = {"python>=3.11", "pyyaml", "uv"}

def check():
    """Return [(name, ok, detail)]. Hard requirements + soft warnings."""
    return [
        ("python>=3.11", sys.version_info >= (3, 11), f"{sys.version_info.major}.{sys.version_info.minor}"),
        ("pyyaml", _has_module("yaml"), "import yaml"),
        ("uv", _on_path("uv"), "uvx launch mechanism (AD-1)"),
        ("dbt", _on_path("dbt"), "warn: needed for `mf validate-configs`"),
        ("mf", _on_path("mf"), "warn: MetricFlow CLI"),
        ("gh", _on_path("gh"), "warn: PR workflow"),
        ("dbt_project.yml in CWD", os.path.exists("dbt_project.yml"), "warn: run from a dbt project root (AD-2)"),
    ]

def main():
    rows = check()
    width = max(len(n) for n, _, _ in rows)
    for name, ok, detail in rows:
        print(f"{'OK ' if ok else 'XX '} {name.ljust(width)}  {detail}")
    missing = [n for n, ok, _ in rows if not ok and n in HARD]
    if missing:
        print(f"\nMissing hard requirements: {', '.join(missing)}")
        sys.exit(1)
    sys.exit(0)

if __name__ == "__main__":
    main()
