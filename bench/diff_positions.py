#!/usr/bin/env python3
"""Ask a network about every position the Expert actually faced, and list where the two disagree.

    selfplay/.venv/bin/python bench/diff_positions.py out/bench/diff/expert out/selfplay/a/final.json

Whole games can't be compared, since they diverge at the first different card.  Replaying the Expert's
own game gives the same position to both players.  Reads tricks.jsonl from a --trace run and writes
positions.jsonl beside it, with the Expert's reason for each play.  Two cards are "equivalent" as in
EP.Equivalent?: same suit, with every card between them already played or in this hand, so choosing
either changes nothing that matters.
"""
import collections
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "selfplay"))
import features  # noqa: E402
import hearts_sim as sim  # noqa: E402


class Network:
    def __init__(self, path):
        model = json.loads(Path(path).read_text())
        self.hidden = [(np.array(w, dtype=np.float32), np.array(b, dtype=np.float32)) for w, b in model["hidden"]]
        self.policy = (np.array(model["policy"][0], dtype=np.float32), np.array(model["policy"][1], dtype=np.float32))

    def scores(self, x):
        values = np.zeros(features.SIZE, dtype=np.float32)
        for index, value in x.items():
            values[index] = value * features.SCALED.get(index, 1)
        for weights, bias in self.hidden:
            values = np.maximum(0, weights @ values + bias)
        return self.policy[0] @ values + self.policy[1]

    def shares(self, request, selected=()):
        """Share of preference for each legal card, as the Thoughts window shows it."""
        x, legal = features.encode(request, selected)
        scores = self.scores(x)[legal]
        weights = np.exp(scores - scores.max())
        return {sim.DECK[i]: float(w) for i, w in zip(legal, weights / weights.sum())}

    def choose_pass(self, request):
        selected = []
        for _ in range(3):
            shares = self.shares(request, selected)
            selected.append(max(shares, key=shares.get))
        return selected


def equivalent(a, b, hand, played):
    if a == b:
        return True
    if a[0] != b[0]:
        return False
    low, high = sorted((sim.RANK_OF[a], sim.RANK_OF[b]))
    between = (a[0] + rank for rank in sim.RANKS[low + 1:high])
    return all(card in hand or card in played for card in between)


def strategy_of(reason):
    """The Expert's strategy at this play, as far as its reason says."""
    if reason.startswith(("Shoot", "Shooting")):
        return "Shooting"
    if reason.startswith("Eclipsing"):
        return "Eclipsing"
    return "Minimizing"


def replay(deal, direction, network):
    """Yield one record for seat 1's pass and for each of its plays."""
    hands = [list(h) for h in deal["hands"]]
    passed = deal["passed"]
    received = [[], [], [], []]
    records = []
    if direction:
        request = {"decision": "pass", "seat": 1, "deal": 1, "direction": direction, "hand": list(hands[0]),
                   "scores": [0, 0, 0, 0]}
        records.append({"deal": deal["deal"], "decision": "pass", "direction": direction, "hand": list(hands[0]),
                        "expert": passed[0], "network": network.choose_pass(request)})
        for i in range(4):
            received[sim.pass_target(i + 1, direction) - 1] = passed[i]
        hands = [[c for c in hands[i] if c not in passed[i]] + list(received[i]) for i in range(4)]
    reasons = list(reversed(deal["reasons"]))
    history = []
    broken = False
    leader = next(i + 1 for i in range(4) if "C2" in hands[i])
    plays = 0
    for number, trick in enumerate(deal["tricks"]):
        cards = []
        first = number == 0
        assert trick["leader"] == leader, deal["deal"]
        for offset, card in enumerate(trick["cards"]):
            seat = (leader - 1 + offset) % 4 + 1
            hand = hands[seat - 1]
            if seat == 1:
                legal = sim.legal_cards(hand, cards, broken, first)
                assert card in legal, (deal["deal"], card, legal)
                reason = reasons[plays].split(" ", 1)[1] if reasons else ""
                plays += 1
                if len(legal) > 1:
                    request = {"decision": "play", "seat": 1, "deal": 1, "direction": direction, "hand": list(hand),
                               "legal": legal, "trick": {"leader": leader, "cards": list(cards)},
                               "hearts_broken": broken, "first_trick": first, "passed": passed[0],
                               "received": received[0], "history": list(history), "scores": [0, 0, 0, 0]}
                    shares = network.shares(request)
                    choice = max(shares, key=shares.get)
                    played = {c for t in history for c in t["cards"]} | set(cards)
                    suit = cards[0][0] if cards else None
                    mode = "lead" if not cards else "follow" if card[0] == suit else "dump"
                    records.append({
                        "deal": deal["deal"], "decision": "play", "trick": number + 1, "position": offset + 1,
                        "mode": mode, "hand": list(hand), "legal": legal, "cards": list(cards),
                        "expert": card, "network": choice, "share_expert": round(shares[card], 4),
                        "share_network": round(shares[choice], 4), "reason": reason,
                        "strategy": strategy_of(reason), "same": card == choice,
                        "equivalent": equivalent(card, choice, hand, played),
                        "taken": [sum(sim.points(c) for t in history if t["winner"] == s + 1 for c in t["cards"])
                                  for s in range(4)],
                        "broken": broken, "queen_gone": "SQ" in played, "seen": sorted(played)})
            hand.remove(card)
            cards.append(card)
            broken = broken or card[0] == "H"
        leader = sim.trick_winner(leader, cards)
        assert leader == trick["winner"], deal["deal"]
        history.append({"leader": trick["leader"], "cards": cards, "winner": leader})
    return records


def table(title, rows, key, minimum=20):
    print(f"\n{title}\n{'n':>6} {'differ':>7} {'real':>7}  {'share':>6}")
    groups = collections.defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    for name, group in sorted(groups.items(), key=lambda kv: -sum(not r["equivalent"] for r in kv[1])):
        if len(group) < minimum:
            continue
        differ = sum(not r["same"] for r in group) / len(group)
        real = sum(not r["equivalent"] for r in group) / len(group)
        share = sum(r["share_expert"] for r in group) / len(group)
        print(f"{len(group):6} {differ:7.0%} {real:7.0%}  {share:6.2f}  {name}")


def main(directory, weights):
    directory = Path(directory)
    network = Network(weights)
    direction = {r["deal"]: r["pass"] for r in map(json.loads, (directory / "deals.jsonl").open(newline=None))}
    records = []
    for line in (directory / "tricks.jsonl").open(newline=None):
        deal = json.loads(line)
        records += replay(deal, None if direction[deal["deal"]] == "None" else direction[deal["deal"]], network)
    with (directory / "positions.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    plays = [r for r in records if r["decision"] == "play"]
    passes = [r for r in records if r["decision"] == "pass"]
    print(f"{len({r['deal'] for r in records})} deals, {len(plays)} plays with a real choice, {len(passes)} passes")
    print("differ: not the same card.  real: not an equivalent card.  share: the network's share for the Expert's card.")
    table("Overall", plays, lambda r: "all")
    table("By kind of play", plays, lambda r: f"{r['mode']} {r['position']}")
    table("By trick", plays, lambda r: f"trick {r['trick']:2}")
    table("By the Expert's strategy", plays, lambda r: r["strategy"])
    table("By the Expert's reason", plays, lambda r: r["reason"])
    overlap = collections.Counter(len(set(r["expert"]) & set(r["network"])) for r in passes)
    print(f"\nPasses: cards in common {sorted(overlap.items())}")
    only_expert = collections.Counter(c for r in passes for c in r["expert"] if c not in r["network"])
    only_network = collections.Counter(c for r in passes for c in r["network"] if c not in r["expert"])
    print("Passed only by the Expert:", only_expert.most_common(14))
    print("Passed only by the network:", only_network.most_common(14))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
