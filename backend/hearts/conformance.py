# Copyright (c) 2026 Athena Decision Systems SAS.
"""Does a table of Python players do what the same table did in Medley?  Plays a whole run in order, as Medley did,
and compares every seat's passes, every trick, every reason, every score and every rule fired.

A record is one deal from a traced benchmark run: bench/bench.lisp's tricks.jsonl joined with deals.jsonl.  Used by
tests/test_conformance.py on committed fixtures and scripts/medley_conformance.py on whole runs in out/bench.
"""
import gzip
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .game import Game
from .players.base import play_game
from .players.conservative import Conservative
from .players.expert import Expert

OVER_SCORE = 100000  # bench/bench.lisp's Game.OverScore.


def load_run(directory, limit=None):
    """The records of a run directory, out/bench/RUN/PLAYER."""
    directory = Path(directory)
    records = []
    with open(directory / "deals.jsonl", encoding="utf-8") as deals, \
            open(directory / "tricks.jsonl", encoding="utf-8") as tricks:
        for deal_line, trick_line in zip(deals, tricks):
            summary, record = json.loads(deal_line), json.loads(trick_line)
            if summary["deal"] != record["deal"]:
                raise ValueError(f"deals.jsonl has deal {summary['deal']} where tricks.jsonl has {record['deal']}")
            record.update({"pass": summary["pass"], "scores": summary["scores"]})
            record.pop("reasons", None)  # The same as seat_reasons[0].
            records.append(record)
            if limit and len(records) >= limit:
                break
    return records


def write_fixture(records, path):
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        for record in records:
            f.write((json.dumps(record, separators=(",", ":")) + "\n").encode())


def read_fixture(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def medley_card(card):
    """Card.Print: "S10" is 10S."""
    return card[1:] + card[0]


class _ReplayedConservative(Conservative):
    """A Conservative whose one random choice is the one Medley's RAND made.  The choice still has to be open to it."""

    def __init__(self, table):
        super().__init__()
        self.table = table

    def play(self, view):
        self.position = len(view["history"]), len(view["trick"]["cards"])
        return super().play(view)

    def _random_spade(self, spades):
        self.table.random_choices += 1
        trick, played = self.position
        card = self.table.record["tricks"][trick]["cards"][played]
        if card not in spades:
            self.table.report.note("cards", self.table.record, None, trick, card, spades)
            return spades[0]
        return card


@dataclass
class Mismatch:
    kind: str
    deal: int
    seat: int | None
    trick: int | None  # From 0.
    medley: object
    python: object
    record: dict = field(repr=False, default=None)


@dataclass
class Report:
    deals: int = 0
    deals_with_mismatches: int = 0
    compared: Counter = field(default_factory=Counter)
    mismatches: Counter = field(default_factory=Counter)
    first: list = field(default_factory=list)  # The first few mismatches, in order.
    random_choices: int = 0
    keep: int = 5

    def note(self, kind, record, seat, trick, medley, python, count=1):
        self.mismatches[kind] += count
        if len(self.first) < self.keep:
            self.first.append(Mismatch(kind, record["deal"], seat, trick, medley, python, record))

    @property
    def clean(self):
        return not self.mismatches

    def summary(self):
        lines = [f"{self.deals} deals, {self.deals_with_mismatches} with a mismatch"]
        for kind in sorted(self.compared):
            lines.append(f"  {kind}: {self.compared[kind]} compared, {self.mismatches[kind]} differ")
        if self.random_choices:
            lines.append(f"  Conservative's random spade: {self.random_choices} choices taken from the Medley log")
        return "\n".join(lines)


def describe(mismatch):
    """A first mismatch, with what a person needs to chase it in the Lisp."""
    r = mismatch.record
    lines = [f"deal {mismatch.deal} ({r['pass']}), {mismatch.kind}"
             + (f", seat {mismatch.seat}" if mismatch.seat else "")
             + (f", trick {mismatch.trick + 1}" if mismatch.trick is not None else ""),
             f"  Medley: {mismatch.medley}", f"  Python: {mismatch.python}",
             "  hands: " + " | ".join(" ".join(h) for h in r["hands"]),
             "  passed: " + " | ".join(" ".join(p) for p in r["passed"])]
    last = len(r["tricks"]) if mismatch.trick is None else mismatch.trick + 1
    for i, trick in enumerate(r["tricks"][:last]):
        cards = " ".join(trick["cards"])
        lines.append(f"  trick {i + 1}: seat {trick['leader']} led {cards}, seat {trick['winner']} won")
    if mismatch.seat:
        reasons = list(reversed(r["seat_reasons"][mismatch.seat - 1]))
        lines.extend(f"  seat {mismatch.seat}'s reason {i + 1}: {text}" for i, text in enumerate(reasons[:last]))
    return "\n".join(lines)


SEATS = {"expert": "EEEE", "conservative": "CCCC", "mixed": "CECE"}


class Table:
    """Four players going through a run, one deal at a time.  The kind says who sits where, as in SEATS.  `rules` gives
    its Experts a variant, which should differ from Medley: it is how the tests know a mismatch would show."""

    def __init__(self, kind, report=None, rules=None, rules_seat_1=None):
        self.report = report or Report()
        self.random_choices = 0
        self.record = None
        self.fired = []
        self.players = [Expert(rules=rules, trace=self.fired) if seat == "E" else _ReplayedConservative(self)
                        for seat in SEATS[kind]]
        if rules_seat_1:
            self.players[0] = Expert(rules=rules_seat_1, trace=self.fired)

    def play(self, records):
        """Plays the records, in order, reporting after each if asked.  Returns the report."""
        deals = ((r["hands"], None if r["pass"] == "None" else r["pass"]) for r in records)
        game = Game(deals=deals, over_score=OVER_SCORE)
        for record in records:
            self.record = record
            before = sum(self.report.mismatches.values())
            self.fired.clear()
            play_game(self.players, game, deals=game.number + 1)
            self._compare(record, game.deal)
            self.report.deals += 1
            if sum(self.report.mismatches.values()) > before:
                self.report.deals_with_mismatches += 1
        self.report.random_choices = self.random_choices
        return self.report

    def _compare(self, r, deal):
        report = self.report
        for i in range(4):
            expected, actual = r["passed"][i], deal.passed[i]
            report.compared["pass cards"] += len(expected)
            if expected != actual:
                report.note("pass cards", r, i + 1, None, expected, actual, _differing(expected, actual))
        for t, (expected, actual) in enumerate(zip(r["tricks"], deal.history)):
            report.compared["cards"] += len(expected["cards"])
            if any(expected[key] != actual[key] for key in ("leader", "winner", "cards")):
                report.note("cards", r, None, t, {k: expected[k] for k in ("leader", "cards", "winner")}, actual,
                            max(_differing(expected["cards"], actual["cards"]), 1))
        report.compared["scores"] += 4
        if r["scores"] != deal.scores:
            report.note("scores", r, None, None, r["scores"], deal.scores, _differing(r["scores"], deal.scores))
        reasons = [[], [], [], []]
        for event in deal.events:
            if event["type"] == "card":
                text = (event.get("thought") or {}).get("text")
                reasons[event["seat"] - 1].insert(0, f"{medley_card(event['card'])} {text}")
        for i, player in enumerate(self.players):
            if player.kind == "expert":
                expected, actual = r["seat_reasons"][i][::-1], reasons[i][::-1]  # Medley's are newest first.
                report.compared["reasons"] += len(expected)
                if expected != actual:
                    t = next((n for n, (a, b) in enumerate(zip(expected, actual)) if a != b), None)
                    report.note("reasons", r, i + 1, t, expected[t], actual[t], _differing(expected, actual))
            elif r["seat_reasons"][i]:
                report.note("reasons", r, i + 1, None, r["seat_reasons"][i], [])
        if "fired" in r:
            expected = r["fired"][::-1]
            report.compared["rules fired"] += len(expected)
            if expected != self.fired:
                n = next((n for n, (a, b) in enumerate(zip(expected, self.fired)) if a != b),
                         min(len(expected), len(self.fired)))
                report.note("rules fired", r, None, None, expected[n:n + 8], self.fired[n:n + 8],
                            _differing(expected, self.fired))


def _differing(expected, actual):
    return sum(1 for a, b in zip(expected, actual) if a != b) + abs(len(expected) - len(actual))
