# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The 1986 player protocol: GiveHand, PassOut, PassIn, Play, Trick, Results.  Trick and Results are optional.

A player's choice can carry a Thought, its reason.  `decide` answers from a complete seat view, whatever
position that is, so any player can be asked about any position; a player with memory rebuilds it there.
"""
from dataclasses import dataclass, field


@dataclass
class Thought:
    """Why a player chose: the Expert's text and rule, an LLM's explanation, or a network's preferences."""
    text: str = ""
    rule: str | None = None
    shares: dict = field(default_factory=dict)

    def as_dict(self):
        return {k: v for k, v in {"text": self.text, "rule": self.rule, "shares": self.shares}.items() if v}


class Player:
    kind = "player"
    label = "A player"
    plays_forced_cards = False  # True if it wants Play even when it has one legal card, as players with memory do.

    def __init__(self, name=None):
        self.name = name or self.label
        self.thought = None  # The reason for the latest pass_out or play.

    def give_hand(self, hand, seat):
        self.hand, self.seat = list(hand), seat

    def pass_out(self, view):
        """The three cards to pass.  It is also sent when view["direction"] is None, for no cards: return []."""
        raise NotImplementedError

    def pass_in(self, cards):
        pass

    def play(self, view):
        raise NotImplementedError

    def trick(self, trick):
        pass

    def results(self, scores):
        pass

    def decide(self, view):
        """(cards or card, Thought) for any position.  A player with no memory just answers."""
        answer = self.pass_out(view) if view["decision"] == "pass" else self.play(view)
        return answer, self.thought


def play_game(players, game, deals=None):
    """Run a game of automated players to its end, or for this many deals in all, sending the six messages in the order
    of H.PlayGame and H.Deal.  Returns the game.

    GiveHand goes to all, then PassOut to all, on a deal with no pass as well (the Expert picks its strategy there),
    then PassIn to all, if there was a pass.  Play goes to each seat in turn, Trick to all after each trick, and Results
    to all after each deal, with the running totals.  Medley sends Play for every card and Trick to everyone, forced or
    not.  Here, a forced card skips Play unless the player asks for it: `plays_forced_cards`.
    """
    while not game.finished and (deals is None or game.number < deals):
        deal = game.next_deal()
        for i, player in enumerate(players):
            player.give_hand(deal.dealt[i], i + 1)
        for i, player in enumerate(players):
            cards = player.pass_out(deal.view(i + 1))
            if deal.direction:
                game.submit_pass(i + 1, cards)
        if deal.direction:
            for i, player in enumerate(players):
                player.pass_in(deal.received[i])
        while deal.phase == "play":
            seat = deal.to_play
            player = players[seat - 1]
            view = deal.view(seat)
            player.thought = None
            card = view["legal"][0] if len(view["legal"]) == 1 and not player.plays_forced_cards else player.play(view)
            done_before = len(deal.history)
            game.submit_play(seat, card, player.thought.as_dict() if player.thought else None)
            if len(deal.history) > done_before:
                for other in players:
                    other.trick(deal.history[-1])
        for other in players:
            other.results(list(game.totals))
    return game
