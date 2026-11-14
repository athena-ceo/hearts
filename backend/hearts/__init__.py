# Copyright (c) 2026 Athena Decision Systems SAS.
"""HEARTS in Python: the rules and the game (no I/O), its players, and a server.

See docs/design/python-platform.md.  Medley is the reference this must match.
"""
from .cards import DECK, DIRECTIONS, INDEX, RANK_OF, RANKS, SUITS, points
from .game import Deal, Game, IllegalMove
from .rules import deal_scores, legal_cards, pass_target, trick_winner

__all__ = ["DECK", "DIRECTIONS", "INDEX", "RANK_OF", "RANKS", "SUITS", "points", "Deal", "Game", "IllegalMove",
           "deal_scores", "legal_cards", "pass_target", "trick_winner"]
