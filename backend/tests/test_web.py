# Copyright (c) 2026 Athena Decision Systems SAS.
"""The server: invitations, tables, moves, hidden hands, reconnection and restarts, over real sockets."""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from hearts.web import create_app


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("HEARTS_ADMIN_PASSWORD", "secret-for-tests")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "hearts.db")
        with TestClient(create_app(path)) as client:
            yield client, path


def invite(client):
    return client.post("/api/admin/invites", json={"note": "test"}, headers={"X-Hearts-Admin": "secret-for-tests"}).json()["code"]


def sign_up(client, name="Ana"):
    r = client.post("/api/auth/register", json={"name": name, "password": "long enough", "code": invite(client)})
    assert r.status_code == 200, r.text
    return {"X-Hearts-Token": r.json()["token"]}, r.json()["token"]


def test_registering_needs_an_unused_invitation(setup):
    client, _ = setup
    bad = client.post("/api/auth/register", json={"name": "A", "password": "long enough", "code": "nope"})
    assert bad.status_code == 400
    code = invite(client)
    assert client.post("/api/auth/register", json={"name": "A", "password": "long enough", "code": code}).status_code == 200
    again = client.post("/api/auth/register", json={"name": "B", "password": "long enough", "code": code})
    assert again.status_code == 400 and "already" in again.json()["detail"]
    assert client.post("/api/auth/login", json={"name": "A", "password": "wrong password"}).status_code == 401
    assert client.post("/api/auth/login", json={"name": "A", "password": "long enough"}).status_code == 200


def test_admin_routes_need_the_password_and_routes_need_a_player(setup):
    client, _ = setup
    assert client.post("/api/admin/invites", json={}).status_code == 403
    assert client.post("/api/admin/invites", json={}, headers={"X-Hearts-Admin": "wrong"}).status_code == 403
    assert client.get("/api/tables").status_code == 401
    assert client.post("/api/tables", json={"seats": ["clown"] * 3}).status_code == 401


def play_until_end_of_deal(socket, seat):
    """Answer as a person until a deal ends, checking that no other seat's cards ever arrive."""
    view = None
    while True:
        m = socket.receive_json()
        if m["type"] in ("snapshot", "turn") and m.get("view"):
            view = m["view"]
            if seat in m.get("waiting", []):
                if view["decision"] == "pass":
                    socket.send_json({"type": "pass", "cards": view["hand"][:3]})
                elif view["legal"]:
                    socket.send_json({"type": "play", "card": view["legal"][0]})
        if m["type"] == "deal":
            assert len(m["hands"]) == 13 and all(isinstance(c, str) for c in m["hands"])
        if m["type"] == "received":
            assert len(m["cards"]) == 3
        if m["type"] == "passed" and m["seat"] != seat:
            assert "cards" not in m
        if m["type"] == "refused":
            raise AssertionError(m)
        if m["type"] == "deal_end":
            return m


def test_a_person_plays_a_deal_against_bots_over_a_socket(setup):
    client, _ = setup
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["clown", "network", "clown"]}, headers=headers).json()
    assert table["status"] == "playing" and table["your_seat"] == 1
    names = [s["name"] for s in table["seats"]]
    assert names[0] == "Ana" and len(set(names)) == 4
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        end = play_until_end_of_deal(socket, 1)
    assert sum(max(s, 0) for s in end["scores"]) in (26, 0)
    listed = client.get("/api/tables", headers=headers).json()["tables"]
    assert listed[0]["id"] == table["id"] and listed[0]["deal"] >= 1


def test_illegal_moves_are_refused_and_thoughts_stay_hidden(setup):
    client, _ = setup
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["network", "network", "network"]}, headers=headers).json()
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        socket.send_json({"type": "pass", "cards": ["XX", "YY", "ZZ"]})
        m = socket.receive_json()
        while m["type"] != "refused":
            assert "thought" not in m
            m = socket.receive_json()
    assert client.post(f"/api/tables/{table['id']}/move", json={"card": "C2"}, headers=headers).status_code == 409


def test_study_tables_show_thoughts_and_advice(setup):
    client, _ = setup
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["network", "network", "network"], "study": True}, headers=headers).json()
    assert table["study"]
    saw_thought = saw_advice = False
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        for _ in range(400):
            m = socket.receive_json()
            if m["type"] == "card" and m.get("thought"):
                saw_thought = True
            if m["type"] == "advice":
                saw_advice = True
                assert any(e["kind"] == "network" for e in m["entries"])
            if m["type"] in ("snapshot", "turn") and m.get("view") and 1 in m.get("waiting", []):
                view = m["view"]
                if view["decision"] == "pass":
                    socket.send_json({"type": "pass", "cards": view["hand"][:3]})
                elif view["legal"]:
                    socket.send_json({"type": "play", "card": view["legal"][0]})
            if saw_thought and saw_advice:
                break
    assert saw_thought and saw_advice


def test_two_people_at_a_table_see_only_their_own_cards(setup):
    client, _ = setup
    first, first_token = sign_up(client, "Ana")
    second, second_token = sign_up(client, "Bruno")
    table = client.post("/api/tables", json={"seats": ["person", "clown", "clown"]}, headers=first).json()
    assert table["status"] == "open"
    assert any(t["id"] == table["id"] for t in client.get("/api/tables", headers=second).json()["tables"])
    joined = client.post(f"/api/tables/{table['id']}/join", json={}, headers=second).json()
    assert joined["status"] == "playing" and joined["your_seat"] == 2
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={first_token}") as a, \
            client.websocket_connect(f"/api/tables/{table['id']}/ws?token={second_token}") as b:
        hand_a = a.receive_json()["view"]["hand"]
        hand_b = b.receive_json()["view"]["hand"]
        assert not set(hand_a) & set(hand_b)
    full = client.post(f"/api/tables/{table['id']}/join", json={}, headers=sign_up(client, "Mei")[0])
    assert full.status_code == 409


def test_a_restart_rebuilds_the_game_and_review_works(monkeypatch):
    monkeypatch.setenv("HEARTS_ADMIN_PASSWORD", "secret-for-tests")
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "hearts.db")
        with TestClient(create_app(path)) as client:
            headers, token = sign_up(client)
            table = client.post("/api/tables", json={"seats": ["clown", "network", "clown"]}, headers=headers).json()
            with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
                end = play_until_end_of_deal(socket, 1)
            assert end["number"] == 1
            before_hand = None
            with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
                snap = socket.receive_json()
                before_hand, before_number = snap["view"]["hand"], snap["number"]
        with TestClient(create_app(path)) as client:
            with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
                snap = socket.receive_json()
            assert snap["number"] == before_number and snap["view"]["hand"] == before_hand
            review = client.get(f"/api/tables/{table['id']}/deals/1/review", headers=headers)
            assert review.status_code == 200, review.text
            data = review.json()
            assert data["scores"] == end["scores"] and len(data["tricks"]) == 13
            assert data["what_if"]["kind"] == "network" and len(data["what_if"]["scores"]) == 4
            assert data["decisions"] and "network" in data["decisions"][0]["advice"]
            assert client.get(f"/api/tables/{table['id']}/deals/9/review", headers=headers).status_code == 409


def test_the_seed_never_reaches_a_client(setup):
    client, _ = setup
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["clown", "clown", "clown"]}, headers=headers).json()
    assert "seed" not in table
    live = client.app.state.tables.tables[table["id"]]
    recorded = client.app.state.store.events(table["id"])
    assert recorded[0]["type"] == "game" and "seed" in recorded[0]  # The record keeps it, to rebuild the game.
    for seat in (1, None):
        assert all("seed" not in live.client_event(event, seat) for event in recorded)
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        assert "seed" not in str(socket.receive_json())


def test_a_new_connection_gets_the_advice_and_someone_seated_gets_a_seat(setup):
    client, _ = setup
    headers, token = sign_up(client)
    other, other_token = sign_up(client, "Bruno")
    study = client.post("/api/tables", json={"seats": ["network", "network", "network"], "study": True}, headers=headers).json()
    with client.websocket_connect(f"/api/tables/{study['id']}/ws?token={token}") as socket:
        while socket.receive_json()["type"] != "advice":
            pass
    with client.websocket_connect(f"/api/tables/{study['id']}/ws?token={token}") as socket:
        assert socket.receive_json()["type"] == "snapshot"
        assert socket.receive_json()["type"] == "advice"
    table = client.post("/api/tables", json={"seats": ["person", "clown", "clown"]}, headers=headers).json()
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={other_token}") as watcher:
        assert watcher.receive_json()["seat"] is None
        client.post(f"/api/tables/{table['id']}/join", json={}, headers=other)
        m = watcher.receive_json()
        while m["type"] != "snapshot":
            m = watcher.receive_json()
        assert m["seat"] == 2


def test_a_refused_socket_says_why(setup):
    client, _ = setup
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect("/api/tables/none/ws?token=bad") as socket:
            socket.receive_json()
    assert refused.value.code == 4401


def test_a_play_that_times_out_is_made_for_you(setup):
    client, _ = setup
    headers, token = sign_up(client)
    table = client.post("/api/tables", json={"seats": ["clown", "clown", "clown"], "time_limit": 10}, headers=headers).json()
    live = client.app.state.tables.tables[table["id"]]
    import asyncio
    deal = None
    with client.websocket_connect(f"/api/tables/{table['id']}/ws?token={token}") as socket:
        socket.receive_json()
        portal = client.portal
        async def run_out():
            await asyncio.sleep(0.05)
            await live._time_out(1)
            live.wake.set()
        portal.call(run_out)
        passed = False
        for _ in range(20):
            m = socket.receive_json()
            if m["type"] == "passed" and m["seat"] == 1:
                passed = True
                break
        assert passed
        while live.game.deal.to_play != 1:
            m = socket.receive_json()
        async def run_out_play():
            await live._time_out(1)
            live.wake.set()
        portal.call(run_out_play)
        while True:
            m = socket.receive_json()
            if m["type"] == "card" and m["seat"] == 1:
                break
