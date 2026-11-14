# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Expert: the 1986 EP.* handlers (medley/EXPERT) around the rules in expert.rules.  It keeps all it knows in its own
slots, so an Expert carries nothing from one deal to the next that a rule reads, and `decide` can rebuild any position.
"""
from rulebook import Session

from ..base import Player, Thought
from ..cardlib import Hand, QUEEN, RuleError, Trick
from .memory import History, OpponentModel, float32
from .rulebase import POOR_SPADES, RULES_1986, STRATEGIES, WEAKEST_SUIT

_LOCATIONS = ("Left", "Right", "Across")  # EP.GiveHand and EP.Trick go through the opponents in this order.
_OFFSET = {"Left": 1, "Across": 2, "Right": 3}
_WHERE = {0: "My", 1: "Left", 2: "Across", 3: "Right"}  # PlayerLoc, by how many seats on from me.


class Expert(Player):
    kind = "expert"
    label = "Expert, 1986"
    plays_forced_cards = True  # The rules answer "One choice." and count the trick.

    def __init__(self, name=None, rules=None, trace=None):
        super().__init__(name)
        self.rules = rules or RULES_1986
        self.trace = trace  # A list to append the name of every rule that fires, or None.
        self.session = Session(self.rules, self, self._fired if trace is not None else None)
        self.opponent = None  # The opponent the rules are thinking about.
        self.hand = None
        self.seat = None
        self.history = History(self)
        self.left, self.right, self.across = OpponentModel(), OpponentModel(), OpponentModel()
        self.strategy = None
        self.shooter = None
        self.maggie_status = "NotPlayed"
        self.maggie_location = "Elsewhere"
        self.trick_number = 0
        self.legals = []
        self.current_trick = None
        self.pass_dir = None
        self.pass_cards = []
        self.number_of_pass_cards = 0
        self.pass_in_cards = None
        self.pass_in_from = None
        self._has_passed = False

    def _fired(self, rule, frame):
        self.trace.append(rule.name)

    @property
    def rule_errors(self):
        return self.session.errors

    def _opinion(self, rule_class, op):
        """Every rule of this class that holds updates its certainty about this opponent."""
        self.opponent = op
        self.session.all(rule_class, "Certainty")

    # ---- what the rules ask

    def suspects(self, op):
        """Is the certainty that this opponent is shooting as high as this personality's trigger?"""
        return op.certainty("Shooting") >= float32(self.rules.parameters["TriggerHappiness"])

    def do_pass(self, cards):
        """EP.DoPass: the count of cards to pass so far, or None if this would make more than three.  Newest first."""
        count = len(cards) + self.number_of_pass_cards
        if not cards or count > 3:
            return None
        for card in cards:
            self.pass_cards.insert(0, card)
        for card in list(cards):
            self.hand.remove(card)
        self.number_of_pass_cards = count
        return count

    def _opponents(self):
        return self.left, self.right, self.across

    def get_opponent(self, seat):
        """EP.GetOpponent, by seat."""
        return {1: self.left, 2: self.across, 3: self.right}[(seat - self.seat) % 4]

    def hearty_non_shooter_void_suits(self):
        """Suits some opponent is void in, if not the shooter, and if it is still holding hearts."""
        return {suit for op in self._opponents() if op is not self.shooter and "H" not in op.voids for suit in op.voids}

    def hearty_opponent_void_suits(self):
        return {suit for op in self._opponents() if "H" not in op.voids for suit in op.voids}

    # ---- the six messages

    def give_hand(self, hand, seat):
        """EP.GiveHand.  MaggieLocation isn't reset here, only set, as in 1986.  It is always Elsewhere by now, since
        the queen is played in every deal."""
        self.seat = seat
        self.hand = Hand(hand)
        self.maggie_status = "NotPlayed"
        self.trick_number = 0
        self.history.init()
        if self.hand.has(QUEEN):
            self.maggie_location = "InHand"
        for location, op in zip(_LOCATIONS, (self.left, self.right, self.across)):
            op.init((seat - 1 + _OFFSET[location]) % 4 + 1)
        self._has_passed = False

    def pass_out(self, view):
        """EP.PassOut.  Medley sends this on a deal with no pass too, and that is when the strategy is chosen."""
        self._has_passed = True
        self.thought = None
        self.strategy = None
        _, self.strategy = self.session.first("initial.evaluation", "Strategy")
        self.number_of_pass_cards = 0
        self.pass_dir = view["direction"]
        self.pass_cards = []
        if not self.pass_dir:
            return []
        rule_class = STRATEGIES[self.strategy]["pass"]
        if self.strategy == "Minimizing":
            self.session.forget(POOR_SPADES)
        fired = []
        while self.number_of_pass_cards != 3:  # EP.MinPass and EP.ShootPass.
            rule, _ = self.session.first(rule_class, "More Cards Selected")
            fired.append(rule.name)
        cards = list(self.pass_cards)
        self._passed_to_opponent(cards)
        self.thought = Thought(rule=", ".join(fired))  # The passing rules give no reasons, only their names.
        return cards

    def _passed_to_opponent(self, cards):
        self.get_opponent((self.seat - 1 + _OFFSET[self.pass_dir]) % 4 + 1).hand_cards.extend(cards)

    def pass_in(self, cards):
        """EP.PassIn."""
        self.pass_in_cards = cards
        self.pass_in_from = self.get_opponent((self.seat - 1 - _OFFSET[self.pass_dir]) % 4 + 1)
        for card in cards:
            self.hand.add(card)
        self.maggie_location = "InHand" if self.hand.has(QUEEN) else "Elsewhere"
        self._opinion("opponent.passin.evaluation", self.pass_in_from)
        _, self.strategy = self.session.first("passin.evaluation", "Strategy")

    def play(self, view):
        """EP.Play."""
        if not self._has_passed:  # A table that doesn't send PassOut on a deal with no pass.
            self.pass_out({"direction": None})
        trick = view["trick"]
        rule, card = self._choose(trick["leader"], trick["cards"], view["hearts_broken"], view["first_trick"])
        self.hand.remove(card)
        self.thought = Thought(text=self.session.reason, rule=rule.name if rule else None)
        return card

    def _choose(self, leader, trick_cards, hearts_broken, first_trick):
        self.legals = self.hand.legal(trick_cards, hearts_broken, first_trick)
        if trick_cards:
            mode = "FollowSuit" if trick_cards[0][0] == self.legals[0][0] else "Dump"
        else:
            mode = "Lead"
        self.current_trick = Trick(leader, list(trick_cards))
        self.trick_number += 1
        if self.strategy == "Shooting":
            self.session.forget(WEAKEST_SUIT)
        return self.session.first(STRATEGIES[self.strategy][mode], "PlayCard")

    def trick(self, trick):
        """EP.Trick, with EP.UpdateModel for each opponent."""
        finished = Trick(trick["leader"], list(trick["cards"]), trick["winner"])
        self.current_trick = finished
        if QUEEN in finished.cards:
            self.maggie_status = "Played"
            self.maggie_location = "Elsewhere"
        winner = finished.winner
        points = self.history.compute_stats(finished, _WHERE[(winner - self.seat) % 4])
        if winner != self.seat:
            self.get_opponent(winner).points = points
        for op in (self.left, self.right, self.across):
            if op.seat == winner:
                op.tricks_won.insert(0, finished)
            card = finished.play_of(op.seat)
            op.played_cards.insert(0, card)
            if card[0] != finished.lead_suit and finished.lead_suit not in op.voids:
                op.voids.insert(0, finished.lead_suit)
            self._opinion("opponent.trick.evaluation", op)
        _, self.strategy = self.session.first("trick.evaluation", "Strategy")

    def results(self, scores):
        """EP.Results: "Presently no storing of results"."""

    def decide(self, view):
        """The card or cards, and the Thought, for any position in a complete seat view, leaving this player as it was.

        It replays the deal in a new Expert: the dealt hand is the hand now plus what this seat has played and passed,
        minus what it received.  It runs its own pass, for the strategy and bookkeeping, then takes back those cards for
        the ones actually passed.  Everything a rule reads rebuilds, so this gives what the Expert that played the game
        gave.  Its slots either reset each deal or come from the hand, the pass and the tricks, and that includes the
        opponent models and certainties, which depend only on the finished tricks.  Nothing read from earlier deals
        survives: the totals are never consulted, and Shooter is only read while Eclipsing, after being set this deal.
        """
        replay = Expert(self.name, self.rules)
        seat = view["seat"]
        if view["decision"] == "pass":
            replay.give_hand(view["hand"], seat)
            cards = replay.pass_out(view)
            return cards, replay.thought
        if not view["legal"]:
            return None, None  # It isn't this seat's turn.
        history = view["history"]
        mine = [t["cards"][(seat - t["leader"]) % 4] for t in history]
        passed, received = view["passed"], view["received"]
        dealt = [c for c in view["hand"] + mine + passed if c not in received]
        replay.give_hand(dealt, seat)
        replay.pass_out({"direction": view["direction"]})
        if view["direction"]:
            replay.hand = Hand([c for c in dealt if c not in passed])
            replay.pass_cards = list(passed)
            replay.get_opponent((seat - 1 + _OFFSET[view["direction"]]) % 4 + 1).hand_cards = list(passed)
            replay.pass_in(received)
        for trick, card in zip(history, mine):
            replay.trick_number += 1
            replay.hand.remove(card)
            replay.trick(trick)
        card = replay.play(view)
        return card, replay.thought
