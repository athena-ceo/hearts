# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Courier door: Medleys sit at the house's tables through two Courier programs on a NetHub.

    HEARTSHOUSE   (19860, version 2)  the house serves it.  A Medley offers players, sits them at a table, leaves.
    HEARTSPLAYERS (19861, version 2)  a Medley with players serves it.  The house tells it what happens at each
                                      table, by the table's name, and asks its players for their passes and cards.

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

HOUSE, PLAYERS, VERSION = 19860, 19861, 2
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
    """One Medley on the hub: the players it has put forward, and the tables they are at.  A Medley that offers
    players to everyone says how many tables it will take at once, and makes a fresh set for each."""

    def __init__(self, door, wire):
        self.door, self.wire = door, wire
        self.id = uuid.uuid4().hex[:8]
        self.names = []  # The players put forward, in the Medley's order: a seat's index is its place here.
        self.public = False  # True if anyone may choose them as opponents.
        self.capacity = 1  # How many tables they can be at.
        self.games = {}  # table id -> {"table", "seats": index -> seat number, "scores", "watch"}
        self.address = None  # Where it connected from.
        self.opened = []  # When it opened each of its recent tables.
        self.client = None
        self.jobs = asyncio.Queue()
        self.asked = None  # The answer the Medley is being waited on for now.
        self.closed = False
        self.worker = asyncio.create_task(self._work())

    # Calls to the Medley, one at a time and in order: a hand must arrive before the request to play from it, and
    # the 1986 Expert's rules have one working memory, so only one of a Medley's players thinks at a time.
    async def _call(self, procedure, arguments):
        if self.client is None or self.client.closed:
            self.client = await self.wire.open()
        return await self.client.call(PLAYERS, VERSION, procedure, arguments)

    async def _work(self):
        while True:
            procedure, arguments, answer = await self.jobs.get()
            result, self.asked = None, answer
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

    def tell(self, procedure, table, arguments=None):
        """A HEARTSPLAYERS call that returns nothing.  Every call names its table first."""
        if not self.closed:
            w = Writer().string(table.id)
            self.jobs.put_nowait((procedure, w.bytes() + (arguments.bytes() if arguments else b""), None))

    async def ask(self, procedure, table, arguments):
        if self.closed:
            return None
        answer = asyncio.get_running_loop().create_future()
        self.jobs.put_nowait((procedure, Writer().string(table.id).bytes() + arguments.bytes(), answer))
        return await answer

    # The tables
    def plays(self, table, seat):
        """Is this seat at this table one the Medley is playing now?"""
        game = self.games.get(table.id)
        return bool(game and not self.closed and seat in game["seats"].values())

    def attach(self, table):
        """The game is starting: tell the Medley its seats, and follow the table's events."""
        if table.id in self.games:
            return
        seats = {s["index"]: i + 1 for i, s in enumerate(table.seats)
                 if s["kind"] == "medley" and s.get("link") == self.id}
        game = self.games[table.id] = {"table": table, "seats": seats, "scores": [0, 0, 0, 0],
                                       "watch": lambda event: self.event(table, event)}
        names = [table.seat_name(i + 1) or "" for i in range(4)]
        self.tell(TABLE, table, Writer().sequence(names, Writer.string)
                  .sequence([seats.get(i, 0) for i in range(len(self.names))], Writer.word))
        table.watchers.append(game["watch"])

    def event(self, table, event):
        """What happened at the table, as HEARTSPLAYERS calls.  Each seat is told only what it may see."""
        game = self.games.get(table.id)
        if game is None:
            return
        kind, mine = event["type"], sorted(game["seats"].values())
        if kind == "deal":
            for seat in mine:
                w = Writer().word(seat).word(event["number"]).word(DIRECTIONS.index(event["direction"]))
                self.tell(DEAL, table, put_cards(w, event["hands"][seat - 1]).sequence(table.game.totals, Writer.word))
        elif kind == "received":
            for seat in mine:
                self.tell(RECEIVED, table, put_cards(Writer().word(seat), event["cards"][seat - 1]))
        elif kind == "card":
            self.tell(CARD, table, put_card(Writer().word(event["seat"]), event["card"]))
        elif kind == "trick":
            w = put_cards(Writer().word(event["leader"]), event["cards"])
            self.tell(TRICK, table, w.word(event["winner"]).word(event["points"]))
        elif kind == "deal_end":
            game["scores"] = event["scores"]
        elif kind == "totals":
            self.tell(SCORES, table, Writer().sequence(game["scores"], Writer.word).sequence(event["totals"], Writer.word))
        elif kind == "game_end":
            self.tell(GAME_OVER, table, Writer().sequence(event["winners"], Writer.word))
            self.release(table)
        elif kind == "stopped":
            self.tell(GAME_OVER, table, Writer().sequence([], Writer.word))
            self.release(table)

    def release(self, table):
        """This table's game is over, or this Medley left it.  Players offered to everyone stay on offer: the Medley
        makes new ones for the next table.  Players a Medley sat itself are nobody's until it sits them again."""
        game = self.games.pop(table.id, None)
        if game and game["watch"] in table.watchers:
            table.watchers.remove(game["watch"])
        if not self.public and not self.games:
            self.names = []

    def _tables(self):
        """Every table with this Medley's players in its seats, waiting or playing."""
        return [t for t in self.door.tables.tables.values() if t.status in ("open", "playing") and any(
            s["kind"] == "medley" and s.get("link") == self.id for s in t.seats)]

    def leave(self, table=None):
        """Take this Medley's players away from a table, or from all of them: a table still waiting gets its seats
        back, a game a stand-in.  If that leaves nobody at the table, the table sees to it."""
        for t in [table] if table else self._tables():
            mine = [i for i, s in enumerate(t.seats) if s["kind"] == "medley" and s.get("link") == self.id
                    and t.status in ("open", "playing")]
            for i in mine:
                if t.status == "open":
                    t.seats[i] = {"kind": "person"}
                else:  # The seats stay Medley seats in name, and the stand-in plays them.
                    t.seats[i]["link"] = None
            if mine:
                t.save()
            self.release(t)
            if mine:
                t.refresh_clients()
                t.unattended()
        if table is None:
            for game in list(self.games.values()):
                self.release(game["table"])

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.leave()
        self.door.links.pop(self.id, None)
        waiting = [self.asked]  # A seat waiting for this Medley's answer gets none: its stand-in plays.
        while not self.jobs.empty():
            waiting.append(self.jobs.get_nowait()[2])
        for answer in waiting:
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

    def __init__(self, link, loop, name, seat, table):
        super().__init__(name)
        self.link, self.loop, self.seat, self.table = link, loop, seat, table

    def _ask(self, procedure, arguments, read):
        # The Medley may have left this game and be in others, where it can hold a seat with the same number.
        if not self.link.plays(self.table, self.seat):
            return None
        raw = asyncio.run_coroutine_threadsafe(self.link.ask(procedure, self.table, arguments), self.loop).result()
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
        cards = self._ask(PASS, w, lambda r: r.sequence(get_card))
        if cards and len(set(cards)) == 3 and all(c in view["hand"] for c in cards):
            return cards
        return self._stand_in(view, "no pass from the Medley" if cards is None else f"it passed {cards}")

    def play(self, view):
        trick = view["trick"]
        w = put_cards(Writer().word(self.seat).word(trick["leader"]), trick["cards"])
        put_cards(w, view["legal"]).boolean(view["hearts_broken"]).boolean(view["first_trick"])
        card = self._ask(PLAY, w, get_card)
        if card in view["legal"]:
            return card
        return self._stand_in(view, "no card from the Medley" if card is None else f"it played {card}")


class Door:
    """The NetHub the Medleys connect to, and the house's Courier programs on it."""

    MAX_LINKS = 64
    MAX_FROM_ONE_ADDRESS = 8
    TABLES_AN_HOUR = 12  # New tables one Medley may open: each is a game the house plays while it stays.
    MAX_TABLES = 16  # The most tables one Medley's offered players may be at, whatever it says it will take.

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
                key, names, tables = r.string(), self._names(r), r.word()
                if self.offer_key and not hmac.compare_digest(key.encode(), self.offer_key.encode()):
                    raise refuse(NOT_ALLOWED, "That isn't the key for offering players to everyone.")
                link.leave()
                link.names, link.public, link.capacity = names, True, max(1, min(tables, self.MAX_TABLES))
                return b""
            if procedure == SIT:
                table_id, names = r.string(), self._names(r)
                table = self.tables.tables.get(table_id)
                if table is None or table.status != "open":
                    raise refuse(NO_SUCH_TABLE, "There's no table with that name waiting for players.")
                if sum(table.is_open(i + 1) for i in range(4)) < len(names):
                    raise refuse(NO_SEATS, "That table hasn't enough free seats.")
                self._visits(link, names)
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
                self._visits(link, names)
                seats = [{"kind": "medley", "name": name, "link": link.id, "index": i} for i, name in enumerate(names)]
                kinds = self._fill(link, kinds)
                claimed = self.claim([k for k in kinds if k.startswith("medley:")])
                table = self.tables.create_table(seats + [self.tables.seat_for(k, claimed) for k in kinds], {})
                return Writer().string(table.id).bytes()
            if procedure == LEAVE:  # One table, or with no name every table.
                table_id = r.string()
                table = self.tables.tables.get(table_id)
                if table_id and table is None:
                    raise refuse(NO_SUCH_TABLE, "There's no table with that name.")
                link.leave(table)
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

    def _visits(self, link, names):
        """This Medley is sitting its own players at one table: they leave wherever they were."""
        link.leave()
        link.names, link.public, link.capacity = names, False, 1

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
        """The players any table may take: those offered to everyone by a Medley that has room for another table."""
        return [{"kind": f"medley:{link.id}:{i}", "label": name}
                for link in self.links.values() if link.public and not self._busy(link)
                for i, name in enumerate(link.names)]

    def _busy(self, link):
        return len(link._tables()) >= link.capacity

    def holds(self, table, seat):
        """Is this Medley seat still played by its Medley?"""
        link = self.links.get(seat.get("link"))  # A Medley that leaves a game takes its name off the seat.
        return bool(link and not link.closed)

    def _at(self, table, public):
        """The Medleys with players in this table's seats: those that offered them to everyone, or the others."""
        ids = {s.get("link") for s in table.seats if s["kind"] == "medley"}
        return [link for link in self.links.values() if link.id in ids and link.public == public and not link.closed]

    def visiting(self, table):
        """Is a Medley that sat its own players at this table still there?  Its owner chose this table, at a screen
        or not; a Medley whose players were offered to everyone is nobody's presence."""
        return bool(self._at(table, False))

    def vacate(self, table):
        """Nobody is at this table: send home the players a Medley offered to everyone.  True if any went.  From a
        game, the Medley is told it is over.  From a table still waiting for players, the Medley was told nothing
        yet, and its seats are open again.  Either way the Medley has room for another table."""
        gone = self._at(table, True)
        for link in gone:
            log.info("table %s: nobody is here, so Medley %s has its players back", table.id, link.id)
            if table.status == "playing":
                link.tell(GAME_OVER, table, Writer().sequence([], Writer.word))
            link.leave(table)
        return bool(gone)

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
        if link is None or link.closed:
            return StandIn(info.get("name"))
        link.attach(table)
        return MedleySeat(link, self.loop, info.get("name"), seat, table)
