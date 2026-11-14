#!/usr/bin/env python3
# Copyright (c) 2025–2026 Athena Decision Systems SAS. All rights reserved.
"""The project's copy of the general working rules has not been edited by hand.

GENERATED into each project as ``scripts/lint-working-rules.py`` by
``working-rules/sync.py`` — change it there, never in a project.

``.claude/rules/general.md`` is a generated copy of ``general.md`` in the
``working-rules`` repository. It has to exist inside every project because a
cloud session, or another machine, sees only that one repository. A copy that
is edited in place drifts from the other projects' copies, so this check fails
when the text no longer matches the hash recorded in its own header.

When the source repository is checked out beside the project
(``../working-rules``) it also says whether the copy is behind the source. That
is a warning, not a failure: CI has no source checkout, and a rule change is
rolled out project by project.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

MARKER = "<!-- working-rules-sha256: "
COPY = Path(".claude/rules/general.md")
RESYNC = "python3 ../working-rules/sync.py ."


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    copy = root / COPY
    if not copy.is_file():
        print(f"working-rules: {COPY} is missing. Restore it with: {RESYNC}")
        return 1

    text = copy.read_bytes().decode("utf-8")
    head, found, rest = text.partition(MARKER)
    recorded, closed, body = rest.partition(" -->\n")
    if not found or not closed:
        print(f"working-rules: {COPY} has no hash header, so it was not written by sync.py. Regenerate it with: {RESYNC}")
        return 1

    actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual != recorded:
        print(
            f"working-rules: {COPY} was edited in place. It is a generated copy: "
            f"make the change in working-rules/general.md, then run: {RESYNC}"
        )
        return 1

    source = root.parent / "working-rules" / "general.md"
    if source.is_file():
        current = hashlib.sha256(source.read_bytes()).hexdigest()
        if current != recorded:
            print(f"working-rules: warning — {COPY} is behind ../working-rules/general.md. Update it with: {RESYNC}")
            return 0

    print("working-rules: the copy is intact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
