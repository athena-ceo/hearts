#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""Which of the Expert's rules fire, over many deals of self-play: how often, and which never do.

    .venv/bin/python scripts/rule_coverage.py [--deals 2000] [--variant x-sr-plus] [--all]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rulebook import coverage  # noqa: E402

from hearts import Game  # noqa: E402
from hearts.players import Expert  # noqa: E402
from hearts.players.base import play_game  # noqa: E402
from hearts.players.expert import RULES_1986, variant  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--deals", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", help="a file in players/expert/variants, or a path")
    parser.add_argument("--all", action="store_true", help="also show how often each rule fired")
    args = parser.parse_args()
    rules = variant(args.variant) if args.variant else RULES_1986
    fired = []
    play_game([Expert(rules=rules, trace=fired) for _ in range(4)], Game(seed=args.seed, over_score=10 ** 9), deals=args.deals)
    counts = collections.Counter(fired)
    if args.all:
        for name, count in counts.most_common():
            print(f"{count:8}  {name}")
    print(f"{len(fired)} firings in {args.deals} deals.  Never fired:")
    for rule_class, names in coverage(rules, counts).items():
        if names:
            print(f"  {rule_class}: {', '.join(names)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
