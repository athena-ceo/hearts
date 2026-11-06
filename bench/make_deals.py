#!/usr/bin/env python3
"""Write bench/deals.lisp: fixed shuffles, so every player in a benchmark gets the same cards.

    python3 bench/make_deals.py

Each shuffle lists, for positions 1-52 of the dealt deck, which card of a fresh Card.CreateDeck goes
there.  The file is committed, so runs stay comparable; change the seed only for a new deal set.
"""
import random
from pathlib import Path

SEED = 1986
COUNT = 4000

rng = random.Random(SEED)
lines = [f'(* "{COUNT} fixed shuffles from bench/make_deals.py, seed {SEED}.")', "(SETQ BM.AllDeals (QUOTE ("]
for _ in range(COUNT):
    lines.append("(" + " ".join(str(n) for n in rng.sample(range(1, 53), 52)) + ")")
lines += [")))", "STOP", ""]
(Path(__file__).resolve().parent / "deals.lisp").write_text("\n".join(lines))
