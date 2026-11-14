# Copyright (c) 2026 Athena Decision Systems SAS.
"""The game as a state machine with no I/O, so the fast benchmark loop and the server drive the same code.

Unlike the 1986 Administrator, this checks every card it gets.  Everything that happens is an event: a
JSON-ready dict in `events`, enough to rebuild the game exactly.  `visible_to` says who may see an event, and
`view` gives a seat what it may know, in the same form the LLM player's request has always had.
"""
import random

from .cards import DECK, DIRECTIONS, points
from .rules import deal_scores, legal_cards, pass_target, trick_winner


class IllegalMove(ValueError):
    pass


class Deal:
    """One deal.  phase is "pass", "play" or "done"."""

    def __init__(self, hands, direction, number=1, totals=(0, 0, 0, 0)):
        self.number = number
        self.direction = direction
        self.totals = list(totals)
        self.dealt = [list(h) for h in hands]
        self.hands = [list(h) for h in hands]
        self.passed = [[], [], [], []]
        self.received = [[], [], [], []]
        self.history = []
        self.cards = []
        self.leader = None
        self.broken = False
        self.taken = [0, 0, 0, 0]
        self.scores = None
        self.events = [{"type": "deal", "number": number, "direction": direction, "hands": self.dealt}]
        self.phase = "pass" if direction else "play"
        if not direction:
            self._start_play()

    def _start_play(self):
        self.phase = "play"
        self.leader = next(i + 1 for i in range(4) if "C2" in self.hands[i])

    @property
    def to_play(self):
        """The seat whose card is awaited, or None."""
        if self.phase != "play":
            return None
        return (self.leader - 1 + len(self.cards)) % 4 + 1

    def waiting(self):
        """Seats that must act now."""
        if self.phase == "pass":
            return [i + 1 for i in range(4) if not self.passed[i]]
        if self.phase == "play":
            return [self.to_play]
        return []

    def legal(self, seat):
        if self.phase == "pass":
            return list(self.hands[seat - 1])
        if seat != self.to_play:
            return []
        return legal_cards(self.hands[seat - 1], self.cards, self.broken, not self.history)

    def submit_pass(self, seat, cards):
        hand = self.hands[seat - 1]
        if self.phase != "pass" or self.passed[seat - 1]:
            raise IllegalMove(f"seat {seat} can't pass now")
        if len(cards) != 3 or len(set(cards)) != 3 or any(c not in hand for c in cards):
            raise IllegalMove(f"seat {seat} must pass three different cards from its hand")
        self.passed[seat - 1] = list(cards)
        self.events.append({"type": "passed", "seat": seat, "cards": list(cards)})
        if all(self.passed):
            for i in range(4):
                self.received[pass_target(i + 1, self.direction) - 1] = self.passed[i]
            self.hands = [[c for c in self.hands[i] if c not in self.passed[i]] + list(self.received[i])
                          for i in range(4)]
            self.events.append({"type": "received", "cards": [list(r) for r in self.received]})
            self._start_play()

    def submit_play(self, seat, card, thought=None):
        if seat != self.to_play:
            raise IllegalMove(f"it isn't seat {seat}'s turn")
        if card not in self.legal(seat):
            raise IllegalMove(f"{card} isn't legal for seat {seat}")
        self.hands[seat - 1].remove(card)
        self.cards.append(card)
        self.broken = self.broken or card[0] == "H"
        event = {"type": "card", "seat": seat, "card": card}
        if thought:
            event["thought"] = thought
        self.events.append(event)
        if len(self.cards) == 4:
            winner = trick_winner(self.leader, self.cards)
            self.taken[winner - 1] += sum(points(c) for c in self.cards)
            self.history.append({"leader": self.leader, "cards": self.cards, "winner": winner})
            self.events.append({"type": "trick", "leader": self.leader, "cards": self.cards, "winner": winner,
                                "points": sum(points(c) for c in self.cards)})
            self.leader = winner
            self.cards = []
            if len(self.history) == 13:
                self.scores = deal_scores(self.taken)
                self.phase = "done"
                self.events.append({"type": "deal_end", "number": self.number, "scores": self.scores})

    def view(self, seat):
        """What this seat may know: the LLM player's request, plus what a person's screen needs."""
        hand = list(self.hands[seat - 1])
        view = {"seat": seat, "deal": self.number, "direction": self.direction, "hand": hand,
                "scores": list(self.totals), "phase": self.phase}
        if self.phase == "pass" or (self.phase == "done" and not self.history):
            view.update(decision="pass", passed=list(self.passed[seat - 1]),
                        legal=list(hand) if not self.passed[seat - 1] else [])
            return view
        view.update(decision="play", legal=self.legal(seat) if seat == self.to_play else [],
                    trick={"leader": self.leader, "cards": list(self.cards)}, hearts_broken=self.broken,
                    first_trick=not self.history, passed=list(self.passed[seat - 1]),
                    received=list(self.received[seat - 1]),
                    history=[{"leader": t["leader"], "cards": list(t["cards"]), "winner": t["winner"]}
                             for t in self.history],
                    taken=list(self.taken), to_play=self.to_play)
        return view


def visible_to(event, seat):
    """The event as this seat (None: a spectator) may see it, keeping other hands and passes hidden."""
    kind = event["type"]
    if kind == "game":  # The seed would give away every hand.
        return {"type": "game", "over_score": event["over_score"]}
    if kind == "deal":
        return {**event, "hands": None if seat is None else event["hands"][seat - 1]}
    if kind == "passed" and event["seat"] != seat:
        return {"type": "passed", "seat": event["seat"]}
    if kind == "received":
        return {"type": "received", "cards": None if seat is None else event["cards"][seat - 1]}
    return event


class Game:
    """Deals until someone goes over over_score, as Game.Winner has it: exactly 100 plays on.  Winners are the seats with
    the lowest total, not the 1986 list, which also collected every seat that was the lowest so far.  Seeded, so a game
    is reproducible from its seed and moves."""

    def __init__(self, seed=None, over_score=100, deals=None):
        self.seed = seed
        self.rng = random.Random(seed)
        self.over_score = over_score
        self.fixed = iter(deals) if deals is not None else None  # (hands, direction) pairs, for benchmarks.
        self.totals = [0, 0, 0, 0]
        self.number = 0
        self.finished = False
        self.deal = None
        self.events = [{"type": "game", "seed": seed, "over_score": over_score}]
        self._seen = 0

    def next_deal(self):
        if self.finished:
            raise IllegalMove("the game is over")
        self.number += 1
        if self.fixed is not None:
            hands, direction = next(self.fixed)
        else:
            deck = list(DECK)
            self.rng.shuffle(deck)
            hands = [deck[i * 13:(i + 1) * 13] for i in range(4)]
            direction = DIRECTIONS[(self.number - 1) % 4]
        self.deal = Deal(hands, direction, self.number, self.totals)
        self._sync()
        return self.deal

    def _sync(self):
        new = self.deal.events[self._seen:]
        self.events.extend(new)
        self._seen = len(self.deal.events)
        return new

    def _after_move(self):
        new = self._sync()
        if self.deal.phase == "done":
            self.totals = [a + b for a, b in zip(self.totals, self.deal.scores)]
            self._seen = 0
            end = {"type": "totals", "totals": list(self.totals)}
            self.events.append(end)
            new = new + [end]
            if max(self.totals) > self.over_score:
                self.finished = True
                low = min(self.totals)
                done = {"type": "game_end", "totals": list(self.totals),
                        "winners": [i + 1 for i in range(4) if self.totals[i] == low]}
                self.events.append(done)
                new.append(done)
        return new

    def submit_pass(self, seat, cards):
        self.deal.submit_pass(seat, cards)
        return self._after_move()

    def submit_play(self, seat, card, thought=None):
        self.deal.submit_play(seat, card, thought)
        return self._after_move()
