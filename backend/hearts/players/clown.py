# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The Clown: passes three random cards and plays a random legal card."""
import random

from .base import Player, Thought


class Clown(Player):
    kind = "clown"
    label = "Clown"

    def __init__(self, name=None, seed=None):
        super().__init__(name)
        self.rng = random.Random(seed)

    def pass_out(self, view):
        return self.rng.sample(view["hand"], 3) if view["direction"] else []

    def play(self, view):
        self.thought = Thought(text="Any legal card will do.")
        return self.rng.choice(view["legal"])
