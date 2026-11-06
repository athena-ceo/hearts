#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decisions Systems SAS.
"""Compare the Python players with a traced Medley run: every seat's passes, every card, reason, score and rule fired.

    python3 bench/run.py --run conform --deals 6000 --trace expert conservative-table mixed-table
    .venv/bin/python scripts/medley_conformance.py out/bench/conform/expert
    .venv/bin/python scripts/medley_conformance.py out/bench/conform/conservative-table --deals 1000

The player follows from the directory unless given.  Exits 0 only if there is no mismatch.  --fixture writes a test
fixture from the run's first --deals deals.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from hearts.conformance import Report, Table, describe, load_run, write_fixture  # noqa: E402
from hearts.players.expert import RULES_1986  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run", help="a traced run: out/bench/RUN/PLAYER")
    parser.add_argument("--kind", choices=["expert", "conservative", "mixed"], help="default: from the directory name")
    parser.add_argument("--deals", type=int, help="only the first so many deals")
    parser.add_argument("--show", type=int, default=1, help="how many mismatches to describe")
    parser.add_argument("--personality", type=json.loads, help="JSON: personality values for all Experts, as the run had")
    parser.add_argument("--personality1", type=json.loads, help="JSON: personality values for seat 1, as the run had")
    parser.add_argument("--fixture", help="write the first --deals deals to this gzipped fixture instead")
    args = parser.parse_args()
    records = load_run(args.run, args.deals)
    if args.fixture:
        write_fixture(records, args.fixture)
        print(f"{len(records)} deals in {args.fixture}, {Path(args.fixture).stat().st_size} bytes")
        return 0
    name = Path(args.run).name
    kind = args.kind or ("conservative" if "conservative" in name else "mixed" if "mixed" in name else "expert")
    start = time.perf_counter()
    rules = RULES_1986.overlay(parameters=args.personality) if args.personality else None
    rules_1 = RULES_1986.overlay(parameters=args.personality1) if args.personality1 else None
    report = Table(kind, Report(keep=max(args.show, 1)), rules, rules_1).play(records)
    seconds = time.perf_counter() - start
    print(f"{kind}, {args.run}")
    print(report.summary())
    print(f"{seconds:.1f} s, {report.deals / seconds:.1f} deals a second")
    for mismatch in report.first[:args.show]:
        print(describe(mismatch))
    return 0 if report.clean else 1


if __name__ == "__main__":
    sys.exit(main())
