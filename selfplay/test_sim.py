#!/usr/bin/env python3
"""Check the simulator against real Medley games.  A mismatch here would quietly ruin training.

    python3 selfplay/test_sim.py

Uses benchmark logs in out/bench/: requests the 1986 code really produced (legal cards, winners,
hearts broken) and whole traced deals (passes and scores).
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).parent))
import features  # noqa: E402
import hearts_sim as sim  # noqa: E402
from bots import DuckBot, RandomBot  # noqa: E402

PILOT = ROOT / "out" / "bench" / "pilot"
TRACE = ROOT / "out" / "bench" / "analysis-trace" / "expert"


def requests():
    for name in ("haiku", "opus-medium", "mistral", "gemma2"):
        path = PILOT / name / "decisions.jsonl"
        if path.exists():
            for line in path.open(newline=None):
                if line.strip():
                    yield json.loads(line)["request"]


def direction_of(number):
    return sim.DIRECTIONS[(number - 1) % 4]


class AgainstRealRequests(unittest.TestCase):
    def test_legal_cards_winners_and_flags(self):
        plays = 0
        for req in requests():
            if req["decision"] != "play":
                continue
            plays += 1
            legal = sim.legal_cards(req["hand"], req["trick"]["cards"], req["hearts_broken"], req["first_trick"])
            self.assertEqual(sorted(legal), sorted(req["legal"]), req)
            history = req.get("history") or []
            for trick in history:
                self.assertEqual(sim.trick_winner(trick["leader"], trick["cards"]), trick["winner"], trick)
            played = [c for t in history for c in t["cards"]] + req["trick"]["cards"]
            self.assertEqual(any(c[0] == "H" for c in played), req["hearts_broken"], req)
            self.assertEqual(req["first_trick"], not history)
            if len(req["trick"]["cards"]) and history:
                self.assertEqual(req["trick"]["leader"], history[-1]["winner"])
            x, encoded_legal = features.encode(req)
            self.assertEqual(sorted(encoded_legal), sorted(sim.INDEX[c] for c in req["legal"]))
            self.assertTrue(all(0 <= i < features.SIZE for i in x))
        self.assertGreater(plays, 1000)


class AgainstRealDeals(unittest.TestCase):
    def test_whole_deals_replay_to_the_same_scores(self):
        scores = {}
        for line in (TRACE / "deals.jsonl").open(newline=None):
            row = json.loads(line)
            scores[row["deal"]] = row
        checked = moons = 0
        for line in (TRACE / "tricks.jsonl").open(newline=None):
            deal = json.loads(line)
            number = deal["deal"] - 200
            direction = direction_of(number)
            self.assertEqual(scores[deal["deal"]]["pass"], direction or "None")
            hands = [list(h) for h in deal["hands"]]
            passed = deal["passed"]
            if direction:
                new = [[c for c in hands[i] if c not in passed[i]] for i in range(4)]
                for i in range(4):
                    new[sim.pass_target(i + 1, direction) - 1] += passed[i]
                hands = new
            leader = next(i + 1 for i in range(4) if "C2" in hands[i])
            taken = [0, 0, 0, 0]
            broken = False
            for index, trick in enumerate(deal["tricks"]):
                self.assertEqual(trick["leader"], leader)
                cards = []
                for offset, card in enumerate(trick["cards"]):
                    seat = (leader - 1 + offset) % 4
                    self.assertIn(card, sim.legal_cards(hands[seat], cards, broken, index == 0), deal["deal"])
                    hands[seat].remove(card)
                    cards.append(card)
                    broken = broken or card[0] == "H"
                leader = sim.trick_winner(leader, cards)
                self.assertEqual(leader, trick["winner"])
                taken[leader - 1] += sum(sim.points(c) for c in cards)
            self.assertEqual(sim.deal_scores(taken), scores[deal["deal"]]["scores"], deal["deal"])
            moons += -26 in scores[deal["deal"]]["scores"]
            checked += 1
        self.assertGreater(checked, 100)
        self.assertGreater(moons, 0)


class Simulator(unittest.TestCase):
    def test_duck_bot_beats_random_and_scores_add_up(self):
        import random
        rng = random.Random(1)
        total = [0, 0, 0, 0]
        for _ in range(2000):
            deck = list(sim.DECK)
            rng.shuffle(deck)
            scores, taken = sim.play_deal([DuckBot(), RandomBot(rng), RandomBot(rng), RandomBot(rng)],
                                          deck, rng.choice(sim.DIRECTIONS))
            self.assertEqual(sum(taken), 26)
            total = [a + b for a, b in zip(total, scores)]
        self.assertLess(total[0] / 2000, min(total[1:]) / 2000 - 2)


if __name__ == "__main__":
    unittest.main()
