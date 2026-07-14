"""
Golden-case harness for the deterministic trust engine.
Runs build_report over each runnable golden case and asserts the expected band + gates.

AD-4: This module is a CLI + integration check, not a pytest test file.
      Scorer unit coverage lives in tests/test_scorer.py.
      CI runs this via: python -m eval.harness (see .github/workflows/ci.yml).
"""

import json
import sys
import os

# Allow running from the repo root without installing.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from trust.cli import build_report


def run_golden_cases(path: str = "eval/golden_cases.json") -> list:
    with open(path, encoding="utf-8") as fh:
        cases = json.load(fh)
    results = []
    for c in cases:
        if not c.get("runnable", True):
            continue
        rep = build_report(c["input_model"], c["model_name"])
        band_ok = rep.get("band") == c["expected_band"]
        gates_ok = rep.get("gates") == c["expected_gates"]
        passed = band_ok and gates_ok
        results.append(
            {
                "id": c["id"],
                "spec": c.get("spec", ""),
                "passed": passed,
                "expected": {"band": c["expected_band"], "gates": c["expected_gates"]},
                "actual": {"band": rep.get("band"), "gates": rep.get("gates")},
            }
        )
    return results


def main():
    results = run_golden_cases()
    any_fail = False
    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        if not r["passed"]:
            any_fail = True
        print(f"{status}  [{r['spec']:6}]  {r['id']}")
        if not r["passed"]:
            print(f"       expected: {r['expected']}")
            print(f"       actual:   {r['actual']}")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
