#!/usr/bin/env python3
"""Compare rule variants with a baseline on the same deals, by points and by margin.

    python3 bench/compare.py --run train --baseline expert

Margin is seat 1's points minus the average of the other three, so a moon shot by an opponent counts
against you, as it does in a real game.  Lower is better for both.
"""
import argparse
import json
import random
import statistics as st
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(directory):
    return {r["deal"]: r for r in map(json.loads, (directory / "deals.jsonl").open(newline=None))}


def margin(row):
    scores = row["scores"]
    return scores[0] - sum(scores[1:]) / 3


def interval(values):
    rng = random.Random(1986)
    means = sorted(sum(rng.choices(values, k=len(values))) / len(values) for _ in range(5000))
    return means[125], means[4875]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default="train")
    parser.add_argument("--baseline", default="expert")
    args = parser.parse_args()
    root = ROOT / "out" / "bench" / args.run
    base = load(root / args.baseline)
    print(f"{args.baseline}: {len(base)} deals, {st.fmean(r['scores'][0] for r in base.values()):.3f} points, "
          f"{st.fmean(margin(r) for r in base.values()):.3f} margin, "
          f"{sum(r['scores'][0] == -26 for r in base.values())} moons shot, "
          f"{sum(-26 in r['scores'][1:] for r in base.values())} moons by others")
    for directory in sorted(root.iterdir()):
        if directory.name == args.baseline or not (directory / "deals.jsonl").exists():
            continue
        rows = load(directory)
        deals = sorted(set(rows) & set(base))
        points = [rows[d]["scores"][0] - base[d]["scores"][0] for d in deals]
        margins = [margin(rows[d]) - margin(base[d]) for d in deals]
        low, high = interval(points)
        mlow, mhigh = interval(margins)
        print(f"{directory.name:22} n={len(deals):<5} changed {sum(p != 0 for p in points) / len(points):4.0%}  "
              f"points {st.fmean(points):+.3f} [{low:+.2f},{high:+.2f}]  "
              f"margin {st.fmean(margins):+.3f} [{mlow:+.2f},{mhigh:+.2f}]  "
              f"moons {sum(rows[d]['scores'][0] == -26 for d in deals)}/"
              f"{sum(-26 in rows[d]['scores'][1:] for d in deals)}")


if __name__ == "__main__":
    main()
