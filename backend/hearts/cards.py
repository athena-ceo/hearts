# Copyright (c) 2026 Athena Decision Systems SAS.
"""Cards are strings such as "S10" and "HA".  Seats are 1-4, clockwise."""
SUITS = "CDHS"
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
DECK = [s + r for s in SUITS for r in RANKS]
INDEX = {card: i for i, card in enumerate(DECK)}
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}
RANK_OF = {card: RANK_ORDER[card[1:]] for card in DECK}
PASS_OFFSET = {"Left": 1, "Across": 2, "Right": 3}
DIRECTIONS = ["Left", "Across", "Right", None]  # By deal, repeating; None means no pass.


def points(card):
    return 13 if card == "SQ" else 1 if card[0] == "H" else 0
