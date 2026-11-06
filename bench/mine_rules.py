#!/usr/bin/env python3
"""Fit a small decision tree to the network's choices in a group of positions, in the Expert's terms.

    selfplay/.venv/bin/python bench/mine_rules.py Shooting lead 4 out/bench/diff/expert

A candidate card is a row, and the label says whether the network chose it.  The tree imitates the
network, so it only suggests rules: the benchmark decides whether a rule is worth having.
"""
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "selfplay"))
import hearts_sim as sim  # noqa: E402

NAMES = ["rank", "cards_out_above", "cards_out_below", "cards_out_in_suit", "my_cards_in_suit", "my_cards_above",
         "my_cards_below", "is_winner", "is_lowest_out", "is_heart", "is_spade", "is_SQ", "i_hold_SQ", "queen_gone",
         "trick", "hearts_broken", "my_winners_total", "my_points_taken", "others_points_taken"]


def candidate(card, row):
    hand, seen, suit = row["hand"], set(row["seen"]), card[0]
    above = [c for c in sim.DECK if c[0] == suit and sim.RANK_OF[c] > sim.RANK_OF[card] and c not in hand and c not in seen]
    below = [c for c in sim.DECK if c[0] == suit and sim.RANK_OF[c] < sim.RANK_OF[card] and c not in hand and c not in seen]
    mine = [c for c in hand if c[0] == suit]
    winners = 0
    for s in "CDHS":
        mine_s = sorted((c for c in hand if c[0] == s), key=sim.RANK_OF.get)
        if mine_s and not [c for c in sim.DECK if c[0] == s and sim.RANK_OF[c] > sim.RANK_OF[mine_s[-1]]
                           and c not in hand and c not in seen]:
            winners += 1
    return [sim.RANK_OF[card], len(above), len(below), len(above) + len(below), len(mine),
            sum(sim.RANK_OF[c] > sim.RANK_OF[card] for c in mine), sum(sim.RANK_OF[c] < sim.RANK_OF[card] for c in mine),
            not above, not below, suit == "H", suit == "S", card == "SQ", "SQ" in hand, row["queen_gone"],
            row["trick"], row["broken"], winners, row["taken"][0], sum(row["taken"][1:])]


def load(paths, strategy, mode):
    rows = []
    for path in paths:
        for line in (Path(path) / "positions.jsonl").open():
            r = json.loads(line)
            if r["decision"] != "play" or r["mode"] != mode:
                continue
            if strategy == "any" or r["strategy"] == strategy or (strategy == "Shooting" and r["reason"] == "The network's card."):
                rows.append(r)
    return rows


def main(strategy, mode, depth, *paths):
    rows = load(paths, strategy, mode)
    rng = np.random.default_rng(1986)
    order = rng.permutation(len(rows))
    fit, check = [rows[i] for i in order[len(rows) // 3:]], [rows[i] for i in order[:len(rows) // 3]]
    X, y = [], []
    for r in fit:
        for card in r["legal"]:
            X.append(candidate(card, r))
            y.append(card == r["network"])
    tree = DecisionTreeClassifier(max_depth=int(depth), min_samples_leaf=25, random_state=0).fit(np.array(X, float), y)
    hits = hits_expert = 0
    for r in check:
        p = tree.predict_proba(np.array([candidate(c, r) for c in r["legal"]], float))[:, 1]
        pick = r["legal"][int(np.argmax(p))]
        hits += pick == r["network"]
        hits_expert += r["expert"] == r["network"]
    print(f"{len(rows)} positions.  On {len(check)} unseen ones the tree picks the network's card {hits / len(check):.0%} of the time; "
          f"the Expert's rules {hits_expert / len(check):.0%}; random {np.mean([1 / len(r['legal']) for r in check]):.0%}")
    print(export_text(tree, feature_names=NAMES, show_weights=False, class_names=None))
    importance = sorted(zip(tree.feature_importances_, NAMES), reverse=True)[:8]
    print("important:", [(n, round(float(v), 2)) for v, n in importance])


if __name__ == "__main__":
    main(*sys.argv[1:])
