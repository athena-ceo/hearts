#!/usr/bin/env python3
"""What do propagated voids and singletons say about leads?  Joins traced tricks with bench/propagate.py.

    selfplay/.venv/bin/python bench/void_leads.py out/bench/diff/expert

For a lead into a suit, it counts opponents who can't hold the suit (they may discard points) and opponents
who hold exactly one card of it (their play is forced), and compares the Expert's and the network's leads.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "bench"))
sys.path.insert(0, str(ROOT / "selfplay"))
import hearts_sim as sim  # noqa: E402
from propagate import SUITS, bounds, positions  # noqa: E402


def facts(p):
    """For each suit, per opponent: (low, high) cards held, passed cards included."""
    unseen = [c for c in sim.DECK if c not in p["seen"] and c not in p["hand"]]
    pinned_all = {c for x in p["pinned"] for c in x}
    unpinned = [sum(c[0] == s and c not in pinned_all for c in unseen) for s in SUITS]
    need = [p["need"][o] - len(p["pinned"][o]) for o in range(3)]
    low, high = bounds(unpinned, need, p["voids"])
    pinned = np.array([[sum(c[0] == s for c in p["pinned"][o]) for o in range(3)] for s in SUITS])
    return low + pinned, high + pinned, unseen


def describe(card, low, high, unseen):
    s = SUITS.index(card[0])
    voids = sum(high[s, o] == 0 for o in range(3))
    singles = sum(low[s, o] == 1 and high[s, o] == 1 for o in range(3))
    higher_out = any(c[0] == card[0] and sim.RANK_OF[c] > sim.RANK_OF[card] for c in unseen)
    return {"voids": voids, "singles": singles, "can_lose": higher_out}


def main(directory):
    directory = Path(directory)
    direction = {r["deal"]: r["pass"] for r in map(json.loads, (directory / "deals.jsonl").open(newline=None))}
    decided = {}
    for line in (directory / "positions.jsonl").open():
        r = json.loads(line)
        if r["decision"] == "play":
            decided[(r["deal"], r["trick"])] = r
    tally = collections.defaultdict(lambda: collections.Counter())
    for line in (directory / "tricks.jsonl").open(newline=None):
        deal = json.loads(line)
        d = direction[deal["deal"]]
        for p in positions(deal, None if d == "None" else d):
            r = decided.get((deal["deal"], p["trick"]))
            if not r or r["mode"] != "lead" or r["strategy"] != "Minimizing":
                continue
            low, high, unseen = facts(p)
            trick = deal["tricks"][p["trick"] - 1]
            pts = sum(sim.points(c) for c in trick["cards"])
            mine = trick["winner"] == 1
            options = [describe(c, low, high, unseen) for c in r["legal"]]
            for key_name, key in (("voids", lambda f: f["voids"]), ("singles", lambda f: f["singles"])):
                e, n = describe(r["expert"], low, high, unseen), describe(r["network"], low, high, unseen)
                for who, f in (("expert", e), ("network", n)):
                    tally[(key_name, key(f), f["can_lose"])][who] += 1
                tally[(key_name, key(e), e["can_lose"])]["cost"] += pts if mine else 0
                tally[(key_name, key(e), e["can_lose"])]["won"] += mine
                tally[(key_name, key(e), e["can_lose"])]["pts"] += pts
    print("Minimizing leads, by what is known about the suit led.  Cost: points the Expert took on that trick.")
    print(f"{'fact':8} {'count':>5} {'can lose':>8} {'Expert':>7} {'Network':>8} {'won':>6} {'cost':>6} {'trick pts':>9}")
    for key in sorted(tally, key=str):
        t = tally[key]
        n = max(1, t["expert"])
        print(f"{key[0]:8} {key[1]:5} {str(key[2]):>8} {t['expert']:7} {t['network']:8} {t['won'] / n:6.0%} {t['cost'] / n:6.2f} {t['pts'] / n:9.2f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
