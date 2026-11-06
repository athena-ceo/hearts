# Copyright (c) 2026 Athena Decisions Systems SAS.
"""After a deal: what each seat did and why, beside what the Expert and the network would have done."""
from __future__ import annotations

from .game import Deal
from .players import BOT_KINDS, make_bot
from .players.base import play_game


def deal_events(events, number):
    """The events of one deal, from its record."""
    start = next((i for i, e in enumerate(events) if e["type"] == "deal" and e["number"] == number), None)
    if start is None:
        return None
    end = next((i for i in range(start, len(events)) if events[i]["type"] == "deal_end"), None)
    return None if end is None else events[start:end + 1]


def _advice(view):
    result = {}
    for kind in ("expert", "network"):
        if kind in BOT_KINDS:
            answer, thought = make_bot(kind).decide(view)
            result[kind] = {"answer": answer, "thought": thought.as_dict() if thought else None}
    return result


def what_if(kind, deal, seat, seats, totals):
    """The same cards with this kind in the seat.  Other players keep their kinds, and a person becomes an Expert
    if there is one.  They start with no memory of earlier deals, so this is close to the real table, not exact."""
    from .game import Game

    other = "expert" if "expert" in BOT_KINDS else "network"
    players = []
    for i, s in enumerate(seats):
        chosen = kind if i + 1 == seat else (s["kind"] if s["kind"] != "person" else other)
        players.append(make_bot(chosen, None, i))
    game = Game(deals=iter([(deal.dealt, deal.direction)]), over_score=-1000)
    game.totals = list(totals)
    play_game_once(players, game)
    return game.deal.scores


def play_game_once(players, game):
    """One deal only: the over score has already been passed once it ends."""
    return play_game(players, game)


def review(events, number, seat, seats):
    """Everything about a finished deal, for one seat.  Returns None if it hasn't finished."""
    record = deal_events(events, number)
    if record is None:
        return None
    first = record[0]
    deal = Deal(first["hands"], first["direction"], number)
    you, tricks = [], []
    if deal.direction:
        passes = {e["seat"]: e["cards"] for e in record if e["type"] == "passed"}
        if seat:
            you.append({"decision": "pass", "trick": None, "you": passes[seat],
                        "advice": _advice(deal.view(seat))})
        for s in range(1, 5):
            deal.submit_pass(s, passes[s])
    thoughts = []
    for event in record:
        if event["type"] != "card":
            continue
        s = event["seat"]
        if s == seat and len(deal.legal(s)) > 1:
            you.append({"decision": "play", "trick": len(deal.history) + 1, "you": event["card"],
                        "thought": event.get("thought"), "advice": _advice(deal.view(s))})
        thoughts.append({"trick": len(deal.history) + 1, "seat": s, "card": event["card"],
                         "thought": event.get("thought")})
        deal.submit_play(s, event["card"])
    for t in deal.history:
        tricks.append({"leader": t["leader"], "cards": t["cards"], "winner": t["winner"]})
    result = {"number": number, "direction": deal.direction, "dealt": deal.dealt, "passed": deal.passed,
              "tricks": tricks, "scores": deal.scores, "thoughts": thoughts, "decisions": you, "what_if": None}
    if seat and "network" in BOT_KINDS and seats[seat - 1]["kind"] != "network":
        result["what_if"] = {"kind": "network", "label": BOT_KINDS["network"].label,
                             "scores": what_if("network", deal, seat, seats, [0, 0, 0, 0])}
    return result
