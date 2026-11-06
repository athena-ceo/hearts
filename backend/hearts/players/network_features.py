# Copyright (c) 2026 Athena Decisions Systems SAS.
"""What the network sees: a request from Medley or the simulator, as 512 numbers from the point of
view of the seat deciding.  Pure Python, so the same code runs in training and beside Medley."""
from hearts import INDEX, points

SIZE = 512
HAND, PLAYED, MY_PASSED, RECEIVED = 0, 52, 104, 156
TRICK = 208            # 3 x 52: the cards played so far in this trick, in order
TRICK_COUNT = 364      # 4: how many cards are on the trick
WINNING = 368          # 4: which seat is winning it, relative to me
VOIDS = 372            # 4 x 4: seat relative to me, suit
TAKEN = 388            # 4: points taken this deal, relative to me (scaled by 1/26)
BROKEN, FIRST, QUEEN_GONE = 392, 393, 394
TRICK_NUMBER = 395     # scaled by 1/13
DIRECTION = 396        # 4: Left, Across, Right, no pass
PHASE = 400            # 4: choosing pass card 1, 2 or 3, or playing
SELECTED = 404         # 52: cards chosen so far for this pass
HAS_POINTS = 456       # 4: has this seat taken any points
LEGAL = 460            # 52

SUIT_INDEX = {"C": 0, "D": 1, "H": 2, "S": 3}
DIRECTION_INDEX = {"Left": 0, "Across": 1, "Right": 2}
SCALED = {TAKEN + i: 1 / 26 for i in range(4)} | {TRICK_NUMBER: 1 / 13}


def encode(request, selected=()):
    """Return ({index: value}, [legal card indices]).  Values are raw: multiply by SCALED to use them."""
    x = {}
    seat = request["seat"]
    for card in request["hand"]:
        x[HAND + INDEX[card]] = 1
    x[DIRECTION + DIRECTION_INDEX.get(request.get("direction"), 3)] = 1
    if request["decision"] == "pass":
        x[PHASE + len(selected)] = 1
        for card in selected:
            x[SELECTED + INDEX[card]] = 1
        legal = [INDEX[c] for c in request["hand"] if c not in selected]
    else:
        x[PHASE + 3] = 1
        legal = [INDEX[c] for c in request["legal"]]
        taken = [0, 0, 0, 0]
        seen = set()
        for done in request.get("history") or []:
            cards = done["cards"]
            suit = cards[0][0]
            leader = done["leader"]
            for i, card in enumerate(cards):
                seen.add(card)
                if card[0] != suit:
                    x[VOIDS + 4 * ((leader - 1 + i - (seat - 1)) % 4) + SUIT_INDEX[suit]] = 1
            taken[done["winner"] - 1] += sum(points(c) for c in cards)
        trick = request["trick"]
        cards = trick["cards"]
        x[TRICK_COUNT + len(cards)] = 1
        if cards:
            suit = cards[0][0]
            best = 0
            for i, card in enumerate(cards):
                seen.add(card)
                x[TRICK + 52 * i + INDEX[card]] = 1
                if card[0] != suit:
                    x[VOIDS + 4 * ((trick["leader"] - 1 + i - (seat - 1)) % 4) + SUIT_INDEX[suit]] = 1
                elif INDEX[card] > INDEX[cards[best]]:
                    best = i
            x[WINNING + (trick["leader"] - 1 + best - (seat - 1)) % 4] = 1
        for card in seen:
            x[PLAYED + INDEX[card]] = 1
        for card in request.get("passed") or []:
            if card not in seen:
                x[MY_PASSED + INDEX[card]] = 1
        for card in request.get("received") or []:
            x[RECEIVED + INDEX[card]] = 1
        for i in range(4):
            relative = (i - (seat - 1)) % 4
            if taken[i]:
                x[TAKEN + relative] = taken[i]
                x[HAS_POINTS + relative] = 1
        if request.get("hearts_broken"):
            x[BROKEN] = 1
        if request.get("first_trick"):
            x[FIRST] = 1
        if "SQ" in seen:
            x[QUEEN_GONE] = 1
        x[TRICK_NUMBER] = len(request.get("history") or []) + 1
    for i in legal:
        x[LEGAL + i] = 1
    return x, legal
