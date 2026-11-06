# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The self-play network, reading the same weights as Medley's NNPLAYER (dist/HEARTSNET)."""
from pathlib import Path

import numpy as np

from hearts import DECK

from .base import Player, Thought
from .network_features import SCALED, SIZE, encode

SHAPES = [(256, 512), (256, 256), (52, 256)]
WEIGHTS = Path(__file__).parent / "data" / "HEARTSNET"


class Weights:
    def __init__(self, path=WEIGHTS):
        raw = np.frombuffer(Path(path).read_bytes(), dtype=">f4").astype(np.float32)
        self.layers, at = [], 0
        for rows, columns in SHAPES:
            weights = raw[at:at + rows * columns].reshape(rows, columns)
            at += rows * columns
            bias = raw[at:at + rows]
            at += rows
            self.layers.append((weights, bias))
        assert at == raw.size, "unexpected size for the network file"

    def scores(self, x):
        values = np.zeros(SIZE, dtype=np.float32)
        for index, value in x.items():
            values[index] = value * SCALED.get(index, 1)
        for weights, bias in self.layers[:2]:
            values = np.maximum(0, weights @ values + bias)
        weights, bias = self.layers[2]
        return weights @ values + bias

    def shares(self, request, selected=()):
        x, legal = encode(request, selected)
        scores = self.scores(x)[legal]
        weights = np.exp(scores - scores.max())
        return {DECK[i]: float(w) for i, w in zip(legal, weights / weights.sum())}


_shared = None


def shared_weights():
    global _shared
    if _shared is None:
        _shared = Weights()
    return _shared


class Network(Player):
    kind = "network"
    label = "Neural network"

    def __init__(self, name=None, weights=None):
        super().__init__(name)
        self.weights = weights or shared_weights()

    def pass_out(self, view):
        if not view["direction"]:
            return []
        selected = []
        for _ in range(3):
            shares = self.weights.shares(view, selected)
            selected.append(max(shares, key=shares.get))
        self.thought = Thought(text="Its preference among the cards. It gives no reasons.")
        return selected

    def play(self, view):
        shares = self.weights.shares(view)
        card = max(shares, key=shares.get)
        self.thought = Thought(text="Its preference among the cards. It gives no reasons.",
                               shares={c: round(s, 3) for c, s in shares.items()})
        return card
