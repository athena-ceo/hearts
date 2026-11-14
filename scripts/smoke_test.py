#!/usr/bin/env python3
# Copyright (c) 2026 Athena Decision Systems SAS.
"""End-to-end smoke test against a running HEARTS backend: health, an invitation, a new account, and a table
that deals.  Needs HEARTS_ADMIN_PASSWORD to create the invitation.

    SMOKE_BASE_URL=http://localhost:8050 HEARTS_ADMIN_PASSWORD=... python3 scripts/smoke_test.py
"""
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.request

BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:8050").rstrip("/")


def call(path, body=None, headers=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(f"{BASE}{path}", data=data, headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode())


def main():
    health = call("/health")
    assert health["status"] == "ok", health
    print("health ok, opponents:", ", ".join(health["opponents"]))
    code = call("/api/admin/invites", {"note": "smoke test"}, {"X-Hearts-Admin": os.environ["HEARTS_ADMIN_PASSWORD"]})["code"]
    name = "smoke-" + secrets.token_hex(4)
    token = call("/api/auth/register", {"name": name, "password": secrets.token_urlsafe(12), "code": code})["token"]
    headers = {"X-Hearts-Token": token}
    table = call("/api/tables", {"seats": ["clown", "clown", "clown"]}, headers)
    assert table["status"] == "playing" and table["your_seat"] == 1, table
    listed = call("/api/tables", headers=headers)["tables"]
    assert any(t["id"] == table["id"] for t in listed)
    print("table", table["id"], "is playing")
    print("smoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
