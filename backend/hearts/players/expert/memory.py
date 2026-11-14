# Copyright (c) 2026 Athena Decision Systems SAS.
"""What an Expert keeps: its History of the deal and a model of each opponent."""
import struct

from hearts.cards import RANK_OF, SUITS

from ..cardlib import SUIT_CARDS, Shouldnt, cards_of_suit, ldifference, max_card, min_card


def float32(x):
    """Medley's floats are 32 bits, and certainties are compared with a threshold, so they round as Medley does."""
    return struct.unpack("f", struct.pack("f", x))[0]


def combine(old, new):
    """KEE.CF.Combine: EMYCIN's parallel combination of two certainty factors."""
    if old is None:
        return new
    if old >= 0 and new >= 0:
        return float32(old + float32(new * float32(1 - old)))
    if old < 0 and new < 0:
        return float32(old + float32(new * float32(1 + old)))
    den = float32(1 - min(abs(old), abs(new)))
    return 0 if den == 0 else float32(float32(old + new) / den)


class OpponentModel:
    """An Opponent Model: what one opponent has shown this deal, and the certainty of its strategy (EP.OpInit)."""

    __slots__ = ("seat", "points", "hand_cards", "played_cards", "tricks_won", "voids", "strategy")

    def __init__(self):
        self.init(None)

    def init(self, seat):
        self.seat = seat
        self.points = 0
        self.hand_cards = []
        self.played_cards = []  # Newest first.
        self.tricks_won = []
        self.voids = []
        self.strategy = {}  # Strategy name -> certainty.

    def certainty(self, strategy):
        return self.strategy.get(strategy, 0)

    def update_certainty(self, strategy, certainty):
        self.strategy[strategy] = combine(self.strategy.get(strategy), float32(certainty))

    def last_card_played(self):
        return self.played_cards[0] if self.played_cards else None


class History:
    """A History unit: the cards seen this deal, each suit's winner and loser, and the points.  CardsPlayed holds only
    finished tricks, so the cards of the trick in progress still count as left and aren't equivalent to anything."""

    def __init__(self, player):
        self.player = player
        self.total = {"My": 0, "Left": 0, "Right": 0, "Across": 0}
        self.points = {"My": 0, "Left": 0, "Right": 0, "Across": 0}
        self.left = {}
        self.played = set()
        self.winner = {}
        self.loser = {}

    def init(self):
        """EP.Init, with its revival fix K4: the deal's points go into the totals and start again at zero."""
        self.left = {suit: list(SUIT_CARDS[suit]) for suit in SUITS}
        self.played = set()
        for where, points in self.points.items():
            self.total[where] += points
            self.points[where] = 0
        self.compute_winners_and_losers()

    def compute_winners_and_losers(self):
        for suit, cards in self.left.items():
            self.winner[suit] = max_card(cards)
            self.loser[suit] = min_card(cards)

    def compute_stats(self, trick, where_winner):
        """EP.ComputeStats."""
        for card in trick.cards:
            self.left[card[0]].remove(card)
            self.played.add(card)
        self.compute_winners_and_losers()
        self.points[where_winner] += trick.points()
        return self.points[where_winner]

    def cards_left(self):
        return [card for suit in SUITS for card in self.left[suit]]

    def get_winner(self, suit):
        try:
            return self.winner[suit]
        except KeyError:
            raise Shouldnt(f"EP.GetWinner: Illegal suit {suit}") from None

    def get_loser(self, suit):
        try:
            return self.loser[suit]
        except KeyError:
            raise Shouldnt(f"EP.GetWinner: Illegal suit {suit}") from None

    def equivalent(self, card1, card2, negate=False):
        """EP.Equivalent?: same suit, and every card from one to the other, both included, played or in my hand.  So a
        card on the table is equivalent to nothing, itself included.  Different suits are never equivalent (fix K7).
        With negate: are they not?"""
        suit = card1[0] if card1 else None
        if suit != (card2[0] if card2 else None):
            return negate
        hand = self.player.hand.in_suit(suit)
        low, high = RANK_OF[card1], RANK_OF[card2]
        if low > high:
            low, high = high, low
        played = self.played
        for card in SUIT_CARDS[suit][low:high + 1]:
            if card not in played and card not in hand:
                return negate
        return not negate

    def equivalent_cards(self, card, limiting=None):
        """EP.EquivalentCards: among limiting or, if none, my cards in the suit.  No card, no cards (fix K8)."""
        if not card:
            return []
        cards = limiting or self.player.hand.in_suit(card[0])
        return [c for c in cards if self.equivalent(card, c)]

    def highest_equivalent(self, card, limiting=None):
        return max_card(self.equivalent_cards(card, limiting))

    def lowest_equivalent(self, card, limiting=None):
        return min_card(self.equivalent_cards(card, limiting))

    def _select(self, suit, cards, target, keep):
        """EP.Winners, EP.Losers and EP.NonWinners: the cards (of the suit, among cards if any, else from my hand) that
        are, or aren't, equivalent to the target card of their suit."""
        hand = self.player.hand
        if suit:
            chosen = cards_of_suit(cards, suit) if cards else hand.in_suit(suit)
            aim = target(suit)
            return [c for c in chosen if self.equivalent(c, aim) == keep]
        return [c for c in (cards or hand.cards()) if self.equivalent(c, target(c[0])) == keep]

    def non_winners(self, suit=None, cards=None):
        return self._select(suit, cards, self.get_winner, False)

    def winners(self, suit=None, cards=None):
        return self._select(suit, cards, self.get_winner, True)

    def losers(self, suit=None, cards=None):
        return self._select(suit, cards, self.get_loser, True)

    def winner_suit(self, suit):
        """EP.WinnerSuit?: true of a suit I am void in, a quirk that te.go.for.it and the shooting rules inherit."""
        if not self.non_winners(suit):
            return True
        return len(self.winners(suit)) > len(ldifference(self.left[suit], self.player.hand.in_suit(suit)))

    def winner_suits(self):
        return [suit for suit in SUITS if self.winner_suit(suit)]

    def fewest_winners(self, excluded):
        """EP.FewestWinners: the first such suit, which is often one I am void in."""
        best, fewest = None, None
        for suit in SUITS:
            if suit not in excluded:
                count = len(self.equivalent_cards(self.get_winner(suit)))
                if fewest is None or count < fewest:
                    best, fewest = suit, count
        return best

    def number_with_points(self):
        return sum(1 for points in self.points.values() if points > 0)

    def suits_with_cards(self):
        return [suit for suit in SUITS if self.player.hand.suits[suit]]

    def all_card_suits(self):
        """EP.AllCardSuits, reconstructed: suits in which every card left is mine."""
        hand = self.player.hand
        return [suit for suit in SUITS if hand.suits[suit] and all(c in hand.suits[suit] for c in self.left[suit])]
