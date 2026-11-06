"""Simple rule-based opponents for training and tracking progress: not the Expert, which lives in
Medley, but enough to stop self-play drifting into habits that only work against itself."""
import random

from hearts_sim import RANK_OF, points


def high(cards):
    return max(cards, key=lambda c: RANK_OF[c])


def low(cards):
    return min(cards, key=lambda c: RANK_OF[c])


class RandomBot:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def forced(self):
        pass

    def choose_pass(self, request):
        return self.rng.sample(request["hand"], 3)

    def choose_play(self, request):
        return self.rng.choice(request["legal"])


class DuckBot:
    """Passes danger, ducks when it can, dumps the queen and hearts on others."""

    def __init__(self, rng=None):
        self.rng = rng or random.Random()

    def forced(self):
        pass

    def choose_pass(self, request):
        hand = list(request["hand"])
        spades = [c for c in hand if c[0] == "S"]
        chosen = []
        if len(spades) < 4:
            chosen += [c for c in ("SA", "SK", "SQ") if c in hand]
        rest = sorted((c for c in hand if c not in chosen),
                      key=lambda c: (RANK_OF[c] + (3 if c[0] == "H" else 0)), reverse=True)
        return (chosen + rest)[:3]

    def choose_play(self, request):
        legal = request["legal"]
        cards = request["trick"]["cards"]
        queen_gone = "SQ" in cards or any("SQ" in t["cards"] for t in request["history"])
        if not cards:
            safe = [c for c in legal if c[0] != "S" or queen_gone or RANK_OF[c] < RANK_OF["SQ"]]
            return low(safe or legal)
        suit = cards[0][0]
        if legal[0][0] != suit or any(c[0] != suit for c in legal):
            if "SQ" in legal:
                return "SQ"
            dangerous = [c for c in legal if c in ("SA", "SK")] if not queen_gone else []
            if dangerous:
                return high(dangerous)
            hearts = [c for c in legal if c[0] == "H"]
            return high(hearts or legal)
        top = high([c for c in cards if c[0] == suit])
        under = [c for c in legal if RANK_OF[c] < RANK_OF[top]]
        if under:
            return "SQ" if "SQ" in under else high(under)
        if len(cards) == 3 and not any(points(c) for c in cards):
            others = [c for c in legal if c != "SQ"]
            return high(others or legal)
        others = [c for c in legal if c != "SQ"]
        return low(others or legal)
