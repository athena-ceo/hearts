# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The core against real Medley games: the same legal cards, winners and scores, and the rules it enforces."""
import gzip
import json
import random
from pathlib import Path

import pytest

from hearts import DECK, DIRECTIONS, Deal, Game, IllegalMove, legal_cards, pass_target, trick_winner
from hearts.game import visible_to
from hearts.players import BOT_KINDS, Clown, make_bot
from hearts.players.base import play_game
from hearts.players.network import Network

FIXTURES = Path(__file__).parent / "fixtures"


def medley_games():
    with gzip.open(FIXTURES / "medley_games.jsonl.gz", "rt") as f:
        return [json.loads(line) for line in f]


def test_replaying_medley_games_gives_the_same_scores():
    games = medley_games()
    for game in games:
        direction = None if game["pass"] == "None" else game["pass"]
        d = Deal(game["hands"], direction, game["deal"])
        if direction:
            for seat in range(1, 5):
                d.submit_pass(seat, game["passed"][seat - 1])
        for trick in game["tricks"]:
            assert d.leader == trick["leader"]
            for card in trick["cards"]:
                d.submit_play(d.to_play, card)
            assert d.history[-1]["winner"] == trick["winner"]
        assert d.phase == "done"
        assert d.scores == game["scores"], game["deal"]
    assert len(games) == 200


def test_network_passes_as_recorded():
    net = Network()
    rows = json.loads((FIXTURES / "network_passes.json").read_text())
    assert rows
    for r in rows:
        view = {"decision": "pass", "seat": 1, "direction": r["direction"], "hand": r["hand"]}
        assert sorted(net.pass_out(view)) == sorted(r["network"])


def test_illegal_moves_are_refused():
    deck = list(DECK)
    random.Random(1).shuffle(deck)
    d = Deal([deck[i * 13:(i + 1) * 13] for i in range(4)], "Left")
    hand = d.hands[0]
    with pytest.raises(IllegalMove):
        d.submit_pass(1, hand[:2])
    with pytest.raises(IllegalMove):
        d.submit_pass(1, [hand[0], hand[0], hand[1]])
    with pytest.raises(IllegalMove):
        d.submit_pass(1, d.hands[1][:3])
    with pytest.raises(IllegalMove):
        d.submit_play(1, hand[0])
    for seat in range(1, 5):
        d.submit_pass(seat, d.hands[seat - 1][:3])
    seat = d.to_play
    assert d.legal(seat) == ["C2"]
    other = next(c for c in d.hands[seat - 1] if c != "C2")
    with pytest.raises(IllegalMove):
        d.submit_play(seat, other)
    with pytest.raises(IllegalMove):
        d.submit_play(seat % 4 + 1, "C2")


def test_a_whole_game_of_clowns_ends_and_adds_up():
    game = play_game([Clown(seed=i) for i in range(4)], Game(seed=7))
    assert game.finished and max(game.totals) >= 100
    last = game.events[-1]
    assert last["type"] == "game_end" and min(game.totals) == game.totals[last["winners"][0] - 1]
    assert game.events[1]["direction"] == DIRECTIONS[0]


def test_views_and_events_keep_other_hands_hidden():
    game = Game(seed=3)
    deal = game.next_deal()
    view = deal.view(2)
    assert view["hand"] == deal.hands[1] and "hands" not in view
    start = visible_to(deal.events[0], 2)
    assert start["hands"] == deal.dealt[1]
    assert visible_to(deal.events[0], None)["hands"] is None
    game.submit_pass(1, deal.hands[0][:3])
    hidden = visible_to(deal.events[-1], 2)
    assert "cards" not in hidden and visible_to(deal.events[-1], 1)["cards"] == deal.passed[0]


def test_helpers_match_the_1986_tables():
    assert [pass_target(s, "Left") for s in (1, 2, 3, 4)] == [2, 3, 4, 1]
    assert [pass_target(s, "Across") for s in (1, 2, 3, 4)] == [3, 4, 1, 2]
    assert [pass_target(s, "Right") for s in (1, 2, 3, 4)] == [4, 1, 2, 3]
    assert trick_winner(2, ["D9", "D7", "D6", "SQ"]) == 2
    assert legal_cards(["HA", "SQ", "C3"], ["D2"], False, True) == ["C3"]
    assert legal_cards(["HA", "H2"], [], False, False) == ["HA", "H2"]


def _play_out(game):
    while game.deal.phase != "done":
        for seat in game.deal.waiting():
            if game.deal.phase == "pass":
                game.submit_pass(seat, game.deal.legal(seat)[:3])
            else:
                game.submit_play(seat, game.deal.legal(seat)[0])


def test_a_game_ends_only_when_someone_goes_over_the_score_as_game_winner_has_it():
    first = Game(seed=5)
    first.next_deal()
    _play_out(first)
    highest = max(first.totals)
    exactly = Game(seed=5, over_score=highest)
    exactly.next_deal()
    _play_out(exactly)
    assert not exactly.finished  # IGREATERP: exactly the score plays on.
    over = Game(seed=5, over_score=highest - 1)
    over.next_deal()
    _play_out(over)
    assert over.finished
    end = over.events[-1]
    assert end["type"] == "game_end"
    assert end["winners"] == [i + 1 for i, t in enumerate(over.totals) if t == min(over.totals)]


@pytest.mark.parametrize("kind", sorted(BOT_KINDS))
def test_every_bot_takes_pass_out_on_a_deal_with_no_pass_as_h_deal_sends_it(kind):
    game = Game(seed=9)
    deal = game.next_deal()
    while deal.direction:
        game.deal.phase = "done"  # Only the deal's direction matters here: find the deal with no pass.
        game.deal.scores = [0, 0, 0, 0]
        deal = game.next_deal()
    bot = make_bot(kind, seed=1)
    bot.give_hand(deal.dealt[0], 1)
    assert not bot.pass_out(deal.view(1))
