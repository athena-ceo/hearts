# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The 1986 card, hand and trick functions (Card.*, CardList.*, Hand.*, Trick.*, H.GetLegals), with their exact results.

None stands for NIL.  These keep Lisp's habits, which the players depend on:

- Card.Higher? and Card.Lower? compare values only, across suits, and Lower? is "not higher and not the same card".
  So two cards of equal value in different suits are each lower than the other: Card.MinCard takes the last of a tie
  and Card.MaxCard the first.
- Anything compared with None is not higher and is lower.
- Trick.WhoPlayed advances its counter twice per card, so it usually names the wrong seat.  See who_played.

Card.MaxCard is the revived version (HEARTS-BUGS.md H3), which starts from the first card in the suit it was asked for.
"""
from rulebook import RuleFailed

from hearts.cards import RANK_OF, RANKS, SUITS

SUIT_CARDS = {suit: [suit + rank for rank in RANKS] for suit in SUITS}
TEN = RANK_OF["C10"]
QUEEN = "SQ"
BRIDGE_POINTS = {"J": 1, "Q": 2, "K": 3, "A": 4}


class RuleError(RuleFailed):
    """A Lisp error inside a rule.  KEELOOPS fails the premise that raised it, and the next rule is tried."""


class Shouldnt(Exception):
    """SHOULDNT.  In Medley it opens a break window, which KEELOOPS doesn't catch, so the game stops there.  This stops
    the game too.  The one way we know to reach it is an Expert passing as a shooter with only spades left."""


def create_card(value, suit):
    """Card.Create."""
    card = None if suit is None else f"{suit}{value}"
    if card not in RANK_OF:
        raise RuleError(f"Illegal card suit: {suit} or value: {value}!")
    return card


def higher(card1, card2):
    """Card.Higher?: card1 if its value is higher, else None."""
    if card1 and card2 and RANK_OF[card1] > RANK_OF[card2]:
        return card1
    return None


def lower(card1, card2):
    """Card.Lower?: not higher and not the same card, so a tie in another suit is lower, as is anything with None."""
    if card1 and card2:
        return RANK_OF[card1] <= RANK_OF[card2] and card1 != card2
    return True


def max_card(cards, in_suit=None):
    """Card.MaxCard: the first of the highest."""
    highest = None
    for card in cards:
        if (not in_suit or card[0] == in_suit) and (highest is None or RANK_OF[card] > RANK_OF[highest]):
            highest = card
    return highest


def min_card(cards, in_suit=None):
    """Card.MinCard: the last of the lowest."""
    lowest = None
    for card in cards:
        if not in_suit or card[0] == in_suit:
            if lowest is None or (RANK_OF[card] <= RANK_OF[lowest] and card != lowest):
                lowest = card
    return lowest


def cards_of_suit(cards, suit):
    return [c for c in cards if c[0] == suit]


def cards_of_suits(cards, suits):
    return [c for c in cards if c[0] in suits]


def eliminate_suit(cards, suit):
    return [c for c in cards if c[0] != suit]


def eliminate_suits(cards, suits):
    return [c for c in cards if c[0] not in suits]


def remove_card(cards, card):
    return [c for c in cards if c != card]


def intersection(cards, others):
    """INTERSECTION keeps the order of its first list (checked in Medley)."""
    return [c for c in cards if c in others]


def ldifference(cards, others):
    return [c for c in cards if c not in others]


def higher_cards(cards, card, in_suit):
    return [c for c in cards if c[0] == in_suit and higher(c, card)]


def lower_cards(cards, card, in_suit):
    return [c for c in cards if c[0] == in_suit and lower(c, card)]


def high_spades(cards):
    """CardList.HighSpades?: the highest spade if it is above the jack."""
    return higher(max_card(cards, "S"), "SJ")


def point_cards(cards):
    return [c for c in cards if c[0] == "H" or c == QUEEN]


def shortest_suit(cards):
    """CardList.ShortestSuit: the first of the shortest suits that has a card."""
    best, fewest = None, None
    for suit in SUITS:
        count = sum(1 for c in cards if c[0] == suit)
        if count and (fewest is None or count < fewest):
            best, fewest = suit, count
    return best


def bridge_points(cards):
    return sum(BRIDGE_POINTS.get(c[1:], 0) for c in cards)


def cards_between(card1, card2):
    """Card.CardsBetween, the cards of the suit strictly between two cards."""
    low, high = (card1, card2) if lower(card1, card2) else (card2, card1)
    return SUIT_CARDS[low[0]][RANK_OF[low] + 1:RANK_OF[high]]


class Hand:
    """A Hand record: its cards by suit, each suit in the order the cards came."""

    __slots__ = ("suits",)

    def __init__(self, cards):
        self.suits = {suit: [c for c in cards if c[0] == suit] for suit in SUITS}

    def cards(self):
        """Hand.Cards: clubs, diamonds, hearts, spades."""
        suits = self.suits
        return suits["C"] + suits["D"] + suits["H"] + suits["S"]

    def in_suit(self, suit):
        """Hand.CardsInSuit, which is SHOULDNT for a suit that isn't one."""
        try:
            return self.suits[suit]
        except KeyError:
            raise Shouldnt(f"Hand.CardsInSuit of suit {suit}") from None

    def add(self, card):
        self.suits[card[0]].append(card)

    def remove(self, card):
        suit = self.in_suit(card[0] if card else None)
        self.suits[card[0]] = [c for c in suit if c != card]
        return card

    def has(self, card):
        return card in self.suits[card[0]]

    def max_card(self, suit):
        return max_card(self.in_suit(suit), suit)

    def min_card(self, suit):
        return min_card(self.in_suit(suit), suit)

    def face_cards(self):
        """Hand.FaceCards: everything above a ten."""
        return [c for c in self.cards() if RANK_OF[c] > TEN]

    def legal(self, trick_cards, hearts_broken, first_trick):
        """H.GetLegals."""
        if trick_cards:
            lead_suit = trick_cards[0][0]
            cards = self.suits[lead_suit]
            if not cards:
                cards = [c for c in self.cards() if c[0] != "H" and c != QUEEN] if first_trick else self.cards()
        elif first_trick:
            if not self.has("C2"):
                raise Shouldnt("Leader of first trick does not have the 2 of clubs.")
            cards = ["C2"]
        elif hearts_broken:
            cards = self.cards()
        else:
            cards = [c for c in self.cards() if c[0] != "H"]
        return cards or self.cards()


class Trick:
    """A Trick record.  The 1986 players keep the very record the Administrator fills in, so the rules that run after
    the trick see all four cards and the winner."""

    __slots__ = ("leader", "cards", "winner")

    def __init__(self, leader, cards, winner=None):
        self.leader, self.cards, self.winner = leader, cards, winner

    @property
    def lead_suit(self):
        """Trick.LeadSuit."""
        return self.cards[0][0] if self.cards else None

    def points(self):
        """Trick.Points."""
        return sum(13 if c == QUEEN else 1 if c[0] == "H" else 0 for c in self.cards)

    def play_of(self, seat):
        """Trick.PlayOf: this seat's card, or None if it hasn't played yet."""
        when = seat - self.leader + 1
        when = when + 4 if when <= 0 else when
        return self.cards[when - 1] if when <= len(self.cards) else None

    def who_played(self, card):
        """Trick.WhoPlayed, a 1986 bug kept as it runs: the loop's body adds one to the seat, and so does `for i from`,
        so the wrap is missed.  From a leader of 1 it answers 1, 3, 5, 3 for the four cards, not 1, 2, 3, 4."""
        seat = self.leader
        for played in self.cards:
            if played == card:
                return seat
            seat += 1
            if seat > 4:
                seat -= 4
            seat += 1
        return seat

    def winner_so_far(self):
        """Trick.WinnerSoFar, which inherits the bug in who_played."""
        return self.who_played(max_card(self.cards, self.lead_suit))
