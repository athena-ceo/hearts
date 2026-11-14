# Copyright (c) 2026 Athena Decision Systems SAS.
"""What the Expert's rules can say.  Every phrase is one function of the 1986 system, with its exact results and quirks
(see cardlib.py and memory.py), and the subject of every phrase is the Expert.

To see it all as a rule author does:  python -m rulebook phrases --vocabulary hearts.players.expert.vocabulary:VOCABULARY
"""
from rulebook import Vocabulary

from ..cardlib import (QUEEN, bridge_points, cards_between, cards_of_suit, cards_of_suits, create_card, eliminate_suit,
                       eliminate_suits, high_spades, higher, intersection, ldifference, lower, max_card, min_card,
                       point_cards, remove_card, shortest_suit)

POOR_SPADES, WEAKEST_SUIT = "Poor Spades Protection", "WeakestSuit"

v = VOCABULARY = Vocabulary()
v.type("rank", phrases=False)
v.parents["number"] = ("rank",)
v.type("card")
v.type("cards", element="card")
v.type("suit")
v.type("suits", element="suit")
v.type("strategy")
v.type("opponent")

# ---- constants

for word, suit in (("clubs", "C"), ("diamonds", "D"), ("hearts", "H"), ("spades", "S")):
    v.constant(word, suit, "suit")
for word, strategy in (("minimizing", "Minimizing"), ("shooting", "Shooting"), ("eclipsing", "Eclipsing")):
    v.constant(word, strategy, "strategy")
for word, rank in (("jack", "J"), ("king", "K"), ("ace", "A")):
    v.constant(word, rank, "rank")
v.constant("the queen", QUEEN, "card")

# ---- any cards

v.term("the {rank} of {suit}", "card", lambda me, rank, suit: create_card(rank, suit))
v.term("{rank} of {suit}", "card", lambda me, rank, suit: create_card(rank, suit))
v.term("the suit of {card}", "suit", lambda me, card: card[0] if card else None)
v.term("the highest of {cards}", "card", lambda me, cards: max_card(cards))
v.term("the lowest of {cards}", "card", lambda me, cards: min_card(cards))
v.term("the first of {cards}", "card", lambda me, cards: cards[0] if cards else None)
v.term("the high spade of {cards}", "card", lambda me, cards: high_spades(cards))
v.term("{cards} in {suit}", "cards", lambda me, cards, suit: cards_of_suit(cards, suit))
v.term("{cards} in {suits}", "cards", lambda me, cards, suits: cards_of_suits(cards, suits))
v.term("{cards} except {suit}", "cards", lambda me, cards, suit: eliminate_suit(cards, suit))
v.term("{cards} except {suits}", "cards", lambda me, cards, suits: eliminate_suits(cards, suits))
v.term("{cards} except {card}", "cards", lambda me, cards, card: remove_card(cards, card))
v.term("{cards} except {cards}", "cards", lambda me, cards, others: ldifference(cards, others))
v.term("{cards} that are also in {cards}", "cards", lambda me, cards, others: intersection(cards, others))
v.term("{cards} plus {cards}", "cards", lambda me, cards, others: cards + others)
v.term("{cards} lower than {card}", "cards", lambda me, cards, card: [c for c in cards if lower(c, card)])
v.term("{cards} higher than {card}", "cards", lambda me, cards, card: [c for c in cards if higher(c, card)])
v.term("the point cards in {cards}", "cards", lambda me, cards: point_cards(cards))
v.term("the shortest suit of {cards}", "suit", lambda me, cards: shortest_suit(cards))
v.term("the bridge points of {cards}", "number", lambda me, cards: bridge_points(cards))
v.term("the cards between {card} and {card}", "cards", lambda me, a, b: cards_between(a, b))
v.test("{card} is higher than {card}", lambda me, a, b: higher(a, b))
v.test("{card} is lower than {card}", lambda me, a, b: lower(a, b))

# ---- my cards

v.term("my legal cards", "cards", lambda me: me.legals)
v.term("my hand", "cards", lambda me: me.hand.cards())
v.term("my {suit}", "cards", lambda me, suit: me.hand.in_suit(suit))
v.term("my face cards", "cards", lambda me: me.hand.face_cards())
v.term("the cards i was passed", "cards", lambda me: me.pass_in_cards)
v.term("the suits i hold", "suits", lambda me: me.history.suits_with_cards())
v.term("the queen if i can otherwise {card}", "card", lambda me, card: QUEEN if QUEEN in me.legals else card)
v.test("i hold the queen", lambda me: me.maggie_location == "InHand")

# ---- the trick

v.term("the trick's cards", "cards", lambda me: me.current_trick.cards)
v.term("the lead suit", "suit", lambda me: me.current_trick.lead_suit)
v.term("the trick's points", "number", lambda me: me.current_trick.points())
v.term("the trick's highest card", "card", lambda me: max_card(me.current_trick.cards, me.current_trick.lead_suit))
v.term("the trick's card from {opponent}", "card", lambda me, op: me.current_trick.play_of(op.seat))
v.term("the trick number", "number", lambda me: me.trick_number)
v.test("the trick has {number} cards", lambda me, n: len(me.current_trick.cards) == n)
v.test("i did not win the trick", lambda me: me.current_trick.winner != me.seat)
v.test("{opponent} won the trick", lambda me, op: me.current_trick.winner == op.seat)
# Trick.WinnerSoFar has a 1986 bug, kept: it usually names the wrong seat.  See Trick.who_played.
v.test("{opponent} is winning so far", lambda me, op: op.seat == me.current_trick.winner_so_far())
v.test("{opponent} is not winning so far", lambda me, op: op.seat != me.current_trick.winner_so_far())

# ---- the deal so far

v.test("the queen has been played", lambda me: me.maggie_status == "Played")
v.test("the queen has not been played", lambda me: me.maggie_status == "NotPlayed")
v.term("the points i have taken", "number", lambda me: me.history.points["My"])
v.term("the number of players with points", "number", lambda me: me.history.number_with_points())
v.term("the cards left", "cards", lambda me: me.history.cards_left())
v.term("the winner of {suit}", "card", lambda me, suit: me.history.get_winner(suit))
v.term("my non-winners in {suit}", "cards", lambda me, suit: me.history.non_winners(suit))
v.term("my losers in {suit}", "cards", lambda me, suit: me.history.losers(suit))
v.term("the non-winners among {cards}", "cards", lambda me, cards: me.history.non_winners(None, cards))
v.term("the non-winners in {suit} among {cards}", "cards", lambda me, suit, cards: me.history.non_winners(suit, cards))
v.term("the winners among {cards}", "cards", lambda me, cards: me.history.winners(None, cards))
v.term("the losers among {cards}", "cards", lambda me, cards: me.history.losers(None, cards))
v.test("{card} is equivalent to {card}", lambda me, a, b: me.history.equivalent(a, b))
v.test("{card} is not equivalent to {card}", lambda me, a, b: me.history.equivalent(a, b, True))
v.term("the highest card equivalent to {card}", "card", lambda me, card: me.history.highest_equivalent(card))
v.term("the highest card equivalent to {card} among {cards}", "card",
       lambda me, card, cards: me.history.highest_equivalent(card, cards))
v.term("the lowest card equivalent to {card} among {cards}", "card",
       lambda me, card, cards: me.history.lowest_equivalent(card, cards))
v.term("my winner suits", "suits", lambda me: me.history.winner_suits())
v.test("{suit} is a winner suit", lambda me, suit: me.history.winner_suit(suit))
v.term("the suits where every card left is mine", "suits", lambda me: me.history.all_card_suits())
v.term("the suit with the fewest winners other than {suit}", "suit", lambda me, suit: me.history.fewest_winners(suit))

# ---- strategy and the other players

v.term("my strategy", "strategy", lambda me: me.strategy)
v.term("the left opponent", "opponent", lambda me: me.left)
v.term("the right opponent", "opponent", lambda me: me.right)
v.term("the opponent across", "opponent", lambda me: me.across)
v.term("the shooter", "opponent", lambda me: me.shooter)
v.term("the opponent", "opponent", lambda me: me.opponent)
v.term("the void suits of {opponent}", "suits", lambda me, op: op.voids)
v.term("the void suits of hearty non-shooters", "suits", lambda me: me.hearty_non_shooter_void_suits())
v.term("the void suits of hearty opponents", "suits", lambda me: me.hearty_opponent_void_suits())
v.term("the last card played by {opponent}", "card", lambda me, op: op.last_card_played())
v.test("{opponent} is suspected of shooting", lambda me, op: me.suspects(op))

# ---- conclusions

v.action("play {card}", lambda me, card: card, goal="PlayCard")
v.action("adopt {strategy}", lambda me, strategy: strategy, goal="Strategy")
v.action("pass {card}", lambda me, card: me.do_pass([card]), goal="More Cards Selected")
v.action("pass {cards}", lambda me, cards: me.do_pass(cards), goal="More Cards Selected")


def _set_shooter(me, op):
    me.shooter = op
    return True


def _certainty(me, op, strategy, certainty):
    op.update_certainty(strategy, certainty)
    return True


v.action("the shooter is {opponent}", _set_shooter)
v.action("{opponent} is {strategy} with certainty {number}", _certainty, goal="Certainty")
v.fact("my spade protection is poor", POOR_SPADES)
v.derived("the weakest suit", "suit", WEAKEST_SUIT)

