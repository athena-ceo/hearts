#!/usr/bin/env python3
"""How much more can seat 1 deduce about the other hands by exact constraint propagation than it knows
from voids it has seen?  This is the method in section 3.4 of the 1986 report, measured on traced games.

    selfplay/.venv/bin/python bench/propagate.py out/bench/diff/expert [positions]

Facts come from cards seen, seat 1's hand, the voids opponents have shown, the cards seat 1 passed, and
how many cards each opponent still holds.  Cards of a suit are interchangeable apart from the passed
ones, so the bounds on how many cards of a suit each opponent holds form a transportation problem,
whose bounds an LP gives exactly.
"""
import collections
import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "selfplay"))
import hearts_sim as sim  # noqa: E402

SUITS = "CDHS"


def bounds(unpinned, need, void):
    """unpinned[suit], need[opp], void[opp] -> (low, high) matrices of free cards of each suit per opp."""
    variables = [(s, o) for s in range(4) for o in range(3) if not void[o][s]]
    index = {v: i for i, v in enumerate(variables)}
    a = np.zeros((7, len(variables)))
    b = np.zeros(7)
    for (s, o), i in index.items():
        a[s, i] = 1
        a[4 + o, i] = 1
    b[:4] = unpinned
    b[4:] = need
    low, high = np.zeros((4, 3), int), np.zeros((4, 3), int)
    for (s, o), i in index.items():
        c = np.zeros(len(variables))
        c[i] = 1
        lo = linprog(c, A_eq=a, b_eq=b, bounds=(0, None), method="highs")
        hi = linprog(-c, A_eq=a, b_eq=b, bounds=(0, None), method="highs")
        if not lo.success:
            raise ValueError("infeasible")
        low[s, o], high[s, o] = round(lo.fun), round(-hi.fun)
    return low, high


def positions(deal, direction):
    """Yield (trick, position, hand, seen, shown voids, pinned cards per opp, need per opp) before each seat-1 play."""
    hands = [list(h) for h in deal["hands"]]
    passed = deal["passed"]
    pinned = [[], [], []]
    if direction:
        target = sim.pass_target(1, direction)
        pinned[target - 2] = list(passed[0])
        received = [[], [], [], []]
        for i in range(4):
            received[sim.pass_target(i + 1, direction) - 1] = passed[i]
        hands = [[c for c in hands[i] if c not in passed[i]] + list(received[i]) for i in range(4)]
    voids = [[False] * 4 for _ in range(3)]
    seen = set()
    for number, trick in enumerate(deal["tricks"]):
        suit = trick["cards"][0][0]
        played = 0
        counts = [13 - number] * 3
        for offset, card in enumerate(trick["cards"]):
            seat = (trick["leader"] - 1 + offset) % 4 + 1
            if seat == 1:
                need = list(counts)
                yield {"trick": number + 1, "position": offset + 1, "hand": list(hands[0]), "seen": set(seen),
                       "truth": [list(hands[o + 1]) for o in range(3)],
                       "voids": [list(v) for v in voids], "pinned": [[c for c in p if c not in seen] for p in pinned],
                       "need": need}
            else:
                counts[seat - 2] -= 1
                if card[0] != suit:
                    voids[seat - 2][SUITS.index(suit)] = True
            hands[seat - 1].remove(card)
            seen.add(card)


def analyse(p):
    """Facts deduced beyond shown voids: new voids, sure holdings, and whether the queen's holder is known."""
    unseen = [c for c in sim.DECK if c not in p["seen"] and c not in p["hand"]]
    pinned_all = {c for x in p["pinned"] for c in x}
    unpinned = [sum(c[0] == s and c not in pinned_all for c in unseen) for s in SUITS]
    need = [p["need"][o] - len(p["pinned"][o]) for o in range(3)]
    low, high = bounds(unpinned, need, p["voids"])
    pinned_in = [[sum(c[0] == s for c in p["pinned"][o]) for s in SUITS] for o in range(3)]
    new_void = sure = 0
    for o in range(3):
        for si in range(4):
            held = sum(c[0] == SUITS[si] for c in p["truth"][o]) - pinned_in[o][si]
            assert low[si, o] <= held <= high[si, o], "a deduction contradicts the real hand"
            if not p["voids"][o][si] and high[si, o] == 0 and not pinned_in[o][si]:
                new_void += 1
            if low[si, o] > 0 and not pinned_in[o][si]:
                sure += 1
    queen = None
    if "SQ" in unseen:
        if "SQ" in pinned_all:
            queen = "passed"
        else:
            able = [o for o in range(3) if high[3, o] > 0]
            queen = "deduced" if len(able) == 1 and not all(p["voids"][x][3] for x in range(3) if x != able[0]) else (
                "seen voids" if len(able) == 1 else "open")
    return new_void, sure, queen


def main(directory, sample="4000"):
    directory = Path(directory)
    direction = {r["deal"]: r["pass"] for r in map(json.loads, (directory / "deals.jsonl").open(newline=None))}
    every = []
    for line in (directory / "tricks.jsonl").open(newline=None):
        deal = json.loads(line)
        d = direction[deal["deal"]]
        every += list(positions(deal, None if d == "None" else d))
    random.Random(1986).shuffle(every)
    every = every[:int(sample)]
    table = collections.defaultdict(lambda: collections.Counter())
    for p in every:
        new_void, sure, queen = analyse(p)
        group = table[(p["trick"] - 1) // 3]
        group["n"] += 1
        group["new void"] += new_void > 0
        group["sure holding"] += sure > 0
        group["voids"] += new_void
        group["queen " + str(queen)] += 1
    print("Tricks     n  any new void  any sure holding   new voids each   queen unseen: deduced  seen voids  passed  open")
    for key in sorted(table):
        g = table[key]
        unseen = g["queen deduced"] + g["queen seen voids"] + g["queen passed"] + g["queen open"]
        print(f"{3 * key + 1:2}-{min(13, 3 * key + 3):2} {g['n']:6} {g['new void'] / g['n']:12.1%} {g['sure holding'] / g['n']:17.1%}"
              f" {g['voids'] / g['n']:16.2f} {g['queen deduced']:21} {g['queen seen voids']:11} {g['queen passed']:7} {g['queen open']:5}")


if __name__ == "__main__":
    main(*sys.argv[1:])
