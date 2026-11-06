# Copyright (c) 2026 Athena Decisions Systems SAS.
"""A small business rules kernel: rules as text that people can read, change and review.

A domain supplies a Vocabulary, the phrases its rules may use, each typed and backed by a Python function.  Rules live in
text files, and load() compiles them against the vocabulary, refusing anything it can't read, or could read two ways.
A Session runs them.  It knows nothing of any domain.  See README.md.
"""
from .compiler import RuleFileError, load, load_text
from .engine import Rule, RuleBase, RuleFailed, Session
from .language import parse
from .tools import coverage, diff, listing, phrases
from .vocabulary import Vocabulary

__all__ = ["Rule", "RuleBase", "RuleFailed", "RuleFileError", "Session", "Vocabulary", "coverage", "diff", "listing",
           "load", "load_text", "parse", "phrases"]
