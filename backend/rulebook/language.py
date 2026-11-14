# Copyright (c) 2026 Athena Decision Systems SAS.
"""The rule file format: what a file says, before any vocabulary gives its phrases a meaning.

    # A comment, on a line of its own.
    class loan.review: what to do with an application

    parameter MaxDebtRatio: the highest debt ratio = 0.4

    rule too.much.debt in loan.review, loan.renewal weight 100
      reason "The debts are too high for this income."
      note "Credit committee, March."
      when
        let the ratio be the debts of the applicant over the income of the applicant
        the ratio is above the highest debt ratio
      then refuse the application

A `when` holds if each of its lines does, in order.  A line indented further than the one above continues it.  A short
`when` or `then` can have its one line on the same line.  A file that varies another adds:

    remove rule too.much.debt
    parameter MaxDebtRatio = 0.5
"""
import re
from dataclasses import dataclass, field

_HEADER = re.compile(r"rule\s+(\S+)\s+in\s+(.+?)\s+weight\s+(-?\d+(?:\.\d+)?)$")
_PARAMETER = re.compile(r"parameter\s+(\w+)\s*(?::\s*(.+?)\s*)?=\s*(\S+)$")
_CLASS = re.compile(r"class\s+(\S+?)\s*(?::\s*(.*))?$")
_REMOVE = re.compile(r"remove\s+rule\s+(\S+)$")
_QUOTED = re.compile(r'(reason|note)\s+"([^"]*)"$')


class RuleSyntaxError(Exception):
    def __init__(self, line, message):
        super().__init__(f"line {line}: {message}")
        self.line, self.message = line, message


def number(text):
    value = float(text)
    return int(value) if value == int(value) and "." not in text else value


@dataclass(frozen=True)
class RuleText:
    """One rule as written.  Lines are normalized for spacing, so a reformatted rule compares as the same rule."""
    name: str
    classes: tuple
    weight: float
    reason: str | None
    note: str | None
    when: tuple
    then: tuple
    line: int


@dataclass(frozen=True)
class ParameterText:
    key: str
    phrase: str | None  # None: this file changes a value that another declares.
    value: object
    line: int


@dataclass
class RuleFile:
    classes: dict = field(default_factory=dict)
    parameters: list = field(default_factory=list)
    rules: list = field(default_factory=list)
    removed: list = field(default_factory=list)
    errors: list = field(default_factory=list)


def _lines(text):
    for number_, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped and not stripped.startswith("#"):
            yield number_, len(raw) - len(raw.lstrip()), " ".join(stripped.split())


class _Open:
    """A rule still being read."""

    def __init__(self, line, name, classes, weight):
        self.line, self.name, self.classes, self.weight = line, name, classes, weight
        self.reason = self.note = None
        self.when, self.then = [], []
        self.block = None  # The list being added to.
        self.block_indent = None
        self.keyword_indent = None

    def close(self):
        return RuleText(self.name, self.classes, self.weight, self.reason, self.note, tuple(self.when), tuple(self.then),
                        self.line)


def parse(text):
    """The RuleFile in this text.  Errors are collected in its `errors`, so that a check reports all of them at once."""
    result = RuleFile()
    current = None

    def finish():
        nonlocal current
        if current:
            if not current.then:
                result.errors.append(RuleSyntaxError(current.line, f"rule {current.name} has no `then`"))
            else:
                result.rules.append(current.close())
            current = None

    for line, indent, content in _lines(text):
        if indent == 0:
            finish()
            if match := _HEADER.match(content):
                name, classes, weight = match.groups()
                current = _Open(line, name, tuple(c.strip() for c in classes.split(",")), number(weight))
            elif match := _PARAMETER.match(content):
                key, phrase, value = match.groups()
                try:
                    result.parameters.append(ParameterText(key, phrase, number(value), line))
                except ValueError:
                    result.errors.append(RuleSyntaxError(line, f"parameter {key}: {value} is not a number"))
            elif match := _CLASS.match(content):
                result.classes[match.group(1)] = match.group(2) or ""
            elif match := _REMOVE.match(content):
                result.removed.append(match.group(1))
            else:
                result.errors.append(RuleSyntaxError(line, f"expected a rule, class, parameter or remove: {content}"))
            continue
        if current is None:
            result.errors.append(RuleSyntaxError(line, f"this line is indented but no rule is open: {content}"))
            continue
        if match := _QUOTED.match(content):
            setattr(current, match.group(1), match.group(2))
            current.block = None
            continue
        word, _, rest = content.partition(" ")
        if word in ("when", "then"):
            current.block = current.when if word == "when" else current.then
            current.keyword_indent = indent
            current.block_indent = None
            if rest:
                current.block.append(rest)
                current.block_indent = indent  # Anything deeper continues this line.
            continue
        if current.block is None:
            result.errors.append(RuleSyntaxError(line, f"expected reason, note, when or then: {content}"))
        elif current.block_indent is None:
            current.block_indent = indent
            current.block.append(content)
        elif indent > current.block_indent:
            current.block[-1] += " " + content
        else:
            current.block.append(content)
    finish()
    return result
