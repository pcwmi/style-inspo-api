#!/usr/bin/env python3
"""
Run the SMS assertion suite: execute eval cases, grade them, gate the result.

This is the "run the evals before shipping" entry point. It reuses the scenario
runner from run_sms_eval.py, then grades each scenario's `expectations` block
with grader.py.

Exit codes:
    0  all GUARD cases passed (TARGET failures are reported but non-fatal)
    1  at least one GUARD case failed  -> block the push
    2  setup error (missing creds, bad fixture, etc.)

Usage:
    cd backend/tests/sms_eval
    python scripts/run_assertions.py                 # full suite
    python scripts/run_assertions.py --tier target   # only the in-progress fixes
    python scripts/run_assertions.py --id T3_rationale_survives
    python scripts/run_assertions.py --no-judge      # skip LLM-judge assertions
    python scripts/run_assertions.py --results-dir <dir>  # grade a prior run, no re-run
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(Path(__file__).parent))  # for grader import

import grader  # noqa: E402

CASES_PATH = Path(__file__).parent.parent / "fixtures" / "assertion_cases.json"

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"


def _load_cases():
    with open(CASES_PATH) as f:
        return json.load(f)


def _status_icon(status):
    return {grader.PASS: f"{GREEN}PASS{RESET}",
            grader.FAIL: f"{RED}FAIL{RESET}",
            grader.SKIP: f"{YELLOW}SKIP{RESET}"}.get(status, status)


def main():
    p = argparse.ArgumentParser(description="Run + grade the SMS assertion suite")
    p.add_argument("--tier", choices=["guard", "target"], help="Run only this tier")
    p.add_argument("--id", help="Run a single case by id")
    p.add_argument("--no-judge", action="store_true", help="Skip llm_judge assertions")
    p.add_argument("--results-dir", help="Grade an existing raw_results.json instead of re-running")
    p.add_argument("--output", help="Where to write graded results")
    args = p.parse_args()

    cases = _load_cases()
    if args.tier:
        cases = [c for c in cases if c["expectations"]["tier"] == args.tier]
    if args.id:
        cases = [c for c in cases if c["id"] == args.id]
    if not cases:
        print("No matching cases.")
        return 2

    by_id = {c["id"]: c for c in cases}

    # --- obtain results (re-run or load) ---
    if args.results_dir:
        rf = Path(args.results_dir) / "raw_results.json"
        if not rf.exists():
            print(f"{RED}No raw_results.json in {args.results_dir}{RESET}")
            return 2
        with open(rf) as f:
            results = json.load(f)
        out_dir = Path(args.results_dir)
    else:
        try:
            from run_sms_eval import run_scenario
        except Exception as e:  # noqa: BLE001
            print(f"{RED}Could not import the scenario runner: {e}{RESET}")
            print("This step needs backend deps + OPENAI/S3 creds (a real .env).")
            return 2

        print(f"Running {len(cases)} assertion case(s)...\n")
        wardrobe_cache, results = {}, []
        for c in cases:
            print(f"  • {c['name']}")
            try:
                results.append(run_scenario(c, 0, wardrobe_cache))
            except Exception as e:  # noqa: BLE001
                print(f"    {RED}run error: {e}{RESET}")
                results.append({"scenario_id": c["id"], "scenario_name": c["name"],
                                "turns": [{"turn": 1, "success": False, "error": str(e)}]})
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = Path(args.output) if args.output else (
            Path(__file__).parent.parent / "results" / f"assert_{stamp}")
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "raw_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)

    if args.no_judge:
        os.environ.pop("OPENAI_API_KEY", None)  # forces llm_judge -> SKIP

    # --- grade ---
    graded = []
    for r in results:
        case = by_id.get(r.get("scenario_id"))
        if not case:
            continue
        graded.append(grader.grade_scenario(r, case["expectations"]))

    # --- report ---
    print(f"\n{'=' * 72}\nASSERTION RESULTS\n{'=' * 72}")
    guard_fail = target_fail = 0
    for g in graded:
        tier = g["tier"].upper()
        head = f"{GREEN}PASS{RESET}" if g["passed"] else f"{RED}FAIL{RESET}"
        print(f"\n[{tier}] {head}  {g['scenario_name']}")
        for a in g["assertions"]:
            print(f"    {_status_icon(a['status'])}  {a['id']} ({a['type']}) {DIM}— {a['detail']}{RESET}")
        if not g["passed"]:
            if g["tier"] == "guard":
                guard_fail += 1
            else:
                target_fail += 1

    n = len(graded)
    n_pass = sum(1 for g in graded if g["passed"])
    print(f"\n{'=' * 72}")
    print(f"{n_pass}/{n} cases passed   "
          f"({RED}{guard_fail} GUARD fail{RESET}, {YELLOW}{target_fail} TARGET fail{RESET})")
    print(f"Results: {out_dir}")
    if guard_fail:
        print(f"\n{RED}✗ GUARD regression — do not ship.{RESET}")
        return 1
    if target_fail:
        print(f"\n{YELLOW}△ Guards green. {target_fail} target(s) still open (expected until fixed).{RESET}")
    else:
        print(f"\n{GREEN}✓ All guards and targets green.{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
