# Copyright (c) 2026 Athena Decision Systems SAS.
"""The players, each answering the six messages of the 1986 protocol.  See base.py."""
from .base import Player, Thought
from .clown import Clown
from .conservative import Conservative
from .expert import Expert
from .network import Network

BOT_KINDS = {cls.kind: cls for cls in (Expert, Conservative, Network, Clown)}


def make_bot(kind, name=None, seed=None):
    """A new automated player of this kind.  Only the kinds with a random choice take the seed."""
    cls = BOT_KINDS[kind]
    return cls(name, seed=seed) if kind in ("clown", "conservative") else cls(name)


__all__ = ["BOT_KINDS", "Player", "Thought", "Clown", "Conservative", "Expert", "Network", "make_bot"]
