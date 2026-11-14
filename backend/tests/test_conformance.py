# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Python players against real Medley runs, card for card and reason for reason.

The fixtures are the first 200 deals of traced runs: four Experts, four Conservatives, and the two taking turns, made by
python3 bench/run.py --run conform --trace, then scripts/medley_conformance.py --fixture.  Each is one long game, so it
is played whole and in order, with Medley's over score.  scripts/medley_conformance.py runs all of out/bench.
"""
from pathlib import Path

import pytest

from hearts import DIRECTIONS, Game
from hearts.conformance import Table, read_fixture
from hearts.players import Conservative, Player
from hearts.players.base import play_game
from hearts.players.expert import RULES_1986

FIXTURES = Path(__file__).parent / "fixtures"
RUNS = {"expert": "medley_expert_table", "conservative": "medley_conservative_table", "mixed": "medley_mixed_table"}


def fixture(kind):
    return read_fixture(FIXTURES / f"{RUNS[kind]}.jsonl.gz")


@pytest.mark.parametrize("kind", RUNS)
def test_a_table_matches_medley(kind):
    records = fixture(kind)
    report = Table(kind).play(records)
    assert report.clean, report.summary()
    assert report.deals == len(records) == 200
    assert report.compared["cards"] == 200 * 52
    assert report.compared["pass cards"] == 150 * 12
    assert report.compared["scores"] == 200 * 4
    experts = {"expert": 4, "conservative": 0, "mixed": 2}[kind]
    assert report.compared["reasons"] == 200 * 13 * experts
    assert bool(report.compared["rules fired"]) == bool(experts)


SHOOT = {"POMaxLowSpades": 13, "POMaxLoserHearts": 13, "PIMaxLowSpades": 13, "PIMaxLoserHearts": 13,
         "POMinShootPoints": 0, "PIMinShootPoints": 0, "PILowestHeart": 2}


def test_rare_rules_match_medley():
    """bench/rules/x-conform-*.lisp, whose personalities and deals reach rules the 1986 table rarely or never does.
    Seat 1 shoots on any hand and the others suspect at once (rare shooting and eclipsing rules), and then made-up deals,
    each giving one seat nearly all the spades (highest.pick)."""
    duel = Table("expert", rules=RULES_1986.overlay(parameters={"TriggerHappiness": 0.1}),
                 rules_seat_1=RULES_1986.overlay(parameters=SHOOT))
    report = duel.play(read_fixture(FIXTURES / "medley_duel_table.jsonl.gz"))
    assert report.clean, report.summary()
    assert report.deals == 100
    spades = Table("expert").play(read_fixture(FIXTURES / "medley_spades_table.jsonl.gz"))
    assert spades.clean, spades.summary()
    assert spades.deals == 8
    assert "highest.pick" in {name for r in read_fixture(FIXTURES / "medley_spades_table.jsonl.gz") for name in r["fired"]}


def test_the_comparison_would_see_a_difference():
    """Without one rule that fires, the same run has to differ, or the comparison isn't comparing."""
    records = fixture("expert")
    report = Table("expert", rules=RULES_1986.overlay(remove=["dump.queen"])).play(records)
    assert report.mismatches["cards"] and report.mismatches["reasons"] and report.mismatches["rules fired"]
    assert report.first and report.first[0].medley != report.first[0].python


def test_conservative_decide_gives_what_the_one_that_played_gave():
    class Steady(Conservative):
        """With its random spade fixed, since Medley's RAND isn't reproduced."""
        def _random_spade(self, spades):
            return max(spades)

    positions = []

    class Checked(Steady):
        def pass_out(self, view):
            decided = Steady().decide(view) if view["direction"] else None
            cards = super().pass_out(view)
            if decided:
                positions.append((view, decided, (cards, self.thought)))
            return cards

        def play(self, view):
            decided = Steady().decide(view)
            card = super().play(view)
            positions.append((view, decided, (card, self.thought)))
            return card

    records = fixture("conservative")[:100]
    game = Game(deals=((r["hands"], None if r["pass"] == "None" else r["pass"]) for r in records), over_score=100000)
    play_game([Checked() for _ in range(4)], game, deals=len(records))
    assert len(positions) == 100 * 52 + 75 * 4
    for view, decided, played in positions:
        assert decided == played, view


class Recorder(Player):
    """Notes every message it gets."""

    def __init__(self, log):
        super().__init__()
        self.log = log

    def give_hand(self, hand, seat):
        super().give_hand(hand, seat)
        self.log.append(("GiveHand", seat))

    def pass_out(self, view):
        self.log.append(("PassOut", self.seat, view["direction"]))
        return view["hand"][:3] if view["direction"] else []

    def pass_in(self, cards):
        self.log.append(("PassIn", self.seat))

    def play(self, view):
        self.log.append(("Play", self.seat))
        return view["legal"][0]

    def trick(self, trick):
        self.log.append(("Trick", self.seat))

    def results(self, scores):
        self.log.append(("Results", self.seat, scores))


class ForcedToo(Recorder):
    plays_forced_cards = True


@pytest.mark.parametrize("deal_number", [1, 4])
def test_the_six_messages_come_in_medleys_order(deal_number):
    """H.PlayGame and H.Deal: GiveHand 1-4, PassOut 1-4 (with no pass too), PassIn 1-4 only if there was one, then 13 times
    Play for each seat in turn and Trick 1-4, then Results 1-4 with the running totals."""
    log = []
    game = Game(seed=5)
    players = [ForcedToo(log) for _ in range(4)]
    play_game(players, game, deals=deal_number)
    direction = DIRECTIONS[deal_number - 1]
    seen = log[len(log) - 1 - log[::-1].index(("GiveHand", 1)):]
    seats = [1, 2, 3, 4]
    assert seen[:4] == [("GiveHand", s) for s in seats]
    assert seen[4:8] == [("PassOut", s, direction) for s in seats]
    at = 8
    if direction:
        assert seen[8:12] == [("PassIn", s) for s in seats]
        at = 12
    for trick in game.deal.history:
        leader = trick["leader"]
        assert seen[at:at + 4] == [("Play", (leader - 1 + i) % 4 + 1) for i in range(4)]
        assert seen[at + 4:at + 8] == [("Trick", s) for s in seats]
        at += 8
    assert seen[at:] == [("Results", s, game.totals) for s in seats]


def test_every_seat_hears_every_trick_even_when_its_card_was_forced():
    log = []
    players = [Recorder(log) for _ in range(4)]
    play_game(players, Game(seed=5), deals=1)
    assert sum(1 for m in log if m[0] == "Trick") == 52
    assert sum(1 for m in log if m[0] == "Play") < 52  # Without plays_forced_cards it isn't asked for forced cards.
