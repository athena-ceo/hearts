# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The web backend: accounts by invitation, tables, and a WebSocket per client.

    python -m hearts.web        # REST and WebSockets on :8050

Every route needs a signed-in player, except the health probe and signing in.  The admin routes need the
HEARTS_ADMIN_PASSWORD, sent as X-Hearts-Admin.  They are disabled when it isn't set.
"""
from __future__ import annotations

import asyncio
import hmac
import logging
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from .game import IllegalMove
from .players import BOT_KINDS
from .review import review
from .store import AuthError, Store
from .tables import Tables

log = logging.getLogger("hearts.web")


class Credentials(BaseModel):
    name: str
    password: str


class Registration(Credentials):
    code: str


class NewTable(BaseModel):
    seats: list[str] = Field(min_length=3, max_length=3, description="Who sits left, across and right of you.")
    study: bool = False
    invite_only: bool = False
    time_limit: int | None = Field(default=None, ge=10, le=86400)
    fill_after: int | None = Field(default=None, ge=0, le=3600)
    over_score: int = Field(default=100, ge=1, le=1000)


class Join(BaseModel):
    seat: int | None = None


class Move(BaseModel):
    cards: list[str] | None = None
    card: str | None = None


class NewInvite(BaseModel):
    note: str = ""


class Client:
    """One socket.  Everything sent to it goes through one queue, so messages keep their order."""

    def __init__(self, socket: WebSocket, player_id: str):
        self.socket = socket
        self.player_id = player_id
        self.queue: asyncio.Queue = asyncio.Queue()

    async def write(self):
        try:
            while True:
                await self.socket.send_json(await self.queue.get())
        except Exception:  # A dead socket ends in the reader's handler.
            pass


def create_app(db_path: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await tables.restore()
        yield
        await tables.stop()

    app = FastAPI(title="Hearts", lifespan=lifespan)
    store = Store(db_path)
    tables = Tables(store)
    app.state.store = store
    app.state.tables = tables

    def player(x_hearts_token: str | None = Header(default=None)) -> dict:
        user = store.user_for_token(x_hearts_token)
        if user is None:
            raise HTTPException(401, "Please sign in.")
        return user

    def admin(x_hearts_admin: str | None = Header(default=None)) -> None:
        password = os.environ.get("HEARTS_ADMIN_PASSWORD")
        if not password:
            raise HTTPException(503, "Set HEARTS_ADMIN_PASSWORD on the server to use the admin routes.")
        if not x_hearts_admin or not hmac.compare_digest(x_hearts_admin, password):
            raise HTTPException(403, "That admin password isn't right.")

    def find_table(table_id: str):
        table = tables.tables.get(table_id)
        if table is None:
            raise HTTPException(404, "There's no such table.")
        return table

    @app.get("/health")
    def health():
        return {"status": "ok", "tables": len(tables.tables), "opponents": sorted(BOT_KINDS)}

    # Accounts
    @app.post("/api/auth/register")
    def register(body: Registration):
        try:
            user, token = store.register(body.name, body.password, body.code)
        except AuthError as e:
            raise HTTPException(400, str(e))
        return {"player": user, "token": token}

    @app.post("/api/auth/login")
    def login(body: Credentials):
        try:
            user, token = store.login(body.name, body.password)
        except AuthError as e:
            raise HTTPException(401, str(e))
        return {"player": user, "token": token}

    @app.post("/api/auth/logout")
    def logout(user: dict = Depends(player), x_hearts_token: str | None = Header(default=None)):
        store.logout(x_hearts_token)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(user: dict = Depends(player)):
        return {"player": user}

    # Tables
    @app.get("/api/opponents")
    def opponents(user: dict = Depends(player)):
        return {"opponents": [{"kind": kind, "label": cls.label} for kind, cls in BOT_KINDS.items()]}

    @app.get("/api/tables")
    def list_tables(user: dict = Depends(player)):
        return {"tables": tables.visible(user["id"])}

    @app.post("/api/tables")
    async def create_table(body: NewTable, user: dict = Depends(player)):
        try:
            table = tables.create(user, body.seats, body.model_dump(exclude={"seats"}))
        except IllegalMove as e:
            raise HTTPException(400, str(e))
        return table.describe(user["id"])

    @app.get("/api/tables/{table_id}")
    def get_table(table_id: str, user: dict = Depends(player)):
        return find_table(table_id).describe(user["id"])

    @app.post("/api/tables/{table_id}/join")
    async def join_table(table_id: str, body: Join, user: dict = Depends(player)):
        table = find_table(table_id)
        try:
            table.join(user, body.seat)
        except IllegalMove as e:
            raise HTTPException(409, str(e))
        table.refresh_clients(user["id"])
        return table.describe(user["id"])

    @app.post("/api/tables/{table_id}/fill")
    async def fill_table(table_id: str, user: dict = Depends(player)):
        table = find_table(table_id)
        if not table.seat_of(user["id"]):
            raise HTTPException(403, "You aren't at this table.")
        table.fill_empty_seats()
        table.refresh_clients()
        return table.describe(user["id"])

    @app.post("/api/tables/{table_id}/move")
    async def move(table_id: str, body: Move, user: dict = Depends(player)):
        try:
            find_table(table_id).submit(user["id"], cards=body.cards, card=body.card)
        except IllegalMove as e:
            raise HTTPException(409, str(e))
        return {"ok": True}

    @app.get("/api/tables/{table_id}/deals/{number}/review")
    async def deal_review(table_id: str, number: int, user: dict = Depends(player)):
        table = find_table(table_id)
        result = await asyncio.to_thread(review, store.events(table_id), number, table.seat_of(user["id"]), table.seats)
        if result is None:
            raise HTTPException(409, "This deal isn't finished yet.")
        return result

    # The live connection
    @app.websocket("/api/tables/{table_id}/ws")
    async def table_socket(socket: WebSocket, table_id: str, token: str = Query(...)):
        await socket.accept()  # Accepting first lets the client read why it was refused.
        user = store.user_for_token(token)
        table = tables.tables.get(table_id)
        if user is None or table is None:
            await socket.close(code=4401 if user is None else 4404)
            return
        client = Client(socket, user["id"])
        writer = asyncio.create_task(client.write())
        table.attach(client, table.seat_of(user["id"]))
        try:
            while True:
                message = await socket.receive_json()
                try:
                    if message.get("type") == "pass":
                        table.submit(user["id"], cards=message["cards"])
                    elif message.get("type") == "play":
                        table.submit(user["id"], card=message["card"])
                except (IllegalMove, KeyError) as e:
                    client.queue.put_nowait({"type": "refused", "message": str(e)})
        except WebSocketDisconnect:
            pass
        finally:
            table.connections.pop(client, None)
            writer.cancel()

    # Admin
    @app.post("/api/admin/invites", dependencies=[Depends(admin)])
    def create_invite(body: NewInvite):
        return {"code": store.create_invite(body.note)}

    @app.get("/api/admin/invites", dependencies=[Depends(admin)])
    def list_invites():
        return {"invites": store.list_invites()}

    @app.get("/api/admin/users", dependencies=[Depends(admin)])
    def list_users():
        return {"users": store.list_users()}

    return app


app = create_app()


def main():
    import uvicorn

    uvicorn.run("hearts.web:app", host="0.0.0.0", port=int(os.environ.get("BACKEND_PORT", "8050")))


if __name__ == "__main__":
    main()
