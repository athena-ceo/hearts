# Copyright (c) 2026 Athena Decisions Systems SAS.
"""Tables: one asyncio task per game, holding its seats and connections.

The game itself is hearts.game.Game.  A table asks each seat for its move, writes each event before announcing
it, and sends every client only what its seat may see.  A restart rebuilds a table by replaying its events.
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from collections import deque

from .game import Game, IllegalMove, visible_to
from .players import BOT_KINDS, make_bot

log = logging.getLogger("hearts.tables")
FALLBACK = "conservative"  # Who plays for someone whose time runs out.
ADVISERS = ("expert", "network")


class Table:
    def __init__(self, manager, table_id, seed, config, seats, status="open"):
        self.manager = manager
        self.id = table_id
        self.seed = seed
        self.config = config
        self.seats = seats  # [{"kind": "person", "player_id": ..., "name": ...} | {"kind": "person"} | {"kind": bot}]
        self.status = status
        self.game = Game(seed=seed, over_score=config.get("over_score", 100))
        self.bots = {}
        self.connections = {}  # send coroutine -> seat number or None
        self.wake = asyncio.Event()
        self.seq = 0
        self.persisted = 0
        self.script = deque()
        self.deadline = None
        self.task = None
        self.fill_task = None
        self.created = time.time()
        self.caught_up = asyncio.Event()
        self.advice = {}  # The latest advice for each seat, sent again when someone connects.

    # Seats ----------------------------------------------------------------------------------------------------
    @property
    def study(self):
        return bool(self.config.get("study"))

    def seat_of(self, player_id):
        return next((i + 1 for i, s in enumerate(self.seats) if s.get("player_id") == player_id), None)

    def describe(self, player_id=None):
        deal = self.game.deal
        seat = self.seat_of(player_id) if player_id else None
        return {
            "id": self.id, "status": self.status, "study": self.study,
            "time_limit": self.config.get("time_limit"), "invite_only": bool(self.config.get("invite_only")),
            "seats": [{"kind": s["kind"], "name": self.seat_name(i + 1), "open": self.is_open(i + 1)}
                      for i, s in enumerate(self.seats)],
            "your_seat": seat, "your_turn": bool(seat and deal and self.status == "playing" and seat in deal.waiting()),
            "deal": self.game.number, "totals": list(self.game.totals),
            "waiting_for": [self.seat_name(s) for s in deal.waiting()] if deal and self.status == "playing" else [],
        }

    def is_open(self, seat):
        s = self.seats[seat - 1]
        return s["kind"] == "person" and not s.get("player_id")

    def seat_name(self, seat):
        s = self.seats[seat - 1]
        if s["kind"] == "person":
            return s.get("name")
        return s.get("name") or BOT_KINDS[s["kind"]].label

    def save(self):
        self.manager.store.save_table(self.id, self.seed, self.config, self.seats, self.status)

    def join(self, player, seat=None):
        if self.seat_of(player["id"]):
            return self.seat_of(player["id"])
        if seat is None:
            seat = next((i + 1 for i in range(4) if self.is_open(i + 1)), None)
        if seat is None or not 1 <= seat <= 4 or not self.is_open(seat):
            raise IllegalMove("That seat isn't free.")
        self.seats[seat - 1] = {"kind": "person", "player_id": player["id"], "name": player["name"]}
        self.save()
        self.maybe_start()
        return seat

    def fill_empty_seats(self):
        for i in range(4):
            if self.is_open(i + 1):
                self.seats[i] = {"kind": self.config.get("fill_with", "expert"), "name": _bot_name(self.seats, i)}
        self.save()
        self.maybe_start()

    def maybe_start(self):
        if self.status == "open" and not any(self.is_open(i + 1) for i in range(4)):
            self.status = "playing"
            self.save()
            self.task = asyncio.create_task(self.run())

    # Events ---------------------------------------------------------------------------------------------------
    def _emit(self, events):
        for event in events:
            self.seq += 1
            if self.seq <= self.persisted:  # Being rebuilt from the record.
                continue
            self.manager.store.append_event(self.id, self.seq, event)
            self.persisted = self.seq
            self._broadcast(event, self.seq)
        if self.seq >= self.persisted:
            self.caught_up.set()

    def client_event(self, event, seat, seq=None):
        shown = visible_to(event, seat)
        if "thought" in shown and not self.study:
            shown = {k: v for k, v in shown.items() if k != "thought"}
        return {**shown, "seq": seq} if seq is not None else shown

    def _broadcast(self, event, seq):
        for send, seat in list(self.connections.items()):
            self._send(send, self.client_event(event, seat, seq))

    def _send(self, send, message):
        send.queue.put_nowait(message)

    def _announce_turn(self):
        deal = self.game.deal
        message = {"type": "turn", "waiting": deal.waiting() if deal else [], "deadline": self.deadline}
        for send, seat in list(self.connections.items()):
            self._send(send, {**message, "view": deal.view(seat) if deal and seat else None})

    def snapshot(self, seat):
        deal = self.game.deal
        return {
            "type": "snapshot", "table": self.describe_for_seat(seat), "seq": self.seq, "seat": seat,
            "view": deal.view(seat) if deal and seat else None,
            "number": self.game.number, "direction": deal.direction if deal else None,
            "phase": deal.phase if deal else None, "waiting": deal.waiting() if deal else [],
            "trick": {"leader": deal.leader, "cards": list(deal.cards)} if deal else None,
            "taken": list(deal.taken) if deal else [0, 0, 0, 0], "totals": list(self.game.totals),
            "tricks_done": len(deal.history) if deal else 0, "deadline": self.deadline,
            "thoughts": self._trick_thoughts() if self.study else [],
            "finished": self.game.finished,
            "winners": self._winners(),
        }

    def _winners(self):
        if not self.game.finished:
            return []
        low = min(self.game.totals)
        return [i + 1 for i in range(4) if self.game.totals[i] == low]

    def current_advice(self, seat):
        """Advice for the position this seat is in now, if it has been worked out."""
        deal, advice = self.game.deal, self.advice.get(seat)
        if advice and deal and advice["number"] == deal.number and advice["tricks_done"] == len(deal.history):
            return advice
        return None

    def attach(self, send, seat):
        """Register a client and send its snapshot, in one step so no event falls between them."""
        self.connections[send] = seat
        self._send(send, self.snapshot(seat))
        advice = self.current_advice(seat) if self.study and seat else None
        if advice:
            self._send(send, advice)

    def refresh_clients(self, player_id=None):
        """Seats changed: everyone needs the new seats, and someone who just sat down has a seat now."""
        seat = self.seat_of(player_id) if player_id else None
        for send, watcher in list(self.connections.items()):
            if player_id and getattr(send, "player_id", None) == player_id:
                self.connections[send] = seat
                watcher = seat
            self._send(send, self.snapshot(watcher))

    def describe_for_seat(self, seat):
        d = self.describe()
        d["your_seat"] = seat
        return d

    def _trick_thoughts(self):
        deal = self.game.deal
        if not deal or deal.phase != "play":
            return []
        recent = [e for e in deal.events if e["type"] == "card"][-len(deal.cards):] if deal.cards else []
        return [{"seat": e["seat"], "card": e["card"], "thought": e.get("thought")} for e in recent]

    # Moves ----------------------------------------------------------------------------------------------------
    def submit(self, player_id, cards=None, card=None):
        """A person's move, from a socket or the REST API."""
        seat = self.seat_of(player_id)
        if not seat or self.status != "playing":
            raise IllegalMove("You aren't playing at this table.")
        if card is not None:
            self._emit(self.game.submit_play(seat, card))
        else:
            self._emit(self.game.submit_pass(seat, cards))
        self.wake.set()

    def _person_seats(self):
        return [i + 1 for i, s in enumerate(self.seats) if s["kind"] == "person"]

    async def _think(self, bot, method, *args):
        return await asyncio.to_thread(getattr(bot, method), *args)

    async def _advise(self, seat):
        """At a study table, what each adviser would do from this seat."""
        deal, entries = self.game.deal, []
        view = deal.view(seat)
        for kind in ADVISERS:
            if kind not in BOT_KINDS:
                continue
            try:
                answer, thought = await asyncio.to_thread(self.manager.adviser(kind).decide, view)
            except Exception:
                log.exception("adviser %s failed", kind)
                continue
            entries.append({"kind": kind, "label": BOT_KINDS[kind].label, "answer": answer,
                            "thought": thought.as_dict() if thought else None})
        message = {"type": "advice", "seat": seat, "number": deal.number,
                   "tricks_done": len(deal.history), "entries": entries}
        self.advice[seat] = message
        for send, s in list(self.connections.items()):
            if s == seat:
                self._send(send, message)

    async def _wait_for_people(self, done):
        """Until done(): wake for each person's move, and play for anyone whose time runs out."""
        limit = self.config.get("time_limit")
        deal = self.game.deal
        while not done():
            people = [s for s in deal.waiting() if self.seats[s - 1]["kind"] == "person"]
            if self.script:
                self._replay_people(people)
                continue
            if not people:
                return
            self.deadline = time.time() + limit if limit else None
            self._announce_turn()
            if self.study:
                for seat in people:
                    asyncio.create_task(self._advise(seat))
            self.wake.clear()
            try:
                if limit:
                    await asyncio.wait_for(self.wake.wait(), limit)
                else:
                    await self.wake.wait()
            except asyncio.TimeoutError:
                for seat in [s for s in deal.waiting() if self.seats[s - 1]["kind"] == "person"]:
                    await self._time_out(seat)
        self.deadline = None

    def _replay_people(self, people):
        kind, seat, value = self.script.popleft()
        if seat in people:
            self._apply(kind, seat, value, None)

    async def _time_out(self, seat):
        deal = self.game.deal
        view = deal.view(seat)
        stand_in = self.manager.adviser(FALLBACK if FALLBACK in BOT_KINDS else "network")
        answer, _ = await asyncio.to_thread(stand_in.decide, view)
        if view["decision"] == "pass":
            self._emit(self.game.submit_pass(seat, answer))
        else:
            self._emit(self.game.submit_play(seat, answer, {"text": "Time ran out, so the Conservative chose."}))

    def _apply(self, kind, seat, value, thought):
        if kind == "pass":
            self._emit(self.game.submit_pass(seat, value))
        else:
            self._emit(self.game.submit_play(seat, value, thought))

    async def _bot_turn(self, seat):
        deal = self.game.deal
        bot = self.bots[seat]
        view = deal.view(seat)
        bot.thought = None
        forced = len(view["legal"]) == 1 and not getattr(bot, "plays_forced_cards", False)
        card = view["legal"][0] if forced else await self._think(bot, "play", view)
        if self.script and self.script[0][:2] == ("card", seat):
            card = self.script.popleft()[2]
        self._apply("card", seat, card, bot.thought.as_dict() if bot.thought else None)

    async def run(self):
        try:
            self.bots = {i + 1: make_bot(s["kind"], s.get("name"), self.seed + i)
                         for i, s in enumerate(self.seats) if s["kind"] != "person"}
            while not self.game.finished:
                deal = self.game.next_deal()
                self._emit(self._new_game_events())
                for seat, bot in self.bots.items():
                    bot.give_hand(deal.dealt[seat - 1], seat)
                if deal.direction:
                    for seat, bot in self.bots.items():
                        cards = await self._think(bot, "pass_out", deal.view(seat))
                        if self.script and self.script[0][:2] == ("pass", seat):
                            cards = self.script.popleft()[2]
                        self._apply("pass", seat, cards, None)
                    await self._wait_for_people(lambda: deal.phase != "pass")
                    for seat, bot in self.bots.items():
                        bot.pass_in(deal.received[seat - 1])
                else:  # H.Deal sends PassOut on a deal with no pass too, and the Expert picks its strategy there.
                    for seat, bot in self.bots.items():
                        bot.pass_out(deal.view(seat))
                told = 0
                while deal.phase == "play":
                    seat = deal.to_play
                    if seat in self.bots:
                        await self._bot_turn(seat)
                    else:
                        before = (len(deal.history), len(deal.cards))
                        await self._wait_for_people(lambda: (len(deal.history), len(deal.cards)) != before)
                    while told < len(deal.history):
                        for bot in self.bots.values():
                            bot.trick(deal.history[told])
                        told += 1
                for bot in self.bots.values():
                    bot.results(list(self.game.totals))
                self._announce_turn()
            self.status = "finished"
            self.save()
            self._announce_turn()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("table %s stopped", self.id)
            self.caught_up.set()
            self.status = "failed"
            self.save()
            for send in list(self.connections):
                self._send(send, {"type": "error", "message": "This table stopped because of an error."})

    def _new_game_events(self):
        """Events the game has made that haven't been counted yet."""
        return self.game.events[self.seq:]

    def _finish_from_record(self, events):
        """A finished game: replay its moves into the game, for review, with no players."""
        for kind, seat, value in list(self.script):
            deal = self.game.deal
            if deal is None or deal.phase == "done":
                deal = self.game.next_deal()
            if kind == "pass":
                self.game.submit_pass(seat, value)
            else:
                self.game.submit_play(seat, value)
        self.script.clear()
        self.seq = self.persisted

    def rebuild(self, events):
        """Prepare to replay a recorded game: moves come from the record until it runs out."""
        self.persisted = len(events)
        for event in events:
            if event["type"] == "passed":
                self.script.append(("pass", event["seat"], event["cards"]))
            elif event["type"] == "card":
                self.script.append(("card", event["seat"], event["card"]))


class Tables:
    def __init__(self, store):
        self.store = store
        self.tables = {}

    def adviser(self, kind):
        """A new player of this kind, for one decide: each rebuilds its own memory from the view."""
        return make_bot(kind, None, 0)

    def create(self, player, seats, config):
        for kind in seats:
            if kind != "person" and kind not in BOT_KINDS:
                raise IllegalMove(f"There's no player called {kind}.")
        table_seats = [{"kind": "person", "player_id": player["id"], "name": player["name"]}]
        for index, kind in enumerate(seats):
            table_seats.append({"kind": kind} if kind == "person" else {"kind": kind, "name": None})
        for index, seat in enumerate(table_seats):
            if seat["kind"] != "person":
                seat["name"] = _bot_name(table_seats, index)
        table_id = uuid.uuid4().hex[:10]
        table = Table(self, table_id, random.randrange(2 ** 31), config, table_seats)
        self.tables[table_id] = table
        table.save()
        table.maybe_start()
        fill_after = config.get("fill_after")
        if fill_after is not None and table.status == "open":
            async def fill():
                await asyncio.sleep(fill_after)
                if table.status == "open":
                    table.fill_empty_seats()
                    table.refresh_clients()
            table.fill_task = asyncio.create_task(fill())
        return table

    async def restore(self):
        """After a restart: rebuild every unfinished game from its record, before serving anyone."""
        for row in self.store.tables():
            if row["status"] == "failed":
                continue
            table = Table(self, row["id"], row["seed"], row["config"], row["seats"], row["status"])
            self.tables[row["id"]] = table
            if row["status"] == "finished":
                table.rebuild(self.store.events(row["id"]))
                table._finish_from_record(self.store.events(row["id"]))
            elif row["status"] == "playing":
                table.rebuild(self.store.events(row["id"]))
                table.task = asyncio.create_task(table.run())
                await table.caught_up.wait()

    def visible(self, player_id):
        result = []
        for table in self.tables.values():
            mine = table.seat_of(player_id)
            if mine or (table.status == "open" and not table.config.get("invite_only")):
                result.append(table.describe(player_id))
        return result

    async def stop(self):
        for table in self.tables.values():
            for task in (table.task, table.fill_task):
                if task:
                    task.cancel()


NAMES = ["Kant", "Dostoevsky", "Proust", "Eisenhower", "Tolstoy", "Hegel", "Austen", "Woolf"]


def _bot_name(seats, index):
    """Names in the spirit of the 1986 examples, unique at this table."""
    taken = {s.get("name") for s in seats}
    return next(n for n in NAMES if n not in taken)
