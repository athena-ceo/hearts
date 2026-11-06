#!/usr/bin/env python3
"""How do the network and the Expert differ around the moon?  Pairs --trace runs on the same deals.

    selfplay/.venv/bin/python bench/moon_stats.py out/bench/diff/expert out/bench/diff/np-HEARTSNET
"""
import collections
import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "selfplay"))
import hearts_sim as sim  # noqa: E402


def load(directory):
    deals = {r["deal"]: r for r in map(json.loads, (Path(directory) / "deals.jsonl").open(newline=None))}
    for line in (Path(directory) / "tricks.jsonl").open(newline=None):
        d = json.loads(line)
        deals[d["deal"]].update(d)
    return deals


def after_pass(row):
    if row["pass"] == "None":
        return list(row["hands"][0])
    target = {"Left": 3, "Across": 2, "Right": 1}[row["pass"]]  # Who passes to seat 1.
    return [c for c in row["hands"][0] if c not in row["passed"][0]] + list(row["passed"][target])


def profile(hand):
    rank = sim.RANK_OF
    suits = collections.Counter(c[0] for c in hand)
    return {
        "aces": sum(rank[c] == 12 for c in hand), "kings": sum(rank[c] == 11 for c in hand),
        "high (J+)": sum(rank[c] >= 9 for c in hand), "low (2-6)": sum(rank[c] <= 4 for c in hand),
        "rank sum": sum(rank[c] for c in hand) / 13,
        "hearts": suits["H"], "high hearts (J+)": sum(c[0] == "H" and rank[c] >= 9 for c in hand),
        "spades": suits["S"], "SQ": "SQ" in hand, "SA or SK": "SA" in hand or "SK" in hand,
        "longest": max(suits.values()), "voids": 4 - len(suits),
    }


def describe(title, hands):
    rows = [profile(h) for h in hands]
    print(f"\n{title} (n={len(rows)})")
    for key in rows[0]:
        print(f"  {key:18} {st.mean(float(r[key]) for r in rows):6.2f}")


def bucket(score):
    return ("moon" if score == -26 else "0" if score == 0 else "1-5" if score < 6 else "6-12" if score < 13
            else "13-18" if score < 19 else "19-25")


def main(expert_dir, net_dir):
    ex, net = load(expert_dir), load(net_dir)
    deals = sorted(set(ex) & set(net))
    for name, rows in (("Expert", ex), ("Network", net)):
        c = collections.Counter(bucket(rows[d]["scores"][0]) for d in deals)
        print(name, {k: c[k] for k in ("moon", "0", "1-5", "6-12", "13-18", "19-25")},
              "other moons", sum(-26 in rows[d]["scores"][1:] for d in deals))
    both = [d for d in deals if net[d]["scores"][0] == -26 and ex[d]["scores"][0] == -26]
    only_net = [d for d in deals if net[d]["scores"][0] == -26 and ex[d]["scores"][0] != -26]
    only_ex = [d for d in deals if ex[d]["scores"][0] == -26 and net[d]["scores"][0] != -26]
    print(f"Both shot {len(both)}, only the network {len(only_net)}, only the Expert {len(only_ex)}")
    print("On deals only the network shot, the Expert scored",
          sorted(collections.Counter(bucket(ex[d]["scores"][0]) for d in only_net).items()))
    print("Who shot instead on those deals in the Expert's game:",
          sum(-26 in ex[d]["scores"][1:] for d in only_net))
    # Tricks won before hearts are in danger, per deal, in shot deals: when does it start running the table?
    describe("Network's hand after the pass, moon", [after_pass(net[d]) for d in deals if net[d]["scores"][0] == -26])
    describe("Network's hand after the pass, no moon", [after_pass(net[d]) for d in deals if net[d]["scores"][0] != -26])
    describe("Expert's hand after the pass, moon", [after_pass(ex[d]) for d in deals if ex[d]["scores"][0] == -26])
    describe("Dealt hand on deals only the network shot", [net[d]["hands"][0] for d in only_net])
    describe("Dealt hand on other deals", [net[d]["hands"][0] for d in deals if d not in set(only_net)])
    # Trapped: took a lot of points but no moon, the price of trying.
    for name, rows in (("Expert", ex), ("Network", net)):
        hi = [rows[d]["scores"][0] for d in deals if rows[d]["scores"][0] >= 13]
        print(name, "13+ deals", len(hi), "mean", round(st.mean(hi), 1) if hi else "-",
              "total points", sum(hi), "of", sum(rows[d]["scores"][0] for d in deals))
    # Passing by rank, as a share of times the card was dealt.
    for name, rows in (("Expert", ex), ("Network", net)):
        dealt, gone = collections.Counter(), collections.Counter()
        for d in deals:
            r = rows[d]
            if r["pass"] == "None":
                continue
            dealt.update(r["hands"][0])
            gone.update(r["passed"][0])
        print(f"\n{name}: share passed when dealt\n     " + " ".join(f"{x:>4}" for x in sim.RANKS))
        for s in "CDHS":
            print(f"  {s}  " + " ".join(f"{gone[s + x] / max(1, dealt[s + x]):4.0%}" for x in sim.RANKS))


if __name__ == "__main__":
    main(*sys.argv[1:])
