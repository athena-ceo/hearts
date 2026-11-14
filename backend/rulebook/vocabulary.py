# Copyright (c) 2026 Athena Decision Systems SAS.
"""A Vocabulary: the types of a domain, and the phrases its rules may use.

    v = Vocabulary()
    v.type("money")
    v.term("the income of {applicant}", "money", lambda subject, a: a.income)
    v.test("{applicant} is in arrears", lambda subject, a: a.arrears > 0)
    v.action("refuse the application", lambda subject: subject.refuse(), goal="Decision")

A template's words are matched as written, and {type} is a phrase of that type.  Each function is given the session's
subject and then the slots, in order.  A function that answers with nothing (None, False, an empty list) makes a premise
fail, or a conclusion not hold.  A function that can't answer raises RuleFailed: the rule fails, the error is noted, and
the next rule is tried.
"""
from dataclasses import dataclass

BOOL, NUMBER, ACTION = "bool", "number", "action"


@dataclass(frozen=True)
class Slot:
    type: str


@dataclass(frozen=True)
class Phrase:
    template: str
    words: tuple  # Each a word or a Slot.
    returns: str
    function: object
    goal: str | None = None
    uses_session: bool = False  # Its function takes the session in place of the subject.


def _is(_, a, b):
    return a == b


def _is_not(_, a, b):
    return a != b


def _exists(_, a):
    return bool(a)


def _no(_, a):
    return not a


class Vocabulary:
    def __init__(self):
        self.parents = {BOOL: (), NUMBER: (), ACTION: ()}
        self.phrases = []
        self.constants = {}  # Tuple of words -> (value, type).
        self.synonyms = {"are": "is"}
        self.term(f"{{{NUMBER}}} is {{{NUMBER}}}", BOOL, _is)
        self.test(f"{{{NUMBER}}} is not {{{NUMBER}}}", _is_not)
        self.test(f"{{{NUMBER}}} is above {{{NUMBER}}}", lambda _, a, b: a > b)
        self.test(f"{{{NUMBER}}} is below {{{NUMBER}}}", lambda _, a, b: a < b)
        self.test(f"{{{NUMBER}}} is at least {{{NUMBER}}}", lambda _, a, b: a >= b)
        self.test(f"{{{NUMBER}}} is at most {{{NUMBER}}}", lambda _, a, b: a <= b)

    def type(self, name, element=None, parents=(), phrases=True):
        """A type, with the phrases every type has.  A list type (`element`, the type of what's in it) also has those
        that every list has.  `parents` are the types it can stand in for, and without `phrases` it adds none."""
        self.parents[name] = tuple(parents)
        if not phrases:
            return
        slot = f"{{{name}}}"
        self.test(f"{slot} is {slot}", _is)
        self.test(f"{slot} is not {slot}", _is_not)
        if element:
            self.test(f"{slot} is empty", _no)
            self.test(f"{slot} is not empty", _exists)
            self.term(f"the number of {slot}", NUMBER, lambda _, a: len(a))
            self.test(f"{{{element}}} is in {slot}", lambda _, a, b: a in b)
            self.test(f"{{{element}}} is not in {slot}", lambda _, a, b: a not in b)
        else:
            self.test(f"{slot} exists", _exists)
            self.test(f"{slot} does not exist", _no)

    def _template(self, template):
        words = []
        for word in template.lower().split():
            if word.startswith("{") and word.endswith("}"):
                name = word[1:-1]
                if name not in self.parents:
                    raise ValueError(f"{template}: no such type: {name}")
                words.append(Slot(name))
            else:
                words.append(self.synonyms.get(word, word))
        return tuple(words)

    def term(self, template, returns, function=None, **options):
        """A phrase with a value.  Usable as a decorator."""
        if function is None:
            return lambda f: self.term(template, returns, f, **options) or f
        if returns not in self.parents:
            raise ValueError(f"{template}: no such type: {returns}")
        self.phrases.append(Phrase(template, self._template(template), returns, function, **options))

    def test(self, template, function=None):
        """A phrase that holds or doesn't, for a `when`."""
        return self.term(template, BOOL, function)

    def action(self, template, function=None, goal=None):
        """A phrase for a `then`.  `goal` is what it concludes, the thing a query asks for.  Its answer is the rule's
        conclusion, and if it answers with nothing the rule hasn't fired."""
        return self.term(template, ACTION, function, goal=goal)

    def constant(self, words, value, type_):
        self.constants[tuple(self.synonyms.get(w, w) for w in words.lower().split())] = (value, type_)

    def fact(self, phrase, goal):
        """Something a rule concludes and another asks about.  Asking looks for what's already known, and then for a rule
        of the class being run that concludes it (backward chaining)."""
        self.term(phrase, BOOL, lambda session: session.prove(goal), uses_session=True)
        self.action(f"conclude {phrase}", lambda subject: True, goal=goal)

    def derived(self, phrase, type_, goal):
        """A value worked out when first asked for, by a rule of the class being run.  `phrase is {type}` concludes it."""
        self.term(phrase, type_, lambda session: session.derive(goal), uses_session=True)
        self.action(f"{phrase} is {{{type_}}}", lambda subject, value: value, goal=goal)

    def accepts(self, slot_type, actual):
        """Can a phrase of type `actual` fill a slot of type `slot_type`?"""
        return actual == slot_type or any(self.accepts(slot_type, p) for p in self.parents.get(actual, ()))
