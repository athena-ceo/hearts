# Copyright (c) 2026 Athena Decision Systems SAS.
"""The exact rules of the 1986 code: H.GetLegals, Trick.Winner, H.Deal and Deal.SetScore."""
from .cards import PASS_OFFSET, RANK_OF


def legal_cards(hand, trick_cards, hearts_broken, first_trick):
    if trick_cards:
        suit = trick_cards[0][0]
        follow = [c for c in hand if c[0] == suit]
        if follow:
            return follow
        if first_trick:
            return [c for c in hand if c[0] != "H" and c != "SQ"] or list(hand)
        return list(hand)
    if first_trick:
        return ["C2"]
    if hearts_broken:
        return list(hand)
    return [c for c in hand if c[0] != "H"] or list(hand)


def trick_winner(leader, cards):
    """The seat that played the highest card of the led suit."""
    suit = cards[0][0]
    best = max((i for i, c in enumerate(cards) if c[0] == suit), key=lambda i: RANK_OF[cards[i]])
    return (leader - 1 + best) % 4 + 1


def deal_scores(taken):
    """26 points become -26 for the shooter, and the others keep what they took."""
    return [-26 if t == 26 else t for t in taken]


def pass_target(seat, direction):
    return (seat - 1 + PASS_OFFSET[direction]) % 4 + 1
