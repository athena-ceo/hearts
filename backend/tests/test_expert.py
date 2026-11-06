# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The Expert's rules against the listing, its engine, decide at every position, and rule variants as overlays."""
import random
import re
from pathlib import Path

import pytest

from hearts import Game
from hearts.conformance import read_fixture
from hearts.players import Clown, Conservative, Expert
from hearts.players.base import play_game
from hearts.players.cardlib import Shouldnt, Trick, cards_between, lower, max_card, min_card
from hearts.players.expert import RULES_1986, variant
from hearts.players.expert.memory import combine, float32

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


def listing():
    """Every KEE.DEFRULE in medley/EXPERT: (class, name, weight, reason, strategy, certainty)."""
    text = (ROOT / "medley" / "EXPERT").read_text()
    rules = []
    for match in re.finditer(r'\(KEE\.DEFRULE \(QUOTE (\S+)\) \(QUOTE (\S+)\) (\d+)\n\s+\(QUOTE (.*)\)\)\n', text):
        rule_class, name, weight, body = match.groups()
        reason = re.search(r'\(QUOTE LatestReason\) "([^"]*)"', body)
        certainty = re.search(r'IS (Shooting|Minimizing) IS (-?[\d.]+) :UPDATE\)\)$', body)
        rules.append((rule_class, name, int(weight), reason and reason.group(1),
                      certainty and certainty.group(1), certainty and float(certainty.group(2))))
    return rules


def test_every_rule_is_the_listings():
    rules = listing()
    assert len(rules) == 97
    ours = [(r.rule_class, r.name, r.weight, r.reason, *(r.conclusion_constants if r.goal == "Certainty" else (None, None)))
            for r in RULES_1986.rules]
    assert sorted(ours, key=str) == sorted(rules, key=str)


def test_rules_are_tried_in_the_order_keeloops_tries_them():
    """Descending weight, then the listing's order: KEE.InsertByWeight."""
    order = {}
    for rule_class, name, weight, *_ in listing():
        rules = order.setdefault(rule_class, [])
        at = next((i for i, (w, _) in enumerate(rules) if weight > w), len(rules))
        rules.insert(at, (weight, name))
    assert {c: [n for _, n in rules] for c, rules in order.items()} \
        == {c: [r.name for r in RULES_1986.of(c)] for c in order}


def test_parameters_are_the_knowledge_bases():
    text = (ROOT / "medley" / "expert-kb.lisp").read_text()
    values = re.search(r"\(DEFCLASS EP\.Personality.*?\(InstanceVariables (.*?)\)\)\n", text, re.S).group(1)
    found = {k: float(v) for k, v in re.findall(r"\((\w+) ([\d.]+)\)", values)}
    assert found == {k: float(v) for k, v in RULES_1986.parameters.items()}


def test_card_functions_answer_as_medley_does():
    """Each answer was checked in Medley."""
    assert min_card(["C5", "D5", "H5"]) == "H5" and max_card(["C5", "D5", "H5"]) == "C5"
    assert lower("C5", "D5") and lower("D5", "C5") and lower("C5", None) and lower(None, "C5")
    cards = ["C2", "C3", "C4", "C5"]
    who = [[Trick(leader, cards).who_played(c) for c in cards] for leader in (1, 2, 3, 4)]
    assert who == [[1, 3, 5, 3], [2, 4, 2, 4], [3, 5, 3, 5], [4, 2, 4, 2]]
    assert Trick(3, ["C2", "C3"]).who_played("C4") == 3


def test_certainties_combine_in_32_bits():
    """The overview's Example 2: suspected at .44 after the pass, .51 after the first trick."""
    after_pass = combine(combine(None, float32(0.2)), float32(0.3))
    assert abs(after_pass - 0.44) < 1e-6
    assert after_pass < 0.5 <= combine(after_pass, float32(0.12))
    low, high = float32(0.2), float32(-0.99)
    assert combine(low, high) == float32(float32(low + high) / float32(1 - low))


def test_decide_gives_what_the_expert_that_played_gave():
    """A new Expert, at every pass and card of a game, from the seat's view alone.  See Expert.decide for why nothing is
    lost.  Replays the fixture's hands, which cover every direction and strategy."""
    positions = []

    class Checked(Expert):
        def pass_out(self, view):
            if view["direction"]:
                decided = Expert().decide(view)
                cards = super().pass_out(view)
                positions.append((view, decided, (cards, self.thought)))
                return cards
            return super().pass_out(view)

        def play(self, view):
            decided = Expert().decide(view)
            card = super().play(view)
            positions.append((view, decided, (card, self.thought)))
            return card

    records = read_fixture(FIXTURES / "medley_expert_table.jsonl.gz")[:60]
    game = Game(deals=((r["hands"], None if r["pass"] == "None" else r["pass"]) for r in records), over_score=100000)
    play_game([Checked() for _ in range(4)], game, deals=len(records))
    assert len(positions) == 60 * 52 + 45 * 4
    for view, (card, thought), (played, played_thought) in positions:
        assert card == played, view
        assert thought == played_thought, view


def test_decide_leaves_the_player_as_it_was():
    expert = Expert()
    deal = Game(seed=3).next_deal()
    expert.give_hand(deal.dealt[0], 1)
    before = list(expert.hand.cards())
    expert.decide(deal.view(1))
    assert expert.hand.cards() == before and expert.strategy is None
    assert Expert().decide(deal.view(1))[0] is not None


def test_a_table_that_skips_pass_out_on_a_deal_with_no_pass_gets_the_same_card():
    """The strategy is chosen in PassOut, which H.Deal sends even with no pass."""
    game = Game(deals=iter([(read_fixture(FIXTURES / "medley_expert_table.jsonl.gz")[3]["hands"], None)]), over_score=100000)
    deal = game.next_deal()
    told, untold = Expert(), Expert()
    seat = deal.to_play
    for player in (told, untold):
        player.give_hand(deal.dealt[seat - 1], seat)
    told.pass_out(deal.view(seat))
    assert told.play(deal.view(seat)) == untold.play(deal.view(seat))
    assert told.thought == untold.thought


def test_expert_plays_legally_at_mixed_tables():
    """The Administrator of 1986 checks nothing, so Medley alone wouldn't show an illegal card.  Deal refuses one."""
    for seed in range(40):
        r = random.Random(seed)
        players = [Expert(), Clown(seed=seed), Conservative(seed=seed), Expert()]
        r.shuffle(players)
        game = play_game(players, Game(seed=seed))
        assert game.finished
        assert not [p.rule_errors for p in players if p.kind == "expert" and p.rule_errors]


def test_passing_as_a_shooter_with_only_spades_left_stops_the_game_as_in_medley():
    """In Medley, DoPass is asked for no card: Help! Shouldn't happen, in a break window.  It takes 11 spades or more."""
    shooter = Expert(rules=RULES_1986.overlay(parameters={"POMinShootPoints": 0, "POMaxLowSpades": 13}))
    spades = ["S" + r for r in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")]
    shooter.give_hand(spades, 1)
    with pytest.raises(Shouldnt):
        shooter.pass_out({"direction": "Left"})


def test_every_play_says_why_and_passes_name_their_rules():
    players = [Expert() for _ in range(4)]
    game = play_game(players, Game(seed=11), deals=2)
    cards = [e for e in game.events if e["type"] == "card"]
    assert len(cards) == 104
    assert all(e["thought"]["text"] and e["thought"]["rule"] for e in cards)
    assert any(e["thought"] == {"text": "One choice.", "rule": "one.choice"} for e in cards)


# ---- rule variants as overlays: x-sr-plus, as text, for one seat

def test_an_overlay_for_one_seat_scores_what_medley_scored():
    """x-sr-plus in seat 1 against three 1986 Experts, deals 4001-4200 of Medley's run, out/bench/fresh/x-sr-plus."""
    records = read_fixture(FIXTURES / "medley_x_sr_plus.jsonl.gz")
    game = Game(deals=((r["hands"], None if r["pass"] == "None" else r["pass"]) for r in records), over_score=100000)
    players = [Expert(rules=variant("x-sr-plus")), Expert(), Expert(), Expert()]
    for record in records:
        play_game(players, game, deals=game.number + 1)
        assert game.deal.scores == record["scores"], record["deal"]


def test_an_overlay_touches_only_its_seat_and_its_rules():
    changed = RULES_1986.overlay(remove=["one.choice"], parameters={"SpadeProtLen": 5})
    assert RULES_1986.parameters["SpadeProtLen"] == 4 and changed.parameters["SpadeProtLen"] == 5
    assert "one.choice" in [r.name for r in RULES_1986.of("lead.play")]
    for rule_class in ("lead.play", "shoot.dump", "eclipse.follow"):
        assert "one.choice" not in [r.name for r in changed.of(rule_class)]
    with pytest.raises(ValueError):
        RULES_1986.overlay(parameters={"SpadeProtection": 5})


def test_a_changed_parameter_changes_what_the_rules_do():
    """The phrase in the rule reads the value from whichever rule base is running, though the rule is shared."""
    hand = ["S2", "S3", "S4", "S5", "SA", "C2", "C3", "C4", "C5", "C6", "D2", "D3", "H2"]
    choices = []
    for rules in (RULES_1986, RULES_1986.overlay(parameters={"SpadeProtLen": 6})):
        expert = Expert(rules=rules)
        expert.give_hand(hand, 1)
        choices.append(expert.pass_out({"direction": "Left"}))
    assert "SA" not in choices[0] and "SA" in choices[1]
