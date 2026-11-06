#!/usr/bin/env python3
"""Check the Lisp propagator (bench/rules/pr.lisp) against bench/propagate.py on the same positions.

    selfplay/.venv/bin/python bench/propagate_check.py out/bench/prcheck/x-pr-check

Needs a run of x-pr-check with --trace.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "bench"), str(ROOT / "selfplay")]
from void_leads import facts  # noqa: E402
from propagate import positions  # noqa: E402


def main(directory):
    directory = Path(directory)
    direction = {r["deal"]: r["pass"] for r in map(json.loads, (directory / "deals.jsonl").open(newline=None))}
    log = {(r["deal"], r["trick"]): r for r in map(json.loads, (directory / "deals.jsonl.pr").open(newline=None))}
    same = different = 0
    for line in (directory / "tricks.jsonl").open(newline=None):
        deal = json.loads(line)
        d = direction[deal["deal"]]
        for p in positions(deal, None if d == "None" else d):
            row = log.get((deal["deal"], p["trick"]))
            if row is None:
                continue
            low, high, _ = facts(p)
            ok = list(low.flatten()) == row["low"] and list(high.flatten()) == row["high"]
            same += ok
            different += not ok
            if not ok and different < 4:
                print(deal["deal"], p["trick"], "python", low.flatten().tolist(), high.flatten().tolist(), "lisp", row["low"], row["high"])
    print(f"Lisp and Python bounds agree on {same} of {same + different} positions; {len(log)} logged")
    return 0 if same and not different else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
