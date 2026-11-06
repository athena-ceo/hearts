#!/usr/bin/env python3
"""Play one move with a trained network, for the LLM player's seat in Medley: same request file, same
one-line answer as medley/llm_player.py.  Pure Python, so it needs nothing installed, and it does in
the open what a Lisp executor would have to do.

    python3 nn_helper.py --model WEIGHTS.json REQUEST.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from features import LEGAL, SCALED, SIZE, encode  # noqa: E402
from hearts_sim import DECK  # noqa: E402


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def forward(model, x):
    """The network's scores for the 52 cards: two hidden layers of rectified units."""
    values = [0.0] * SIZE
    for index, value in x.items():
        values[index] = value * SCALED.get(index, 1)
    for weights, bias in model["hidden"]:
        values = [max(0.0, sum(w * v for w, v in zip(row, values) if v) + b) for row, b in zip(weights, bias)]
    weights, bias = model["policy"]
    return [sum(w * v for w, v in zip(row, values)) + b for row, b in zip(weights, bias)]


def best_card(model, request, selected=()):
    x, legal = encode(request, selected)
    scores = forward(model, x)
    return DECK[max(legal, key=lambda i: scores[i])]


def choose(model, request):
    if request["decision"] == "pass":
        selected = []
        for _ in range(3):
            selected.append(best_card(model, request, selected))
        return selected
    return [best_card(model, request)]


def lisp_card(card):
    return f"({card[0]} . {card[1:]})"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("request", nargs="?")
    parser.add_argument("--model")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--log")
    for ignored in ("--provider", "--effort", "--timeout"):  # What Medley sends for an LLM.
        parser.add_argument(ignored)
    args = parser.parse_args(argv)
    if args.check:
        print(f'(CHECK "{sys.version.split()[0]}" "none" T "{args.model}")', flush=True)
        return 0
    started = time.monotonic()
    try:
        with open(args.request, encoding="utf-8") as f:
            request = json.load(f)
        cards = choose(load(args.model), request)
        elapsed = (time.monotonic() - started) * 1000
        reply = f'(OK ({" ".join(lisp_card(c) for c in cards)}) "" "The network chooses {" ".join(cards)}." (0 0 {int(elapsed)}))'
    except (OSError, ValueError, KeyError) as e:
        reply = '(ERROR "' + f"{type(e).__name__}: {e}".replace("%", "%%").replace('"', "'") + '")'
        request = {}
    if args.log:
        with open(args.log, "a", encoding="utf-8") as f:
            f.write(json.dumps({"time": time.time(), "seconds": round(time.monotonic() - started, 3),
                                "request": request, "reply": reply}) + "\n")
    print(reply, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
