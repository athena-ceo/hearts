# Copyright (c) 2026 Athena Decisions Systems SAS.
"""Accounts, invitations and game records, in SQLite with the standard library.

Invite-only for now: registering needs an unused invitation code.  Auth is low-ceremony, as in Adventure: name
and password, and a random bearer token per login.  Each game is its seed plus an append-only list of events,
enough to rebuild it exactly.  Point HEARTS_DB at a persistent volume; it defaults to memory.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
import uuid

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    is_admin      INTEGER NOT NULL DEFAULT 0,
    created       REAL NOT NULL,
    last_seen     REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS tokens (
    token     TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    created   REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS invites (
    code     TEXT PRIMARY KEY,
    note     TEXT NOT NULL DEFAULT '',
    created  REAL NOT NULL,
    used_by  TEXT,
    used_at  REAL
);
CREATE TABLE IF NOT EXISTS tables (
    id         TEXT PRIMARY KEY,
    seed       INTEGER NOT NULL,
    config     TEXT NOT NULL,
    seats      TEXT NOT NULL,
    status     TEXT NOT NULL,
    created    REAL NOT NULL,
    updated    REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    table_id TEXT NOT NULL,
    seq      INTEGER NOT NULL,
    event    TEXT NOT NULL,
    PRIMARY KEY (table_id, seq)
);
"""
ITERATIONS = 600_000


def hash_password(password: str, iterations: int = ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    iterations, salt, digest = stored.split("$")
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
    return hmac.compare_digest(check, base64.b64decode(digest))


class AuthError(ValueError):
    pass


class Store:
    def __init__(self, path: str | None = None):
        self.path = path if path is not None else os.environ.get("HEARTS_DB", ":memory:")
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        with self.lock, self.db:
            if self.path != ":memory:":
                self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript(_SCHEMA)

    # Invitations ----------------------------------------------------------------------------------------------
    def create_invite(self, note: str = "") -> str:
        code = secrets.token_urlsafe(9)
        with self.lock, self.db:
            self.db.execute("INSERT INTO invites (code, note, created) VALUES (?, ?, ?)", (code, note, time.time()))
        return code

    def list_invites(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute(
                "SELECT i.code, i.note, i.created, i.used_at, p.name AS used_by FROM invites i "
                "LEFT JOIN players p ON p.id = i.used_by ORDER BY i.created DESC").fetchall()
        return [dict(r) for r in rows]

    # Accounts -------------------------------------------------------------------------------------------------
    def register(self, name: str, password: str, code: str) -> tuple[dict, str]:
        name = name.strip()
        if not 1 <= len(name) <= 24:
            raise AuthError("Choose a name of 1 to 24 characters.")
        if len(password) < 8:
            raise AuthError("Choose a password of at least 8 characters.")
        hashed = hash_password(password)
        with self.lock, self.db:
            invite = self.db.execute("SELECT used_by FROM invites WHERE code = ?", (code,)).fetchone()
            if invite is None:
                raise AuthError("That invitation code isn't valid.")
            if invite["used_by"]:
                raise AuthError("That invitation has already been used.")
            if self.db.execute("SELECT 1 FROM players WHERE name = ?", (name,)).fetchone():
                raise AuthError("That name is taken.")
            player_id, now = uuid.uuid4().hex, time.time()
            self.db.execute("INSERT INTO players (id, name, password_hash, created, last_seen) VALUES (?, ?, ?, ?, ?)",
                            (player_id, name, hashed, now, now))
            self.db.execute("UPDATE invites SET used_by = ?, used_at = ? WHERE code = ?", (player_id, now, code))
            token = self._issue(player_id)
        return {"id": player_id, "name": name}, token

    def login(self, name: str, password: str) -> tuple[dict, str]:
        with self.lock:
            row = self.db.execute("SELECT * FROM players WHERE name = ?", (name.strip(),)).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            raise AuthError("That name and password don't match.")
        with self.lock, self.db:
            token = self._issue(row["id"])
        return {"id": row["id"], "name": row["name"]}, token

    def _issue(self, player_id: str) -> str:
        token = secrets.token_urlsafe(32)
        self.db.execute("INSERT INTO tokens (token, player_id, created) VALUES (?, ?, ?)",
                        (token, player_id, time.time()))
        return token

    def user_for_token(self, token: str | None) -> dict | None:
        if not token:
            return None
        with self.lock, self.db:
            row = self.db.execute("SELECT p.id, p.name FROM tokens t JOIN players p ON p.id = t.player_id "
                                  "WHERE t.token = ?", (token,)).fetchone()
            if row:
                self.db.execute("UPDATE players SET last_seen = ? WHERE id = ?", (time.time(), row["id"]))
        return dict(row) if row else None

    def logout(self, token: str) -> None:
        with self.lock, self.db:
            self.db.execute("DELETE FROM tokens WHERE token = ?", (token,))

    def list_users(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT name, created, last_seen FROM players ORDER BY last_seen DESC").fetchall()
        return [dict(r) for r in rows]

    # Games ----------------------------------------------------------------------------------------------------
    def save_table(self, table_id: str, seed: int, config: dict, seats: list, status: str) -> None:
        now = time.time()
        with self.lock, self.db:
            self.db.execute(
                "INSERT INTO tables (id, seed, config, seats, status, created, updated) VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET seats = excluded.seats, status = excluded.status, "
                "updated = excluded.updated",
                (table_id, seed, json.dumps(config), json.dumps(seats), status, now, now))

    def append_event(self, table_id: str, seq: int, event: dict) -> None:
        with self.lock, self.db:
            self.db.execute("INSERT INTO events (table_id, seq, event) VALUES (?, ?, ?)",
                            (table_id, seq, json.dumps(event)))

    def events(self, table_id: str) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT event FROM events WHERE table_id = ? ORDER BY seq", (table_id,)).fetchall()
        return [json.loads(r["event"]) for r in rows]

    def tables(self) -> list[dict]:
        with self.lock:
            rows = self.db.execute("SELECT * FROM tables ORDER BY created").fetchall()
        return [{**dict(r), "config": json.loads(r["config"]), "seats": json.loads(r["seats"])} for r in rows]
