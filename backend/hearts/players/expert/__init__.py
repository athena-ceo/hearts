# Copyright (c) 2026 Athena Decision Systems SAS.
"""The 1986 Expert in Python.  Its rules are text, in expert.rules, in the language of the rulebook package, and the
phrases they can use are in vocabulary.py."""
from .player import Expert
from .rulebase import RULES_1986, variant

__all__ = ["Expert", "RULES_1986", "variant"]
