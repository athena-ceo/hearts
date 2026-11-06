#!/usr/bin/env python3
"""Where does a player in seat 1 lose its points?  Reads tricks.jsonl from a --trace run.

    python3 bench/analyze_expert.py out/bench/train/expert
"""
import collections
import json
import sys
from pathlib import Path


def points(card):
    return 13 if card == "SQ" else 1 if card[0] == "H" else 0


def main(directory):
    deals = [json.loads(l) for l in (Path(directory) / "tricks.jsonl").open(newline=None) if l.strip()]
    by_reason = collections.Counter()
    plays = collections.Counter()
    queen = collections.Counter()
    strategy_deals = collections.Counter()
    strategy_points = collections.Counter()
    for deal in deals:
        reasons = list(reversed(deal.get("reasons", [])))
        total = 0
        kinds = set()
        for number, trick in enumerate(deal["tricks"]):
            seat_index = (1 - trick["leader"]) % 4
            reason = " ".join(reasons[number].split(" ")[1:]) if number < len(reasons) else "?"
            plays[reason] += 1
            kinds.add(reason.split(" ")[0])
            worth = sum(points(c) for c in trick["cards"])
            if trick["winner"] == 1 and worth:
                by_reason[reason] += worth
                total += worth
                if "SQ" in trick["cards"]:
                    mine = trick["cards"][seat_index] == "SQ"
                    dealt = "SQ" in deal["hands"][0] and "SQ" not in deal["passed"][0]
                    queen[("played my own" if mine else "someone dumped it on me",
                           "kept it" if dealt else "received or not dealt")] += 1
        label = "Eclipsing" if "Eclipsing" in kinds else "Shooting" if any(k.startswith("Shoot") for k in kinds) else "Minimizing"
        strategy_deals[label] += 1
        strategy_points[label] += total
    print(len(deals), "deals; raw points taken by seat 1:", sum(by_reason.values()))
    print("\nStrategy that showed up in the deal:")
    for label, count in strategy_deals.most_common():
        print(f"  {label:12} {count:5} deals  {strategy_points[label] / count:5.2f} raw points per deal")
    print("\nQueen of spades taken by seat 1:")
    for key, count in queen.most_common():
        print(f"  {count:5}  {key[0]}, {key[1]}")
    print("\nPoints taken on tricks where seat 1's play had this reason:")
    for reason, worth in by_reason.most_common(25):
        print(f"  {worth:6} points  {plays[reason]:6} plays  {worth / plays[reason]:5.2f}  {reason}")


if __name__ == "__main__":
    main(sys.argv[1])
