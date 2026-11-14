# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Courier door: Medleys sit at the house's tables through two Courier programs on a NetHub.

    HEARTSHOUSE   (19860, version 1)  the house serves it.  A Medley offers players, sits them at a table, leaves.
    HEARTSPLAYERS (19861, version 1)  a Medley with players serves it.  The house tells it what happens at the table
                                      and asks its players for their passes and cards.

Both are defined for Medley in medley/hcourier.lisp, which must stay in step with the numbers and types here.  The
calls carry the same game as the WebSocket door: every event a seat may see, and each request with its legal cards.

The door is also the NetHub the Medleys connect to (`medley --nethub HOST:PORT:MAC`).  It passes no frame from one
machine to another, so a Medley here reaches the house and nothing else.  The house answers only these two programs.
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
import re
import time
import uuid

from . import xns
from .cards import RANK_ORDER, RANKS, SUITS
from .game import IllegalMove
from .players import Player
from .tables import StandIn
from .xns import Closed, CourierError, Writer

log = logging.getLogger("hearts.courier")

HOUSE, PLAYERS, VERSION = 19860, 19861, 1
HOUSE_MAC = bytes.fromhex("100048454152")  # The house's host number: 0#10000.44105.40522# to Medley.
DIRECTIONS = [None, "Left", "Across", "Right"]
# HEARTSPLAYERS procedures
TABLE, DEAL, PASS, RECEIVED, PLAY, CARD, TRICK, SCORES, GAME_OVER = range(9)
# HEARTSHOUSE procedures and errors
OFFER, SIT, NEW_TABLE, LEAVE, TABLES, OPPONENTS = range(6)
NO_SUCH_TABLE, NO_SEATS, NOT_ALLOWED, BAD_REQUEST = range(4)
NOT_NAME = re.compile(r"[^A-Za-z0-9 .,'()\-]")


def put_card(w, card):
    return w.word(SUITS.index(card[0])).word(RANK_ORDER[card[1:]] + 2)


def get_card(r):
    suit, value = r.word(), r.word()
    if suit > 3 or not 2 <= value <= 14:
        raise ValueError("not a card")
    return SUITS[suit] + RANKS[value - 2]


def put_cards(w, cards):
    return w.sequence(cards, put_card)


def refuse(number, message):
    return CourierError("abort", number, Writer().string(message).bytes())


class Link:
    """One Medley on the hub: the players it has offered, and the table they are at."""

    def __init__(self, door, wire):
        self.door, self.wire = door, wire
        self.id = uuid.uuid4().hex[:8]
        self.names = []  # The players offered, in the Medley's order: a seat's index is its place here.
        self.public = False  # True if anyone may choose them as opponents.
        self.table = None
        self.seats = {}  # index -> seat number at self.table
        self.address = None  # Where it connected from.
        self.opened = []  # When it opened each of its recent tables.
        self.scores = [0, 0, 0, 0]  # The deal just ended, until its totals follow.
        self.client = None
        self.jobs = asyncio.Queue()
        self.closed = False
        self.worker = asyncio.create_task(self._work())

    # Calls to the Medley, one at a time and in order: a hand must arrive before the request to play from it.
    async def _call(self, procedure, arguments):
        if self.client is None or self.client.closed:
            self.client = await self.wire.open()
        return await self.client.call(PLAYERS, VERSION, procedure, arguments)

    async def _work(self):
        while True:
            procedure, arguments, answer = await self.jobs.get()
            result = None
            try:
                result = await asyncio.wait_for(self._call(procedure, arguments),
                                                self.door.answer_within if answer else 120)
            except CourierError as e:
                log.warning("Medley %s refused call %s: %s", self.id, procedure, e)
            except (Closed, asyncio.TimeoutError) as e:
                log.info("Medley %s is not answering (%s); its seats go to a stand-in", self.id, e or "timeout")
                if answer and not answer.done():
                    answer.set_result(None)
                self.close()
                return
            if answer and not answer.done():
                answer.set_result(result)

    def tell(self, procedure, arguments=b""):
        if not self.closed:
            self.jobs.put_nowait((procedure, arguments, None))

    async def ask(self, procedure, arguments):
        if self.closed:
            return None
        answer = asyncio.get_running_loop().create_future()
        self.jobs.put_nowait((procedure, arguments, answer))
        return await answer

    # The table
    def attach(self, table):
        """The game is starting: open the Medley's card table and follow the table's events."""
        if self.table is table and self.event in table.watchers:
            return
        self.table = table
        self.seats = {s["index"]: i + 1 for i, s in enumerate(table.seats)
                      if s["kind"] == "medley" and s.get("link") == self.id}
        seats = [self.seats.get(i, 0) for i in range(len(self.names))]
        names = [table.seat_name(i + 1) or "" for i in range(4)]
        self.tell(TABLE, Writer().sequence(names, Writer.string).sequence(seats, Writer.word).bytes())
        table.watchers.append(self.event)

    def event(self, event):
        """What happened at the table, as HEARTSPLAYERS calls.  Each seat is told only what it may see."""
        kind, mine = event["type"], sorted(self.seats.values())
        if kind == "deal":
            totals = self.table.game.totals
            for seat in mine:
                w = Writer().word(seat).word(event["number"]).word(DIRECTIONS.index(event["direction"]))
                put_cards(w, event["hands"][seat - 1]).sequence(totals, Writer.word)
                self.tell(DEAL, w.bytes())
        elif kind == "received":
            for seat in mine:
                self.tell(RECEIVED, put_cards(Writer().word(seat), event["cards"][seat - 1]).bytes())
        elif kind == "card":
            self.tell(CARD, put_card(Writer().word(event["seat"]), event["card"]).bytes())
        elif kind == "trick":
            w = put_cards(Writer().word(event["leader"]), event["cards"])
            self.tell(TRICK, w.word(event["winner"]).word(event["points"]).bytes())
        elif kind == "deal_end":
            self.scores = event["scores"]
        elif kind == "totals":
            w = Writer().sequence(self.scores, Writer.word).sequence(event["totals"], Writer.word)
            self.tell(SCORES, w.bytes())
        elif kind == "game_end":
            self.tell(GAME_OVER, Writer().sequence(event["winners"], Writer.word).bytes())
            self.release()
        elif kind == "stopped":
            self.tell(GAME_OVER, Writer().sequence([], Writer.word).bytes())
            self.release()

    def release(self):
        """The game is over, or this Medley left it: its players are no longer anyone's."""
        table, self.table, self.seats, self.names, self.public = self.table, None, {}, [], False
        if table and self.event in table.watchers:
            table.watchers.remove(self.event)

    def leave(self):
        """Take this Medley's players away from their table: an open table gets its seats back, a game a stand-in."""
        table = self.table or next((t for t in self.door.tables.tables.values() if t.status == "open" and any(
            s["kind"] == "medley" and s.get("link") == self.id for s in t.seats)), None)
        if table and table.status == "open":
            for i, s in enumerate(table.seats):
                if s["kind"] == "medley" and s.get("link") == self.id:
                    table.seats[i] = {"kind": "person"}
            table.save()
            table.refresh_clients()
        elif table:  # A game goes on: the seats stay Medley seats in name, and the stand-in plays them.
            for s in table.seats:
                if s["kind"] == "medley" and s.get("link") == self.id:
                    s["link"] = None
            table.save()
        self.release()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.leave()
        self.door.links.pop(self.id, None)
        while not self.jobs.empty():
            answer = self.jobs.get_nowait()[2]
            if answer and not answer.done():
                answer.set_result(None)
        if self.worker is not asyncio.current_task():
            self.worker.cancel()
        self.wire.close()


class MedleySeat(Player):
    """A seat whose player is on a Medley.  The table's events reach the Medley through its Link; this asks it for the
    seat's passes and cards.  If the Medley has gone, or answers with something it may not play, a stand-in chooses."""

    kind = "medley"
    label = "A player on Medley"
    plays_forced_cards = True  # The Medley's players keep their own hands: they must see every turn.
    remote = True

    def __init__(self, link, loop, name, seat):
        super().__init__(name)
        self.link, self.loop, self.seat = link, loop, seat

    def _ask(self, procedure, arguments, read):
        if self.link.closed or self.seat not in self.link.seats.values():
            return None
        raw = asyncio.run_coroutine_threadsafe(self.link.ask(procedure, arguments), self.loop).result()
        try:
            return read(xns.Reader(raw)) if raw is not None else None
        except ValueError:
            return None

    def _stand_in(self, view, why):
        log.info("seat %s: the stand-in chooses (%s)", self.seat, why)
        stand_in = StandIn(self.name)
        return stand_in.pass_out(view) if view["decision"] == "pass" else stand_in.play(view)

    def pass_out(self, view):
        if not view["direction"]:
            return []
        w = put_cards(Writer().word(self.seat).word(DIRECTIONS.index(view["direction"])), view["hand"])
        cards = self._ask(PASS, w.bytes(), lambda r: r.sequence(get_card))
        if cards and len(set(cards)) == 3 and all(c in view["hand"] for c in cards):
            return cards
        return self._stand_in(view, "no pass from the Medley" if cards is None else f"it passed {cards}")

    def play(self, view):
        trick = view["trick"]
        w = put_cards(Writer().word(self.seat).word(trick["leader"]), trick["cards"])
        put_cards(w, view["legal"]).boolean(view["hearts_broken"]).boolean(view["first_trick"])
        card = self._ask(PLAY, w.bytes(), get_card)
        if card in view["legal"]:
            return card
        return self._stand_in(view, "no card from the Medley" if card is None else f"it played {card}")


class Door:
    """The NetHub the Medleys connect to, and the house's Courier programs on it."""

    MAX_LINKS = 64
    MAX_FROM_ONE_ADDRESS = 8
    TABLES_AN_HOUR = 12  # New tables one Medley may open: each is a game the house plays to its end.

    def __init__(self, tables, offer_key=None, answer_within=None):
        self.tables = tables
        self.offer_key = offer_key if offer_key is not None else os.environ.get("HEARTS_OFFER_KEY", "")
        self.answer_within = answer_within or float(os.environ.get("HEARTS_MEDLEY_ANSWER_WITHIN", "900"))
        self.links = {}
        self.server = None
        self.loop = None
        tables.remote = self

    async def start(self, port, host="0.0.0.0"):
        self.loop = asyncio.get_running_loop()
        self.server = await asyncio.start_server(self._connected, host, port)
        log.info("the Courier door is open on port %s", port)

    @property
    def port(self):
        return self.server.sockets[0].getsockname()[1]

    async def stop(self):
        if self.server:
            self.server.close()
        for link in list(self.links.values()):
            link.close()

    async def _connected(self, reader, writer):
        address = (writer.get_extra_info("peername") or ("?",))[0]
        if len(self.links) >= self.MAX_LINKS or \
                sum(l.address == address for l in self.links.values()) >= self.MAX_FROM_ONE_ADDRESS:
            writer.close()
            return
        link = None

        def handler(program, version, procedure, r):
            return self._serve(link, program, version, procedure, r)

        wire = xns.Wire(reader, writer, HOUSE_MAC, handler)
        link = Link(self, wire)
        link.address = address
        self.links[link.id] = link
        try:
            await wire.run()
        finally:
            link.close()

    # HEARTSHOUSE ----------------------------------------------------------------------------------------------
    def _serve(self, link, program, version, procedure, r):
        if program != HOUSE:
            raise CourierError("reject", 0)
        if version != VERSION:
            raise CourierError("reject", 1)
        try:
            if procedure == OFFER:
                key, names = r.string(), self._names(r)
                if self.offer_key and not hmac.compare_digest(key.encode(), self.offer_key.encode()):
                    raise refuse(NOT_ALLOWED, "That isn't the key for offering players to everyone.")
                link.leave()
                link.names, link.public = names, True
                return b""
            if procedure == SIT:
                table_id, names = r.string(), self._names(r)
                table = self.tables.tables.get(table_id)
                if table is None or table.status != "open":
                    raise refuse(NO_SUCH_TABLE, "There's no table with that name waiting for players.")
                if sum(table.is_open(i + 1) for i in range(4)) < len(names):
                    raise refuse(NO_SEATS, "That table hasn't enough free seats.")
                link.leave()
                link.names = names
                for index, name in enumerate(names):
                    table.seat_medley(link.id, index, name)
                table.maybe_start()
                table.refresh_clients()
                return Writer().string(table.id).bytes()
            if procedure == NEW_TABLE:
                names, kinds = self._names(r), r.sequence(lambda x: x.string(40), 3)
                if len(names) + len(kinds) != 4:
                    raise refuse(BAD_REQUEST, "A table has four seats.")
                now = time.time()
                link.opened = [t for t in link.opened if now - t < 3600]
                if len(link.opened) >= self.TABLES_AN_HOUR:
                    raise refuse(BAD_REQUEST, "This Medley has opened many tables. Try again later.")
                link.opened.append(now)
                link.leave()
                link.names = names
                seats = [{"kind": "medley", "name": name, "link": link.id, "index": i} for i, name in enumerate(names)]
                kinds = self._fill(link, kinds)
                claimed = self.claim([k for k in kinds if k.startswith("medley:")])
                table = self.tables.create_table(seats + [self.tables.seat_for(k, claimed) for k in kinds], {})
                return Writer().string(table.id).bytes()
            if procedure == LEAVE:
                link.leave()
                return b""
            if procedure == TABLES:
                rows = [t for t in self.tables.tables.values() if t.status == "open" and not t.config.get("invite_only")]
                w = Writer().word(min(len(rows), 20))
                for t in rows[:20]:
                    w.string(t.id).sequence([t.seat_name(i + 1) for i in range(4) if not t.is_open(i + 1)], Writer.string)
                    w.word(sum(t.is_open(i + 1) for i in range(4)))
                return w.bytes()
            if procedure == OPPONENTS:
                rows = [("person", "An open seat")] + [(o["kind"], o["label"]) for o in self.tables.opponents()]
                w = Writer().word(len(rows))
                for kind, label in rows:
                    w.string(kind).string(label)
                return w.bytes()
        except IllegalMove as e:
            raise refuse(BAD_REQUEST, str(e))
        raise CourierError("reject", 2)

    def _names(self, r):
        """One to four players' names, with anything but plain letters, digits and spaces taken out."""
        names = [NOT_NAME.sub("", n).strip()[:32] or "Medley player" for n in r.sequence(lambda x: x.string(60), 4)]
        if not names:
            raise refuse(BAD_REQUEST, "Offer one to four players.")
        return names

    def _fill(self, link, kinds):
        """Seats left to the house ("") go to players another Medley offers to everyone, then to Experts."""
        offered = [o["kind"] for o in self.offers() if o["kind"].split(":")[1] != link.id]
        offered = [k for k in offered if k.split(":")[1] == offered[0].split(":")[1]]  # One Medley's.
        return [kind or (offered.pop(0) if offered else "expert") for kind in kinds]

    # What the tables ask of the door ----------------------------------------------------------------------------
    def offers(self):
        """The players any table may take: those offered to everyone by a Medley that isn't in a game."""
        return [{"kind": f"medley:{link.id}:{i}", "label": name}
                for link in self.links.values() if link.public and not self._busy(link)
                for i, name in enumerate(link.names)]

    def _busy(self, link):
        return link.table is not None or any(s["kind"] == "medley" and s.get("link") == link.id
                                             for t in self.tables.tables.values() if t.status in ("open", "playing")
                                             for s in t.seats)

    def claim(self, kinds):
        """Seats for these offered kinds ("medley:LINK:INDEX"), or IllegalMove if any has been taken meanwhile."""
        free = {o["kind"]: o["label"] for o in self.offers()}
        if len(set(kinds)) != len(kinds) or any(k not in free for k in kinds):
            raise IllegalMove("Those Medley players have just been taken. Choose again.")
        if len({k.split(":")[1] for k in kinds}) > 1:
            raise IllegalMove("The Medley players at a table must come from one Medley.")
        return {k: {"kind": "medley", "name": free[k], "link": k.split(":")[1], "index": int(k.split(":")[2])}
                for k in kinds}

    def player(self, table, seat, info):
        """The player for a Medley seat as a game starts: the Medley if it is still there, or a stand-in."""
        link = self.links.get(info.get("link"))
        if link is None or link.closed or (link.table is not None and link.table is not table):
            return StandIn(info.get("name"))
        link.attach(table)
        return MedleySeat(link, self.loop, info.get("name"), seat)
