#!/usr/bin/env python3
"""Check a decision log from the LLM player against what its seat may know.

Prints one S-expression line for Interlisp to READ: T, or the problems found.  Fields are compared
with an exact list, so a new field has to be added here on purpose: this is the guard against
leaking another seat's cards into a request.
"""
import json
import sys

PLAY_FIELDS = {"decision", "seat", "deal", "direction", "hand", "legal", "trick", "hearts_broken",
               "first_trick", "passed", "received", "history", "scores", "over_score", "plan"}
PASS_FIELDS = {"decision", "seat", "deal", "direction", "hand", "scores", "over_score", "plan"}


def problems_in(req):
    problems = []
    allowed = PASS_FIELDS if req["decision"] == "pass" else PLAY_FIELDS
    if set(req) - allowed:
        problems.append(f"unexpected fields {sorted(set(req) - allowed)}")
    hand = req["hand"]
    if len(set(hand)) != len(hand):
        problems.append("duplicate cards in hand")
    if req["decision"] == "pass":
        if len(hand) != 13:
            problems.append(f"passing from {len(hand)} cards")
        return problems
    history = req["history"]
    played = [c for t in history for c in t["cards"]] + req["trick"]["cards"]
    if len(set(played)) != len(played):
        problems.append("a card was played twice")
    if set(played) & set(hand):
        problems.append("a played card is still in hand")
    if not set(req["legal"]) <= set(hand):
        problems.append("legal cards outside the hand")
    if len(hand) + len(history) != 13:
        problems.append(f"{len(hand)} cards in hand after {len(history)} tricks")
    if any(len(t["cards"]) != 4 or not 1 <= t["winner"] <= 4 for t in history):
        problems.append("an incomplete completed trick")
    return problems


def main(path):
    decisions = 0
    problems = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            decisions += 1
            problems += problems_in(json.loads(line)["request"])
    if decisions == 0:
        problems.append("the log is empty")
    print("T" if not problems else "(" + " ".join(json.dumps(p) for p in problems[:5]) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
