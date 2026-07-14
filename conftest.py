import sys
import pathlib

# Make the repo root importable so `scripts/` and other non-package dirs are
# accessible in tests without installing them as packages.
sys.path.insert(0, str(pathlib.Path(__file__).parent))
