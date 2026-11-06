# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The engine: rule classes, weights, and two ways to run a class.

Rules are tried by descending weight, and among equals in the order they were written.  A rule's premises run in order,
and it fires if they all hold and its conclusion has a value.  Session.first stops at the first rule that fires.
Session.all fires every rule that holds, for rules that add up evidence.  A rule answers only for what it concludes, so
one class can hold rules that others reach through Session.derive and Session.prove, by backward chaining.
"""
from dataclasses import dataclass


class RuleFailed(Exception):
    """A phrase couldn't answer.  The rule fails, the error is noted, and the next rule is tried."""


@dataclass(frozen=True)
class Rule:
    rule_class: str
    name: str
    weight: float
    goal: str  # What it concludes.
    reason: str | None
    premises: tuple
    actions: tuple
    conclusion_constants: tuple  # The fixed values in its last action.
    locals: dict  # Each `let` name, as words, and where it is kept.
    text: object  # Its RuleText.

    def bindings(self, frame):
        """What each `let` came to, for explaining a firing."""
        return {" ".join(words): frame[slot] for words, slot in self.locals.items()}


class RuleBase:
    """Compiled rules and parameter values.  Immutable: a variant is a new RuleBase, and the rules are shared."""

    def __init__(self, rules, parameters, parameter_phrases, classes_declared, texts=(), failure=RuleFailed):
        self.rules = list(rules)
        self.parameters = dict(parameters)
        self.parameter_phrases = dict(parameter_phrases)
        self.classes_declared = dict(classes_declared)
        self.texts = list(texts)
        self.failure = failure
        self.classes = {}
        for rule in self.rules:
            self.classes.setdefault(rule.rule_class, []).append(rule)
        self._by_goal = {}
        for name, members in self.classes.items():
            members.sort(key=lambda r: -r.weight)  # Stable, so equal weights keep the order written.
            for rule in members:
                self._by_goal.setdefault((name, rule.goal), []).append(rule)

    def of(self, rule_class):
        return self.classes.get(rule_class, [])

    def answering(self, rule_class, goal):
        return self._by_goal.get((rule_class, goal), ())

    def overlay(self, add=(), remove=(), parameters=None, parameter_phrases=None, classes=None):
        """A variant.  `remove` names rules to drop from every class.  `add` is new rules, which go after the existing
        rules of equal weight, and which replace a rule of the same class and name.  `parameters` is values to change."""
        added = {(r.rule_class, r.name) for r in add}
        removed = set(remove)
        kept = [r for r in self.rules if r.name not in removed and (r.rule_class, r.name) not in added]
        phrases = {**self.parameter_phrases, **(parameter_phrases or {})}
        changes = dict(parameters or {})
        unknown = set(changes) - set(phrases)
        if unknown:
            raise ValueError(f"no such parameters: {sorted(unknown)}")
        return RuleBase(kept + list(add), {**self.parameters, **changes}, phrases,
                        {**self.classes_declared, **(classes or {})}, self.texts, self.failure)


class Session:
    """One subject using a rule base: what's been concluded, the last reason given, and what went wrong."""

    def __init__(self, rules, subject, on_fire=None):
        self.rules = rules
        self.parameters = rules.parameters
        self.subject = subject
        self.on_fire = on_fire  # Called with (rule, frame) for every firing.
        self.reason = None
        self.errors = []  # (rule name, message)
        self.known = {}
        self.current_class = None

    def attempt(self, rule):
        """Try one rule: its conclusion, or None."""
        frame = [self.subject, self] + [None] * len(rule.locals)
        try:
            for premise in rule.premises:
                if not premise(frame):
                    return None
            value = None
            for action in rule.actions:
                value = action(frame)
                if not value:
                    return None
        except self.rules.failure as error:
            self.errors.append((rule.name, str(error)))
            return None
        if self.on_fire:
            self.on_fire(rule, frame)
        if rule.reason:
            self.reason = rule.reason
        return value

    def first(self, rule_class, goal):
        """The first rule of the class that fires for this goal, and its conclusion."""
        self.current_class = rule_class
        for rule in self.rules.answering(rule_class, goal):
            value = self.attempt(rule)
            if value:
                return rule, value
        return None, None

    def all(self, rule_class, goal):
        """Fire every rule of the class that holds for this goal.  The rules that fired, in order."""
        self.current_class = rule_class
        return [rule for rule in self.rules.answering(rule_class, goal) if self.attempt(rule)]

    def derive(self, goal):
        """What's known of this goal, or else what the first rule of the current class to conclude it says."""
        value = self.known.get(goal)
        if value is None:
            for rule in self.rules.answering(self.current_class, goal):
                value = self.attempt(rule)
                if value:
                    self.known[goal] = value
                    return value
            return None
        return value

    def prove(self, goal):
        return bool(self.derive(goal))

    def forget(self, goal):
        self.known.pop(goal, None)
