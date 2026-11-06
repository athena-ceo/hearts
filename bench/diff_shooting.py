#!/usr/bin/env python3
"""Describe the cards the Expert and the network choose in a group of positions, in the Expert's terms.

    selfplay/.venv/bin/python bench/diff_shooting.py out/bench/diff/expert Shooting lead
"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "selfplay"))
import hearts_sim as sim  # noqa: E402


def attributes(card, row):
    """What kind of card this is, given what has been seen."""
    hand = row["hand"]
    suit = card[0]
    played = set()
    # positions.jsonl has no history, so unseen cards come from "seen" if present.
    played |= set(row.get("seen", []))
    above = [c for c in sim.DECK if c[0] == suit and sim.RANK_OF[c] > sim.RANK_OF[card] and c not in hand and c not in played]
    below = [c for c in sim.DECK if c[0] == suit and sim.RANK_OF[c] < sim.RANK_OF[card] and c not in hand and c not in played]
    mine = sorted((c for c in hand if c[0] == suit), key=sim.RANK_OF.get)
    return {
        "winner (nothing above is out)": not above,
        "loser (nothing below is out)": not below,
        "top of my suit": card == mine[-1],
        "bottom of my suit": card == mine[0],
        "suit " + suit: True,
        "longest suit": len(mine) == max(sum(c[0] == s for c in hand) for s in "CDHS"),
        "shortest suit": len(mine) == min(n for n in (sum(c[0] == s for c in hand) for s in "CDHS") if n),
    }


def main(directory, strategy, mode):
    rows = [json.loads(l) for l in (Path(directory) / "positions.jsonl").open()]
    rows = [r for r in rows if r["decision"] == "play" and (strategy == "any" or r["strategy"] == strategy)
            and (mode == "any" or r["mode"] == mode)]
    seen = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        for who, card in enumerate((r["expert"], r["network"])):
            for key, value in attributes(card, r).items():
                if value:
                    seen[key][who] += 1
    print(f"{strategy} / {mode}: {len(rows)} positions, differ {sum(not r['same'] for r in rows) / len(rows):.0%},"
          f" real {sum(not r['equivalent'] for r in rows) / len(rows):.0%}")
    print(f"{'':32} {'Expert':>7} {'Network':>8}")
    for key, (e, n) in sorted(seen.items(), key=lambda kv: -abs(kv[1][0] - kv[1][1])):
        print(f"{key:32} {e / len(rows):7.0%} {n / len(rows):8.0%}")
    by_trick = collections.defaultdict(list)
    for r in rows:
        by_trick[(r["trick"] - 1) // 3].append(r)
    for k in sorted(by_trick):
        g = by_trick[k]
        print(f"tricks {3 * k + 1}-{3 * k + 3}: n={len(g)} real {sum(not r['equivalent'] for r in g) / len(g):.0%}")
    examples = [r for r in rows if not r["equivalent"]][:8]
    for r in examples:
        print(f"  deal {r['deal']} trick {r['trick']} hand {' '.join(sorted(r['hand']))}  Expert {r['expert']} ({r['reason'][:40]})  network {r['network']} {r['share_network']:.0%}")


if __name__ == "__main__":
    main(*sys.argv[1:])
