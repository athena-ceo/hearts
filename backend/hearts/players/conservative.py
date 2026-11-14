# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Conservative: the 1986 rule-of-thumb minimizer, CP.* in medley/HEARTS, as one straight procedure.

Its one random choice is CP.Follow's when it must win a spade trick last and holds the queen on top: any of its spades,
through _random_spade.  Medley's RAND isn't reproduced, so the conformance test feeds that choice from the Medley log.
Thoughts are its CP.Think lines, which in Medley only print.
"""
import random

from .base import Player, Thought
from .cardlib import Hand, QUEEN, higher, intersection, max_card, min_card


def _name(card):
    """Card.PrintCard."""
    value = {"J": "Jack", "Q": "Queen", "K": "King", "A": "Ace"}.get(card[1:], card[1:])
    return f"{value} of {dict(C='Clubs', D='Diamonds', H='Hearts', S='Spades')[card[0]]}"


class Conservative(Player):
    kind = "conservative"
    label = "Conservative"
    plays_forced_cards = True  # It keeps its own hand, so it has to hear about every card.

    def __init__(self, name=None, seed=None):
        super().__init__(name)
        self.rng = random.Random(seed)
        self.held = None
        self.maggie_played = False

    def give_hand(self, hand, seat):
        self.seat = seat
        self.held = Hand(hand)
        self.maggie_played = False

    def _has_maggie(self):
        return QUEEN if self.held.has(QUEEN) else None

    def _high_spade(self):
        """CP.HighSpades."""
        return higher(max_card(self.held.in_suit("S")), "SJ")

    def _pass_card(self):
        held = self.held
        if held.has(QUEEN):
            return QUEEN, ""
        spade = max_card(held.in_suit("S"))
        if higher(spade, QUEEN):
            return spade, "I will pass my highest spade, the "
        heart = max_card(held.in_suit("H"))
        if higher(heart, "H10"):
            return heart, "I will pass my highest heart, the "
        if len(held.in_suit("D")) == 1:
            return held.in_suit("D")[0], "I will pass my singleton, the "
        if len(held.in_suit("C")) in (1, 2):
            return max_card(held.in_suit("C")), "I will pass my singleton or doubleton club, the "
        return max_card(held.cards()), "I will pass my highest card, the "

    def pass_out(self, view):
        """CP.PassOut, one card at a time, three times.  No pass direction, no cards."""
        self.thought = None
        if not view["direction"]:
            return []
        cards, lines = [], []
        for _ in range(3):
            card, line = self._pass_card()
            self.held.remove(card)
            cards.append(card)
            lines.append(line + _name(card))
        self.thought = Thought(text=". ".join(lines) + ".")
        return cards

    def pass_in(self, cards):
        for card in cards:
            self.held.add(card)

    def play(self, view):
        cards = view["trick"]["cards"]
        legal = self.held.legal(cards, view["hearts_broken"], view["first_trick"])
        card, thought = self._follow(cards, legal) if cards else self._lead(legal, view["hearts_broken"])
        self.held.remove(card)
        self.thought = Thought(text=thought)
        return card

    def _lead(self, legal, hearts_broken):
        """CP.Lead."""
        held, thoughts = self.held, []
        leads = intersection(held.in_suit("C") + held.in_suit("D"), legal)
        if not self._high_spade() or self.maggie_played:
            thoughts.append("Spades would be good to lead...")
            leads = leads + intersection(held.in_suit("S"), legal)
        if hearts_broken:
            thoughts.append("I could lead hearts...")
            leads = leads + intersection(held.in_suit("H"), legal)
        if not leads:
            thoughts.append("Nothing good to lead.")
            leads = legal
        card = min_card(leads)
        thoughts.append(f"I will lead the {_name(card)}")
        return card, " ".join(thoughts)

    def _follow(self, trick_cards, legal):
        """CP.Follow."""
        lead_suit = trick_cards[0][0]
        follow = self.held.in_suit(lead_suit)
        if follow:
            highest = max_card([c for c in trick_cards if c[0] == lead_suit])
            under = [c for c in follow if not higher(c, highest)]
            if under:
                card, thought = max_card(under), "I won't win this one!"
            elif len(trick_cards) == 3:
                thought = "Oh well, I might as well win big."
                spades = self.held.in_suit("S")
                if lead_suit == "S" and max_card(spades) == self._has_maggie() and len(spades) > 1:
                    card = self._random_spade(spades)
                else:
                    card = max_card(follow)
            else:
                card, thought = min_card(follow), "Sure hope someone plays higher than me."
        else:
            high_spade = None if self.maggie_played else self._high_spade()
            hearts = self.held.in_suit("H")
            if self._has_maggie() and QUEEN in legal:
                card, thought = QUEEN, "Eat this, sucker."
            elif high_spade and high_spade in legal:
                card, thought = high_spade, "Don't want to eat the Black Bitch."
            elif hearts and max_card(hearts) in legal:
                card, thought = max_card(hearts), "Munch, munch."
            else:
                card, thought = max_card(legal), "My highest card."
        return card, f"{thought} I will play the {_name(card)}"

    def _random_spade(self, spades):
        """(CAR (FNTH Spades (RAND 1 SpadeLength)))."""
        return self.rng.choice(spades)

    def trick(self, trick):
        """CP.Trick."""
        if QUEEN in trick["cards"]:
            self.maggie_played = True

    def decide(self, view):
        """Any position: all it remembers is its hand, which the view gives, and whether the queen has gone."""
        replay = type(self)(self.name)
        replay.rng = self.rng
        replay.held = Hand(view["hand"])
        if view["decision"] == "pass":
            cards = replay.pass_out(view)
            return cards, replay.thought
        if not view["legal"]:
            return None, None  # It isn't this seat's turn.
        replay.maggie_played = any(QUEEN in t["cards"] for t in view["history"])
        card = replay.play(view)
        return card, replay.thought
