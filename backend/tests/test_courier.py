# Copyright (c) 2026 Athena Decision Systems SAS.
"""The Courier door, with a stand-in for Medley: a program that speaks the two HEARTS Courier programs over a real
socket, through the same XNS code in the other role.  What Medley itself makes of them is tests/run-courier.sh."""
import asyncio
import os
import tempfile
import threading
import time

import pytest
from fastapi.testclient import TestClient

from hearts import courier, xns
from hearts.courier import HOUSE, PLAYERS, VERSION, get_card, put_card, put_cards
from hearts.web import create_app
from hearts.xns import CourierError, Reader, Writer

from test_web import play_until_end_of_deal, sign_up

MEDLEY_MAC = bytes.fromhex("1000AA000001")


class FakeMedley:
    """A Medley's side: it calls HEARTSHOUSE, and serves HEARTSPLAYERS for players that pass and play their first cards."""

    def __init__(self, port):
        self.port = port
        self.calls = []  # (procedure, arguments read) for each HEARTSPLAYERS call
        self.tables = []  # The table each of those calls was about.
        self.hands = {}  # (table, seat) -> cards
        self.ended = {}  # table -> its winners, once GAME.OVER came
        self.over = asyncio.Event()
        self.winners = None
        self.illegal = False  # Answer PLAY with a card that isn't legal.

    async def connect(self):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        self.wire = xns.Wire(reader, writer, MEDLEY_MAC, self.serve)
        self.wire.peer = courier.HOUSE_MAC
        self.reading = asyncio.create_task(self.wire.run())
        self.house = await self.wire.open()
        return self

    async def call(self, procedure, arguments=b""):
        return await self.house.call(HOUSE, VERSION, procedure, arguments)

    def serve(self, program, version, procedure, r):
        assert (program, version) == (PLAYERS, VERSION)
        table = r.string()
        if procedure != courier.GAME_OVER:
            self.tables.append(table)
        if procedure == courier.TABLE:
            self.calls.append(("table", r.sequence(Reader.string), r.sequence(Reader.word)))
        elif procedure == courier.DEAL:
            seat, number, direction = r.word(), r.word(), r.word()
            self.hands[table, seat] = r.sequence(get_card)
            self.calls.append(("deal", seat, number, direction, list(self.hands[table, seat]), r.sequence(Reader.integer)))
        elif procedure == courier.PASS:
            seat, direction, hand = r.word(), r.word(), r.sequence(get_card)
            self.calls.append(("pass", seat, direction))
            assert sorted(hand) == sorted(self.hands[table, seat])
            return put_cards(Writer(), hand[:3]).bytes()
        elif procedure == courier.RECEIVED:
            self.calls.append(("received", r.word(), r.sequence(get_card)))
        elif procedure == courier.PLAY:
            seat, leader, cards, legal = r.word(), r.word(), r.sequence(get_card), r.sequence(get_card)
            self.calls.append(("play", seat, leader, cards, legal, r.boolean(), r.boolean()))
            return put_card(Writer(), "H2" if self.illegal and "H2" not in legal else legal[0]).bytes()
        elif procedure == courier.CARD:
            self.calls.append(("card", r.word(), get_card(r)))
        elif procedure == courier.TRICK:
            self.calls.append(("trick", r.word(), r.sequence(get_card), r.word(), r.word()))
        elif procedure == courier.SCORES:
            self.calls.append(("scores", r.sequence(Reader.integer), r.sequence(Reader.integer)))
        elif procedure == courier.GAME_OVER:
            self.winners = self.ended[table] = r.sequence(Reader.word)
            self.over.set()
        else:
            raise CourierError("reject", 2)
        return b""

    def close(self):
        self.wire.close()


OFFERED = ["Expert on Medley", "Network on Medley", "Conservative on Medley"]


class Medleys:
    """Fake Medleys on a loop of their own, so that a test can also make blocking web requests."""

    def __init__(self, port):
        self.port = port
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()
        self.all = []

    def do(self, coroutine):
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop).result(30)

    def connect(self):
        medley = self.do(FakeMedley(self.port).connect())
        self.all.append(medley)
        return medley

    def resident(self, tables=1):
        """A Medley that offers three players to everyone, at this many tables at once."""
        medley = self.connect()
        self.offer(medley, tables)
        return medley

    def offer(self, medley, tables=1):
        self.do(medley.call(courier.OFFER, Writer().string("the-key").bytes() + names(*OFFERED).word(tables).bytes()))

    def new_table(self, medley, *kinds):
        return Reader(self.do(medley.call(courier.NEW_TABLE, names("Visitor").bytes() + names(*kinds).bytes()))).string()

    def stop(self):
        for medley in self.all:
            self.loop.call_soon_threadsafe(medley.close)
        time.sleep(0.05)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(5)


EVERY_TABLE = Writer().string("").bytes()  # LEAVE with no table's name: leave them all.


def names(*items):
    return Writer().sequence(list(items), Writer.string)


@pytest.fixture
def house(monkeypatch):
    monkeypatch.setenv("HEARTS_ADMIN_PASSWORD", "secret-for-tests")
    monkeypatch.setenv("HEARTS_NETHUB_PORT", "0")
    monkeypatch.setenv("HEARTS_OFFER_KEY", "the-key")
    with tempfile.TemporaryDirectory() as folder:
        with TestClient(create_app(os.path.join(folder, "hearts.db"))) as client:
            yield client, client.app.state.door


def run(coroutine):
    return asyncio.run(asyncio.wait_for(coroutine, 60))


def table_of(client, table_id):
    return client.app.state.tables.tables[table_id]


def test_courier_values_round_trip():
    w = put_cards(Writer().word(3).boolean(True).string("Kant"), ["C2", "S10", "HA", "DQ"]).word(-26)
    r = Reader(w.bytes())
    assert (r.word(), r.boolean(), r.string()) == (3, True, "Kant")
    assert r.sequence(get_card) == ["C2", "S10", "HA", "DQ"] and r.integer() == -26
    with pytest.raises(ValueError):
        Reader(b"\x00\x09\x00\x02").sequence(get_card)  # A sequence that says 9 and holds less.
    with pytest.raises(ValueError):
        get_card(Reader(b"\x00\x07\x00\x02"))  # Suit 7.


def test_a_medleys_players_play_a_whole_game_at_a_new_table(house):
    client, door = house

    async def play():
        medley = await FakeMedley(door.port).connect()
        table_id = Reader(await medley.call(courier.NEW_TABLE, names("Kant", "Hegel").bytes()
                                            + names("clown", "clown").bytes())).string()
        await medley.over.wait()
        medley.close()
        return medley, table_id

    medley, table_id = run(play())
    table = table_of(client, table_id)
    assert table.status == "finished" and [s["kind"] for s in table.seats] == ["medley", "medley", "clown", "clown"]
    kinds = [c[0] for c in medley.calls]
    assert medley.calls[0] == ("table", [table.seat_name(i + 1) for i in range(4)], [1, 2])
    deals = table.game.number
    assert kinds.count("deal") == 2 * deals and kinds.count("scores") == deals
    assert kinds.count("card") == 52 * deals and kinds.count("trick") == 13 * deals
    assert kinds.count("play") == 26 * deals  # Every card of both seats, forced or not.
    assert all(c[4] and (c[3] or c[4]) for c in medley.calls if c[0] == "play")
    assert medley.calls[-1][2] == table.game.totals and medley.winners == table._winners()
    # A deal's calls come in the game's order: the hand, the pass, the cards received, and only then a card to play.
    first = kinds[1:kinds.index("trick")]
    assert first.index("deal") < first.index("pass") < first.index("received") < first.index("play")
    # Each seat was dealt only its own hand, and was told every card as it was played.
    events = client.app.state.store.events(table_id)
    dealt = next(e for e in events if e["type"] == "deal")["hands"]
    assert [c[4] for c in medley.calls if c[0] == "deal"][:2] == dealt[:2]
    assert [(c[1], c[2]) for c in medley.calls if c[0] == "card"] == [(e["seat"], e["card"]) for e in events if e["type"] == "card"]


def test_refusals_are_declared_errors(house):
    client, door = house

    async def ask():
        medley = await FakeMedley(door.port).connect()
        results = []
        for procedure, arguments in [
            (courier.SIT, Writer().string("no-such-table").bytes() + names("Kant").word(1).bytes()),
            (courier.OFFER, Writer().string("wrong").bytes() + names("Kant").word(1).bytes()),
            (courier.NEW_TABLE, names("A", "B").bytes() + names("clown", "clown", "clown").bytes()),
            (courier.NEW_TABLE, names("A").bytes() + names("clown", "clown", "nobody").bytes()),
        ]:
            with pytest.raises(CourierError) as e:
                await medley.call(procedure, arguments)
            results.append((e.value.kind, e.value.number, Reader(e.value.body).string()))
        with pytest.raises(CourierError) as e:
            await medley.house.call(4242, 1, 0)
        results.append((e.value.kind, e.value.number))
        with pytest.raises(CourierError) as e:
            await medley.call(courier.SIT, b"\x00\x05ab")  # Not the procedure's arguments.
        results.append((e.value.kind, e.value.number))
        opponents = Reader(await medley.call(courier.OPPONENTS)).sequence(lambda r: (r.string(), r.string()))
        medley.close()
        return results, opponents

    results, opponents = run(ask())
    assert [r[:2] for r in results[:4]] == [("abort", courier.NO_SUCH_TABLE), ("abort", courier.NOT_ALLOWED),
                                            ("abort", courier.BAD_REQUEST), ("abort", courier.BAD_REQUEST)]
    assert all(r[2] for r in results[:4])
    assert results[4:] == [("reject", 0), ("reject", 3)]
    assert ("person", "An open seat") in opponents and "expert" in dict(opponents)
    assert not client.app.state.tables.tables  # Nothing was created by the refused calls.


def test_one_medley_cannot_open_tables_without_end(house):
    client, door = house
    door.TABLES_AN_HOUR = 2

    async def open_three():
        medley = await FakeMedley(door.port).connect()
        arguments = names("Kant").bytes() + names("person", "person", "person").bytes()
        first = Reader(await medley.call(courier.NEW_TABLE, arguments)).string()
        second = Reader(await medley.call(courier.NEW_TABLE, arguments)).string()
        with pytest.raises(CourierError) as e:
            await medley.call(courier.NEW_TABLE, arguments)
        # Opening the second table took its player away from the first, whose seat is free again.
        seats = table_of(client, first).is_open(1), table_of(client, second).is_open(1)
        medley.close()
        return seats, Reader(e.value.body).string()

    seats, refusal = run(open_three())
    assert "later" in refusal and len(client.app.state.tables.tables) == 2
    assert seats == (True, False)


def test_players_offered_to_everyone_are_chosen_from_the_web(house):
    client, door = house
    headers, token = sign_up(client)
    ready, played, finished = threading.Event(), threading.Event(), threading.Event()
    seen = {}

    async def offer():
        medley = await FakeMedley(door.port).connect()
        await medley.call(courier.OFFER, Writer().string("the-key").bytes() + names("Expert on Medley", "Network on Medley",
                                                                                 "Conservative on Medley").word(1).bytes())
        ready.set()
        await medley.over.wait()
        seen["first"] = list(medley.calls)
        played.set()
        await medley.call(courier.OFFER, Writer().string("the-key").bytes() + names("Fresh one").word(1).bytes())
        ready.set()
        await asyncio.to_thread(finished.wait, 30)
        medley.close()

    thread = threading.Thread(target=lambda: asyncio.run(offer()), daemon=True)
    thread.start()
    assert ready.wait(20)
    ready.clear()
    offered = [o for o in client.get("/api/opponents", headers=headers).json()["opponents"] if o["kind"].startswith("medley:")]
    assert [o["label"] for o in offered] == ["Expert on Medley", "Network on Medley", "Conservative on Medley"]
    table = client.post("/api/tables", json={"seats": [o["kind"] for o in offered], "over_score": 1}, headers=headers).json()
    assert [s["kind"] for s in table["seats"]] == ["person", "medley", "medley", "medley"]
    assert [s["name"] for s in table["seats"]][1:] == [o["label"] for o in offered]
    # While they play, nobody else can take them.
    assert not [o for o in client.get("/api/opponents", headers=headers).json()["opponents"] if o["kind"].startswith("medley:")]
    again = client.post("/api/tables", json={"seats": [o["kind"] for o in offered]}, headers=headers)
    assert again.status_code == 400 and "taken" in again.json()["detail"]
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        while not table_of(client, table["id"]).game.finished:
            play_until_end_of_deal(socket, 1)
    assert played.wait(20)
    assert seen["first"][0] == ("table", ["Ana", "Expert on Medley", "Network on Medley", "Conservative on Medley"], [2, 3, 4])
    # After the game the Medley offers again, and its new players are on the list.
    assert ready.wait(20)
    offered = [o["label"] for o in client.get("/api/opponents", headers=headers).json()["opponents"] if o["kind"].startswith("medley:")]
    assert offered == ["Fresh one"]
    finished.set()
    thread.join(20)


def test_a_stand_in_plays_for_a_medley_that_plays_a_card_it_may_not_and_a_game_left_empty_ends(house):
    client, door = house

    async def play():
        cheat = await FakeMedley(door.port).connect()
        cheat.illegal = True
        cheating = Reader(await cheat.call(courier.NEW_TABLE, names("Cheat").bytes() + names("clown", "clown", "clown").bytes())).string()
        gone = await FakeMedley(door.port).connect()
        leaving = Reader(await gone.call(courier.NEW_TABLE, names("Gone").bytes() + names("clown", "clown", "clown").bytes())).string()
        while not any(c[0] == "trick" for c in gone.calls):
            await asyncio.sleep(0.01)
        gone.close()
        await cheat.over.wait()
        cheat.close()
        return cheating, leaving

    cheating, leaving = run(play())
    # The cheat's game was played to its end.  The other had nobody left at it, so it ended there (test_presence).
    assert table_of(client, cheating).status == "finished" and table_of(client, leaving).status == "abandoned"
    assert not door.links


def test_a_medley_sits_at_a_table_someone_opened_and_can_leave_it(house):
    client, door = house
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["person", "person", "clown"], "over_score": 1}, headers=headers).json()
    assert table["status"] == "open"

    async def sit():
        medley = await FakeMedley(door.port).connect()
        listed = Reader(await medley.call(courier.TABLES)).sequence(lambda r: (r.string(), r.sequence(Reader.string), r.word()))
        assert listed == [(table["id"], ["Ana", table["seats"][3]["name"]], 2)]
        await medley.call(courier.SIT, Writer().string(table["id"]).bytes() + names("Kant").bytes())
        assert not table_of(client, table["id"]).is_open(2)
        await medley.call(courier.LEAVE, EVERY_TABLE)
        assert table_of(client, table["id"]).status == "open" and table_of(client, table["id"]).is_open(2)
        with pytest.raises(CourierError):  # Three players for two seats.
            await medley.call(courier.SIT, Writer().string(table["id"]).bytes() + names("A", "B", "C").bytes())
        await medley.call(courier.SIT, Writer().string(table["id"]).bytes() + names("Kant", "Hegel").bytes())
        return medley

    async def session():
        medley = await sit()
        await medley.over.wait()
        medley.close()

    thread = threading.Thread(target=lambda: asyncio.run(asyncio.wait_for(session(), 60)), daemon=True)
    thread.start()
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        m = socket.receive_json()
        while not (m["type"] == "snapshot" and m["table"]["status"] == "playing"):
            m = socket.receive_json()
        assert m["table"]["seats"][1] == {"kind": "medley", "name": "Kant", "open": False, "stand_in": False}
        while not table_of(client, table["id"]).game.finished:
            play_until_end_of_deal(socket, 1)
    thread.join(30)
    assert table_of(client, table["id"]).status == "finished"


def test_a_game_with_medley_seats_survives_a_restart_with_stand_ins(monkeypatch):
    monkeypatch.setenv("HEARTS_ADMIN_PASSWORD", "secret-for-tests")
    monkeypatch.setenv("HEARTS_NETHUB_PORT", "0")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "hearts.db")
        with TestClient(create_app(path)) as client:
            headers, token = sign_up(client)
            made = client.post("/api/tables", json={"seats": ["person", "clown", "clown"]}, headers=headers).json()
            medleys = Medleys(client.app.state.door.port)
            medley = medleys.connect()
            medleys.do(medley.call(courier.SIT, Writer().string(made["id"]).bytes() + names("Kant").bytes()))
            with client.websocket_connect(f"/api/tables/{made['id']}/ws?token={token}") as socket:
                play_until_end_of_deal(socket, 1)  # One deal cannot end a game to 100.
            assert [c for c in medley.calls if c[0] == "play"]
            before = len(client.app.state.store.events(made["id"]))
            medleys.stop()
        with TestClient(create_app(path)) as client:
            table = table_of(client, made["id"])  # A person can come back to it, so it was kept.
            assert table.status == "playing" and table.describe()["seats"][1]["stand_in"]
            with client.websocket_connect(f"/api/tables/{made['id']}/ws?token={token}") as socket:
                while not table.game.finished:
                    play_until_end_of_deal(socket, 1)
            events = client.app.state.store.events(made["id"])
            assert len(events) > before and events[-1]["type"] == "game_end"


def test_a_game_whose_only_people_were_on_a_medley_is_not_brought_back_by_a_restart(monkeypatch):
    monkeypatch.setenv("HEARTS_NETHUB_PORT", "0")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "hearts.db")
        with TestClient(create_app(path)) as client:
            medleys = Medleys(client.app.state.door.port)
            medley = medleys.connect()
            table_id = medleys.new_table(medley, "clown", "clown", "clown")
            for _ in range(1000):
                if any(c[0] == "trick" for c in medley.calls):
                    break
                time.sleep(0.01)
            medleys.stop()
        with TestClient(create_app(path)) as client:  # It ended as the Medley went.  Put it back as a crash leaves it.
            store = client.app.state.store
            row = next(r for r in store.tables() if r["id"] == table_id)
            assert row["status"] == "abandoned"
            store.save_table(table_id, row["seed"], row["config"], row["seats"], "playing")
        with TestClient(create_app(path)) as client:
            assert table_of(client, table_id).status == "abandoned"
            assert not table_of(client, table_id).game.finished


def test_the_hub_passes_nothing_between_machines_and_survives_rubbish(house):
    client, door = house

    async def intrude():
        victim = await FakeMedley(door.port).connect()
        heard = []
        frame = victim.wire.frame
        victim.wire.frame = lambda f: (heard.append(bytes(f)), frame(f))[1]
        heard_before = len(heard)
        reader, writer = await asyncio.open_connection("127.0.0.1", door.port)

        def send(frame):
            writer.write(len(frame).to_bytes(2, "big") + frame)

        idp = b"\xff\xff" + (30).to_bytes(2, "big") + b"\x00\x05" + bytes(4) + MEDLEY_MAC + b"\x00\x05" \
            + bytes(4) + bytes.fromhex("1000AA000099") + b"\x0b\xb8"
        send(MEDLEY_MAC + bytes.fromhex("1000AA000099") + xns.XNS + idp)          # To the other machine.
        send(xns.BROADCAST + bytes.fromhex("1000AA000099") + xns.XNS + idp)       # To everyone.
        send(courier.HOUSE_MAC + bytes.fromhex("1000AA000099") + b"\x08\x00" + bytes(40))   # Not XNS.
        send(courier.HOUSE_MAC + bytes.fromhex("1000AA000099") + xns.XNS + b"\x00" * 7)     # Too short.
        send(courier.HOUSE_MAC + bytes.fromhex("1000AA000099") + xns.XNS + b"\xff\xff\xff\xff" + bytes(40))  # A false length.
        # A connection request, then a Courier call that is nothing like one.
        spp = b"\xc0\x00" + (7).to_bytes(2, "big") + bytes(8)
        head = b"\xff\xff" + (42).to_bytes(2, "big") + b"\x00\x05" + bytes(4) + courier.HOUSE_MAC + b"\x00\x05" \
            + bytes(4) + bytes.fromhex("1000AA000099") + b"\x0b\xb8"
        send(courier.HOUSE_MAC + bytes.fromhex("1000AA000099") + xns.XNS + head + spp)
        await writer.drain()
        await asyncio.sleep(0.2)
        writer.write(b"\xff\xff" + bytes(100))                                       # A length no frame has.
        await writer.drain()
        await asyncio.sleep(0.2)
        closed = (await reader.read()) is not None and reader.at_eof()
        # The house still serves the machine that behaved.
        opponents = Reader(await victim.call(courier.OPPONENTS)).sequence(lambda r: (r.string(), r.string()))
        delivered = [f for f in heard[heard_before:] if f[6:12] != courier.HOUSE_MAC]
        victim.close()
        return closed, opponents, delivered

    closed, opponents, delivered = run(intrude())
    assert closed and "expert" in dict(opponents)
    assert delivered == []  # Every frame the machine got came from the house.


def test_a_routing_question_is_answered_so_medley_does_not_wait_for_a_router(house):
    client, door = house

    async def ask():
        reader, writer = await asyncio.open_connection("127.0.0.1", door.port)
        me = bytes.fromhex("1000AA000055")
        request = b"\x00\x01" + b"\xff\xff\xff\xff" + b"\x00\x10"   # What networks are there?
        idp = b"\xff\xff" + (30 + len(request)).to_bytes(2, "big") + b"\x00\x01" + bytes(4) + xns.BROADCAST + b"\x00\x01" \
            + bytes(4) + me + b"\x00\x01" + request
        frame = xns.BROADCAST + me + xns.XNS + idp
        writer.write(len(frame).to_bytes(2, "big") + frame)
        size = int.from_bytes(await asyncio.wait_for(reader.readexactly(2), 5), "big")
        answer = await reader.readexactly(size)
        writer.close()
        return answer

    answer = run(ask())
    packet = answer[14:]
    assert answer[0:6] == bytes.fromhex("1000AA000055") and answer[6:12] == courier.HOUSE_MAC and len(answer) % 2 == 0
    assert packet[5] == 1 and int.from_bytes(packet[2:4], "big") == 38
    assert packet[30:38] == b"\x00\x02" + bytes(4) + b"\x00\x00"   # A response: network 0, no hops.
