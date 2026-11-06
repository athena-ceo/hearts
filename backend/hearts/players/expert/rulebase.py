# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The knowledge base as it runs in Medley, and the variants of it.  Variants of the rules are .rules files in variants/."""
from pathlib import Path

from rulebook import load

from ..cardlib import RuleError
from .vocabulary import POOR_SPADES, VOCABULARY, WEAKEST_SUIT

HERE = Path(__file__).resolve().parent
RULES_1986 = load(HERE / "expert.rules", VOCABULARY, failure=RuleError)

# The strategies: which rule class each asks, for passing, and for playing in each mode.
STRATEGIES = {
    "Minimizing": {"pass": "minimizing.passout", "Lead": "lead.play", "FollowSuit": "follow.play", "Dump": "dump.play"},
    "Shooting": {"pass": "shooting.passout", "Lead": "shoot.lead", "FollowSuit": "shoot.follow", "Dump": "shoot.dump"},
    "Eclipsing": {"Lead": "eclipse.lead", "FollowSuit": "eclipse.follow", "Dump": "eclipse.dump"},
}


def variant(name_or_path):
    """A variant of the 1986 rules, from variants/NAME.rules or a path."""
    path = Path(name_or_path)
    if not path.suffix:
        path = HERE / "variants" / f"{name_or_path}.rules"
    return load(path, VOCABULARY, RULES_1986)


__all__ = ["POOR_SPADES", "RULES_1986", "STRATEGIES", "VOCABULARY", "WEAKEST_SUIT", "variant"]
