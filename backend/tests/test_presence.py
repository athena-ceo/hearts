# Copyright (c) 2026 Athena Decision Systems SAS.
"""Who is at a table.  The players a Medley offers to everyone are held only while someone is there: a person with
the table open in a browser, or a Medley that sat its own players.  When nobody is, they go home and are offered
again.  The game is kept if a person can come back to it, and ends if no one can.

The cases are a matrix: who the people were, how they went, what else was at the table, and when."""
import asyncio
import os
import tempfile
import threading
import time

import pytest
from fastapi.testclient import TestClient

from hearts import courier
from hearts.web import create_app
from hearts.xns import Reader, Writer

from test_courier import EVERY_TABLE, OFFERED, Medleys, names, table_of
from test_web import play_until_end_of_deal, sign_up

HOLD = 0.4  # Seconds a game keeps a Medley's players after the last browser closed it, in these tests.


@pytest.fixture
def house(monkeypatch):
    monkeypatch.setenv("HEARTS_ADMIN_PASSWORD", "secret-for-tests")
    monkeypatch.setenv("HEARTS_NETHUB_PORT", "0")
    monkeypatch.setenv("HEARTS_OFFER_KEY", "the-key")
    monkeypatch.setenv("HEARTS_MEDLEY_HOLD", str(HOLD))
    with tempfile.TemporaryDirectory() as folder:
        with TestClient(create_app(os.path.join(folder, "hearts.db"))) as client:
            medleys = Medleys(client.app.state.door.port)
            try:
                yield client, medleys
            finally:
                medleys.stop()


def until(what, within=10.0):
    end = time.time() + within
    while time.time() < end:
        if what():
            return True
        time.sleep(0.01)
    return False


def offered_now(client):
    return [o["label"] for o in client.app.state.tables.opponents() if o["kind"].startswith("medley:")]


def offered_kinds(client):
    return [o["kind"] for o in client.app.state.tables.opponents() if o["kind"].startswith("medley:")]


def sent_home(client, medleys, resident):
    """The resident was told its game is over, with no winner, and its players are on offer again without its
    having to do anything."""
    assert until(resident.over.is_set), "the resident's players were not sent home"
    assert resident.winners == []
    return until(lambda: offered_now(client) == OFFERED)


def stood_in(table):
    return [s["stand_in"] for s in table.describe()["seats"]]


# A Medley that sat its own players is the only one there, and goes -------------------------------------------------
@pytest.mark.parametrize("when", ["as the game starts", "after a trick"])
@pytest.mark.parametrize("how", ["leaves", "loses its connection"])
@pytest.mark.parametrize("others", ["the house's players", "the resident's players"])
def test_a_game_ends_when_the_medley_that_was_its_only_person_goes(house, others, how, when):
    client, medleys = house
    resident = medleys.resident() if others == "the resident's players" else None
    visitor = medleys.connect()
    table = table_of(client, medleys.new_table(visitor, *(["", "", ""] if resident else ["clown", "clown", "clown"])))
    if resident:
        assert [s["kind"] for s in table.seats] == ["medley"] * 4 and offered_now(client) == []
    assert until(lambda: any(c[0] == ("trick" if when == "after a trick" else "deal") for c in visitor.calls))
    if how == "leaves":
        medleys.do(visitor.call(courier.LEAVE, EVERY_TABLE))
    else:
        medleys.loop.call_soon_threadsafe(visitor.close)
    assert until(lambda: table.status == "abandoned"), table.status
    events = len(client.app.state.store.events(table.id))
    if resident:
        assert sent_home(client, medleys, resident)
    time.sleep(0.2)
    assert len(client.app.state.store.events(table.id)) == events  # Nothing more is played.
    assert not table.game.finished


# A person in a browser has gone -------------------------------------------------------------------------------------
@pytest.mark.parametrize("when", ["never opened the table", "closed it after a deal"])
@pytest.mark.parametrize("timer", [None, 10])
def test_the_residents_players_go_home_when_the_person_has_gone_and_the_game_is_kept(house, timer, when):
    client, medleys = house
    resident = medleys.resident()
    headers, token = sign_up(client)
    made = client.post("/api/tables", json={"seats": offered_kinds(client), "over_score": 30, "time_limit": timer},
                       headers=headers).json()
    table = table_of(client, made["id"])
    if when == "closed it after a deal":
        with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
            play_until_end_of_deal(socket, 1)
            time.sleep(HOLD + 0.3)  # However long the table is open, nothing changes.
            assert not resident.over.is_set() and stood_in(table) == [False] * 4
    assert sent_home(client, medleys, resident)
    assert table.status == "playing" and stood_in(table) == [False, True, True, True]
    # The person comes back, is told who they are playing, and finishes the game against the stand-ins.
    calls = len(resident.calls)
    with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
        snapshot = socket.receive_json()
        assert [s["stand_in"] for s in snapshot["table"]["seats"]] == [False, True, True, True]
    with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
        while not table.game.finished:
            play_until_end_of_deal(socket, 1)
    assert until(lambda: table.status == "finished")
    assert len(resident.calls) == calls  # The resident hears no more of this game.
    assert offered_now(client) == OFFERED  # And it was free all the while.


# Someone is there: nothing is taken away -----------------------------------------------------------------------------
def test_a_reload_inside_the_wait_changes_nothing(house):
    client, medleys = house
    resident = medleys.resident()
    headers, token = sign_up(client)
    made = client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=headers).json()
    table = table_of(client, made["id"])
    for _ in range(4):  # Closed for less than the wait, four times over: longer than the wait in all.
        with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
            socket.receive_json()
        time.sleep(HOLD / 2)
    with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
        socket.receive_json()
        time.sleep(HOLD + 0.3)
        assert not resident.over.is_set() and stood_in(table) == [False] * 4
        assert offered_now(client) == []


def test_someone_who_only_watches_does_not_hold_the_players(house):
    client, medleys = house
    resident = medleys.resident()
    headers, _ = sign_up(client)
    _, watcher = sign_up(client, "Bea")
    made = client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=headers).json()
    with client.websocket_connect(f"/api/tables/{made['id']}/ws?token={watcher}") as socket:
        assert socket.receive_json()["seat"] is None
        assert sent_home(client, medleys, resident)
        m = socket.receive_json()  # The watcher is shown that stand-ins have the seats.
        while not (m["type"] == "snapshot" and m["table"]["seats"][1]["stand_in"]):
            m = socket.receive_json()


def test_a_person_who_moves_without_a_live_connection_counts_as_there(house):
    client, medleys = house
    resident = medleys.resident()
    headers, _ = sign_up(client)
    made = client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=headers).json()
    table = table_of(client, made["id"])
    time.sleep(HOLD * 0.7)
    hand = table.game.deal.view(1)["hand"]
    assert client.post(f"/api/tables/{table.id}/move", json={"cards": hand[:3]}, headers=headers).status_code == 200
    time.sleep(HOLD * 0.7)
    assert not resident.over.is_set()
    assert sent_home(client, medleys, resident)


@pytest.mark.parametrize("how", ["leaves", "loses its connection"])
def test_a_visiting_medley_keeps_the_table_while_the_person_is_away_and_frees_it_when_it_goes(house, how):
    client, medleys = house
    resident = medleys.resident()
    headers, token = sign_up(client)
    kinds = offered_kinds(client)
    made = client.post("/api/tables", json={"seats": ["person"] + kinds[:2]}, headers=headers).json()
    table = table_of(client, made["id"])
    visitor = medleys.connect()
    medleys.do(visitor.call(courier.SIT, Writer().string(table.id).bytes() + names("Visitor").bytes()))
    assert until(lambda: table.status == "playing")
    time.sleep(HOLD + 0.3)
    assert not resident.over.is_set() and stood_in(table) == [False] * 4
    if how == "leaves":
        medleys.do(visitor.call(courier.LEAVE, EVERY_TABLE))
    else:
        medleys.loop.call_soon_threadsafe(visitor.close)
    assert until(resident.over.is_set)
    # A person can still come back, so the game is kept, with stand-ins in every Medley seat.
    assert table.status == "playing" and stood_in(table) == [False, True, True, True]
    with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
        play_until_end_of_deal(socket, 1)


def test_a_medley_that_left_one_game_is_not_asked_about_it_from_its_next(house):
    """The seat numbers of the two games are the same: the old game must not take the new game's answers."""
    client, medleys = house
    resident = medleys.resident()
    headers, token = sign_up(client)
    first = table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=headers).json()["id"])
    assert sent_home(client, medleys, resident)
    resident.over.clear()
    _, other = sign_up(client, "Bea")
    second = table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client), "over_score": 1},
                                          headers={"X-Hearts-Token": other}).json()["id"])
    asked = len([c for c in resident.calls if c[0] in ("pass", "play")])
    with client.websocket_connect(f"/api/tables/{first.id}/ws?token={token}") as socket:
        play_until_end_of_deal(socket, 1)
    with client.websocket_connect(f"/api/tables/{second.id}/ws?token={other}") as socket:
        assert socket.receive_json()["table"]["seats"][1]["stand_in"] is False
    # The first game's deal was played by stand-ins: the resident was asked only for the second game's passes.
    plays = [c for c in resident.calls if c[0] == "play"]
    assert not plays and len([c for c in resident.calls if c[0] == "pass"]) - asked <= 3


# A table still waiting for players ----------------------------------------------------------------------------------
def waiting_table(client, headers, kinds):
    made = client.post("/api/tables", json={"seats": ["person"] + kinds}, headers=headers).json()
    assert made["status"] == "open"
    return table_of(client, made["id"])


def kinds_of(table):
    return [(s["kind"], table.is_open(i + 1)) for i, s in enumerate(table.seats)]


@pytest.mark.parametrize("when", ["never opened the table", "opened it and closed it"])
def test_a_waiting_table_gives_the_residents_players_back_when_its_owner_has_gone(house, when):
    client, medleys = house
    resident = medleys.resident()
    headers, token = sign_up(client)
    table = waiting_table(client, headers, offered_kinds(client)[:2])
    assert offered_now(client) == []
    if when == "opened it and closed it":
        with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
            socket.receive_json()
            time.sleep(HOLD + 0.3)  # While the owner waits at the table, the players stay.
            assert offered_now(client) == [] and kinds_of(table)[2:] == [("medley", False)] * 2
    # The resident was told nothing about a table that never started, so its offer stands as it was.
    assert until(lambda: offered_now(client) == OFFERED)
    assert not resident.over.is_set() and not resident.calls
    assert table.status == "open" and kinds_of(table) == [("person", False)] + [("person", True)] * 3
    # The owner comes back to a table with those seats open, and can still fill it and play.
    with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
        assert [s["open"] for s in socket.receive_json()["table"]["seats"]] == [False, True, True, True]
        assert client.post(f"/api/tables/{table.id}/fill", headers=headers).status_code == 200
        play_until_end_of_deal(socket, 1)
    assert offered_now(client) == OFFERED and not resident.calls


@pytest.mark.parametrize("how", ["leaves", "loses its connection"])
def test_a_medley_waiting_at_a_table_keeps_the_residents_players_there_until_it_goes(house, how):
    client, medleys = house
    resident = medleys.resident()
    headers, _ = sign_up(client)
    table = waiting_table(client, headers, ["person"] + offered_kinds(client)[:1])
    visitor = medleys.connect()
    medleys.do(visitor.call(courier.SIT, Writer().string(table.id).bytes() + names("Visitor").bytes()))
    time.sleep(HOLD + 0.3)
    assert offered_now(client) == [] and table.status == "open"
    if how == "leaves":
        medleys.do(visitor.call(courier.LEAVE, EVERY_TABLE))
    else:
        medleys.loop.call_soon_threadsafe(visitor.close)
    assert until(lambda: offered_now(client) == OFFERED)
    assert table.status == "open" and kinds_of(table) == [("person", False)] + [("person", True)] * 3
    assert not resident.calls


def test_a_medley_that_opened_a_waiting_table_and_left_frees_the_residents_players(house):
    client, medleys = house
    resident = medleys.resident()
    visitor = medleys.connect()
    kinds = offered_kinds(client)
    table = table_of(client, medleys.new_table(visitor, "person", *kinds[:2]))
    assert table.status == "open" and offered_now(client) == []
    time.sleep(HOLD + 0.3)
    assert offered_now(client) == []  # The Medley is waiting there.
    medleys.do(visitor.call(courier.LEAVE, EVERY_TABLE))
    assert until(lambda: offered_now(client) == OFFERED)
    assert table.status == "open" and all(open for _, open in kinds_of(table)) and not resident.calls


# One Medley, several tables ------------------------------------------------------------------------------------------
def test_one_medleys_players_are_at_several_tables_at_once_and_each_game_is_its_own(house):
    client, medleys = house
    resident = medleys.resident(tables=3)
    people = [sign_up(client, name) for name in ("Ana", "Bea", "Cy")]
    tables = []
    for headers, _ in people:
        assert offered_now(client) == OFFERED  # Still on offer while there is room.
        made = client.post("/api/tables", json={"seats": offered_kinds(client), "over_score": 1}, headers=headers).json()
        tables.append(table_of(client, made["id"]))
    assert offered_now(client) == []  # Three tables is what it said it would take.
    _, token = sign_up(client, "Dee")
    full = client.post("/api/tables", json={"seats": ["medley:%s:0" % resident_id(client)] * 1 + ["clown", "clown"]},
                       headers={"X-Hearts-Token": token})
    assert full.status_code == 400 and "taken" in full.json()["detail"]
    # The games are played in turn here, a deal of each, then to the end: the Medley keeps them apart.
    for (_, token), table in zip(people, tables):
        with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
            while not table.game.finished:
                play_until_end_of_deal(socket, 1)
    assert until(lambda: len(resident.ended) == 3)
    assert set(resident.ended) == {t.id for t in tables} and all(resident.ended.values())
    for table in tables:
        mine = [c for c, t in zip(resident.calls, resident.tables) if t == table.id]
        assert mine[0] == ("table", [table.seat_name(i) for i in (1, 2, 3, 4)], [2, 3, 4])
        plays = [c for c in mine if c[0] == "play"]
        cards = [e for e in client.app.state.store.events(table.id) if e["type"] == "card" and e["seat"] != 1]
        assert len(plays) == len(cards) and len(plays) % 39 == 0  # Every card of its three seats, and no other's.
    assert until(lambda: offered_now(client) == OFFERED)  # Free again, with nothing to do.


def resident_id(client):
    return next(iter(client.app.state.door.links))


def test_a_medley_leaves_one_table_and_plays_on_at_the_others(house):
    client, medleys = house
    resident = medleys.resident(tables=2)
    (ana, ana_token), (bea, bea_token) = sign_up(client, "Ana"), sign_up(client, "Bea")
    first = table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=ana).json()["id"])
    second = table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client), "over_score": 1},
                                          headers=bea).json()["id"])
    with client.websocket_connect(f"/api/tables/{second.id}/ws?token={bea_token}") as socket:
        # Ana never opens hers: after the wait her table gives the players back, and Bea's game is untouched.
        assert until(lambda: resident.ended.get(first.id) == [])
        assert stood_in(first) == [False, True, True, True] and stood_in(second) == [False] * 4
        assert offered_now(client) == OFFERED  # One table of its two is free again.
        while not second.game.finished:
            play_until_end_of_deal(socket, 1)
    assert until(lambda: bool(resident.ended.get(second.id)))
    # The Medley can also leave one table by name.
    third = table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client)}, headers=bea).json()["id"])
    with client.websocket_connect(f"/api/tables/{third.id}/ws?token={bea_token}") as socket:
        socket.receive_json()
        medleys.do(resident.call(courier.LEAVE, Writer().string(third.id).bytes()))
        assert stood_in(third) == [False, True, True, True] and third.status == "playing"
        assert offered_now(client) == OFFERED
    with pytest.raises(Exception):
        medleys.do(resident.call(courier.LEAVE, Writer().string("nosuchtable").bytes()))


def test_a_medley_that_goes_away_leaves_every_table_to_stand_ins(house):
    client, medleys = house
    resident = medleys.resident(tables=2)
    people = [sign_up(client, name) for name in ("Ana", "Bea")]
    tables = [table_of(client, client.post("/api/tables", json={"seats": offered_kinds(client), "over_score": 1},
                                           headers=headers).json()["id"]) for headers, _ in people]
    medleys.loop.call_soon_threadsafe(resident.close)
    assert until(lambda: all(stood_in(t) == [False, True, True, True] for t in tables))
    for (_, token), table in zip(people, tables):
        with client.websocket_connect(f"/api/tables/{table.id}/ws?token={token}") as socket:
            while not table.game.finished:
                play_until_end_of_deal(socket, 1)
