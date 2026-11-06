# Copyright (c) 2026 Athena Decisions Systems SAS.
"""Reading a rule's phrases with a vocabulary, and compiling them to Python closures.

A line is read by trying every phrase in the vocabulary at every position, as a chart parser does, with types deciding
which readings make sense.  The reading must be unique, so a rule can't mean something its author didn't see: a line
with two readings is refused and shows both, and parentheses settle it.  Likewise `a and b or c` needs parentheses.
"""
import difflib
import re
from pathlib import Path

from .engine import Rule, RuleBase, RuleFailed
from .language import RuleSyntaxError, RuleText, parse
from .vocabulary import ACTION, BOOL, NUMBER, Slot

_TOKEN = re.compile(r'\(|\)|-?\d+(?:\.\d+)?(?![^\s()])|[^\s()]+')
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?$")


class RuleFileError(Exception):
    """All that is wrong with a rule file, one line each."""

    def __init__(self, errors, path=None):
        where = f"{path}: " if path else ""
        super().__init__("\n".join(where + str(e) for e in errors))
        self.errors = errors


class Node:
    __slots__ = ("type", "kind", "value", "args", "goal", "grouped")

    def __init__(self, type_, kind, value=None, args=(), goal=None):
        self.type, self.kind, self.value, self.args, self.goal = type_, kind, value, tuple(args), goal
        self.grouped = False

    def show(self):
        """The reading, with its grouping, for error messages."""
        if self.kind == "phrase":
            args = iter(self.args)
            return " ".join(f"[{next(args).show()}]" if isinstance(w, Slot) else w for w in self.value.words)
        if self.kind in ("and", "or"):
            return f" {self.kind} ".join(f"[{a.show()}]" for a in self.args)
        if self.kind == "not":
            return f"not [{self.args[0].show()}]"
        return " ".join(self.value) if isinstance(self.value, tuple) else str(self.value)

    def key(self):
        return (self.kind, id(self.value) if self.kind == "phrase" else self.value, tuple(a.key() for a in self.args))

    def constants(self):
        """The fixed values among its arguments."""
        return tuple(a.value for a in self.args if a.kind == "constant")


class _Reader:
    """All the readings of one line."""

    def __init__(self, vocabulary, prefix, infix, names, tokens):
        self.vocabulary, self.prefix, self.infix, self.names, self.tokens = vocabulary, prefix, infix, names, tokens
        self.memo = {}
        self.farthest = 0
        self.mixed = False

    def read(self, i):
        """Every (node, end) of a phrase that starts at token i."""
        if i in self.memo:
            return self.memo[i]
        self.memo[i] = found = {}
        tokens = self.tokens
        if i >= len(tokens):
            return found
        self.farthest = max(self.farthest, i)
        token = tokens[i]

        def add(node, end):
            key = (node.key(), end)
            if key in found:
                return False
            found[key] = (node, end)
            self.farthest = max(self.farthest, end)
            return True

        if token == "(":
            for node, end in list(self.read(i + 1).values()):
                if end < len(tokens) and tokens[end] == ")":
                    group = Node(node.type, node.kind, node.value, node.args, node.goal)
                    group.grouped = True
                    add(group, end + 1)
        elif _NUMBER.match(token):
            add(Node(NUMBER, "constant", float(token) if "." in token else int(token)), i + 1)
        elif token == "not":
            for node, end in list(self.read(i + 1).values()):
                if node.type == BOOL and (node.grouped or node.kind not in ("and", "or")):
                    add(Node(BOOL, "not", args=[node]), end)
        for words, (value, type_) in self.vocabulary.constants.items():
            if tuple(tokens[i:i + len(words)]) == words:
                add(Node(type_, "constant", value), i + len(words))
        for words, (kind, type_, value) in self.names.items():
            if tuple(tokens[i:i + len(words)]) == words:
                add(Node(type_, kind, value), i + len(words))
        for phrase in self.prefix.get(token, ()):
            self.farthest = max(self.farthest, i + 1)
            for args, end in self._match(phrase, 1, i + 1, ()):
                add(Node(phrase.returns, "phrase", phrase, args, phrase.goal), end)
        queue = list(found.values())
        while queue:  # Grow each reading with the phrases that begin with a slot.
            node, end = queue.pop()
            for phrase in self.infix:
                if self.vocabulary.accepts(phrase.words[0].type, node.type):
                    for args, stop in self._match(phrase, 1, end, (node,)):
                        new = Node(phrase.returns, "phrase", phrase, args, phrase.goal)
                        if add(new, stop):
                            queue.append((new, stop))
            if node.type == BOOL and end < len(tokens) and tokens[end] in ("and", "or"):
                connective = tokens[end]
                for right, stop in list(self.read(end + 1).values()):
                    if right.type != BOOL or (right.kind in ("and", "or") and not right.grouped):
                        continue
                    if node.kind in ("and", "or") and not node.grouped:
                        if node.kind != connective:
                            self.mixed = True
                            continue
                        new = Node(BOOL, connective, args=(*node.args, right))
                    else:
                        new = Node(BOOL, connective, args=(node, right))
                    if add(new, stop):
                        queue.append((new, stop))
        return found

    def _match(self, phrase, k, position, args):
        words = phrase.words
        if k == len(words):
            yield args, position
            return
        word = words[k]
        if isinstance(word, Slot):
            for node, end in list(self.read(position).values()):
                if self.vocabulary.accepts(word.type, node.type):
                    yield from self._match(phrase, k + 1, end, (*args, node))
        elif position < len(self.tokens) and self.tokens[position] == word:
            self.farthest = max(self.farthest, position + 1)
            yield from self._match(phrase, k + 1, position + 1, args)


class Compiler:
    def __init__(self, vocabulary, parameters=()):
        """`parameters` are (key, phrase) pairs that the rules can read."""
        self.vocabulary = vocabulary
        self.prefix = {}
        self.infix = []
        for phrase in vocabulary.phrases:
            if isinstance(phrase.words[0], Slot):
                self.infix.append(phrase)
            else:
                self.prefix.setdefault(phrase.words[0], []).append(phrase)
        self.parameters = {}
        for key, words in parameters:
            self.add_parameter(key, words)

    def tokens(self, text):
        synonyms = self.vocabulary.synonyms
        return [synonyms.get(t, t) for t in (t.lower() for t in _TOKEN.findall(text))]

    def add_parameter(self, key, phrase):
        self.parameters[tuple(self.tokens(phrase))] = ("parameter", NUMBER, key)

    def read(self, text, want, names):
        """The one reading of this text as a `want`, or a ValueError that says what's wrong."""
        tokens = self.tokens(text)
        reader = _Reader(self.vocabulary, self.prefix, self.infix, {**self.parameters, **names}, tokens)
        complete = [n for n, end in reader.read(0).values() if end == len(tokens) and self.vocabulary.accepts(want, n.type)]
        if len(complete) == 1:
            return complete[0]
        if complete:
            readings = "\n    ".join(n.show() for n in complete)
            raise ValueError(f"this can be read more than one way, so use parentheses: {text}\n    {readings}")
        if reader.mixed:
            raise ValueError(f"use parentheses to say how `and` and `or` group: {text}")
        word = tokens[reader.farthest] if reader.farthest < len(tokens) else "the end of the line"
        hint = difflib.get_close_matches(text.lower(), [p.template for p in self.vocabulary.phrases], n=3, cutoff=0.5)
        hint = f" Closest phrases: {'; '.join(hint)}." if hint else ""
        kind = "a conclusion" if want == ACTION else "a condition" if want == BOOL else want
        raise ValueError(f"can't read this as {kind}, stuck at `{word}`: {text}.{hint}")

    def rule(self, text, rule_class, classes):
        """A Rule of this class, from its text."""
        if rule_class not in classes:
            raise ValueError(f"rule {text.name}: no such class: {rule_class}")
        names = {}
        premises = []
        for line in text.when:
            if line.startswith("let "):
                head, separator, expression = line[4:].partition(" be ")
                if not separator:
                    raise ValueError(f"rule {text.name}: expected `let NAME be ...`: {line}")
                node = self._line(text, expression, None, names)
                slot = 2 + sum(1 for n in names.values() if n[0] == "local")
                words = tuple(self.tokens(head))
                if words in names or words in self.parameters or words in self.vocabulary.constants:
                    raise ValueError(f"rule {text.name}: the name `{head}` is taken")
                names[words] = ("local", node.type, slot)
                premises.append(_let(slot, _compile(node)))
            else:
                premises.append(_compile(self._line(text, line, BOOL, names)))
        actions = [self._line(text, line, ACTION, names) for line in text.then]
        goals = {a.goal for a in actions if a.goal}
        if len(goals) != 1:
            raise ValueError(f"rule {text.name}: a rule must conclude one thing, and this concludes {sorted(goals) or 'nothing'}")
        locals_ = {words: value[2] for words, value in names.items() if value[0] == "local"}
        return Rule(rule_class, text.name, text.weight, goals.pop(), text.reason, tuple(premises),
                    tuple(_compile(a) for a in actions), actions[-1].constants(), locals_, text)

    def _line(self, text, line, want, names):
        if want is not None:
            try:
                return self.read(line, want, names)
            except ValueError as error:
                raise ValueError(f"rule {text.name}: {error}") from None
        tokens = self.tokens(line)
        reader = _Reader(self.vocabulary, self.prefix, self.infix, {**self.parameters, **names}, tokens)
        complete = [n for n, end in reader.read(0).values() if end == len(tokens)]
        if len(complete) == 1:
            return complete[0]
        problem = "has more than one reading" if complete else "can't be read"
        raise ValueError(f"rule {text.name}: this `let` {problem}: {line}")


def _let(slot, value):
    def let(frame):
        frame[slot] = value(frame)
        return True
    return let


def _compile(node):
    kind = node.kind
    if kind == "constant":
        value = node.value
        return lambda frame: value
    if kind == "local":
        slot = node.value
        return lambda frame: frame[slot]
    if kind == "parameter":
        key = node.value
        return lambda frame: frame[1].parameters[key]
    args = [_compile(a) for a in node.args]
    if kind == "not":
        inner = args[0]
        return lambda frame: not inner(frame)
    if kind == "and":
        def all_of(frame):
            for arg in args:
                if not arg(frame):
                    return False
            return True
        return all_of
    if kind == "or":
        def any_of(frame):
            for arg in args:
                if arg(frame):
                    return True
            return False
        return any_of
    phrase = node.value
    function = phrase.function
    who = 1 if phrase.uses_session else 0
    if len(args) == 0:
        return lambda frame: function(frame[who])
    if len(args) == 1:
        a = args[0]
        return lambda frame: function(frame[who], a(frame))
    if len(args) == 2:
        a, b = args
        return lambda frame: function(frame[who], a(frame), b(frame))
    return lambda frame: function(frame[who], *[arg(frame) for arg in args])


def _build(source, vocabulary, base=None):
    """Compile a parsed file: on its own, or as a variant of `base`."""
    errors = list(source.errors)
    classes = {**(base.classes_declared if base else {}), **source.classes}
    values = dict(base.parameters) if base else {}
    declared = dict(base.parameter_phrases) if base else {}
    for parameter in source.parameters:
        if parameter.phrase:
            declared[parameter.key] = parameter.phrase
        elif parameter.key not in declared:
            errors.append(RuleSyntaxError(parameter.line, f"no such parameter: {parameter.key}"))
            continue
        values[parameter.key] = parameter.value
    compiler = Compiler(vocabulary, declared.items())
    rules = []
    seen = set()
    for text in source.rules:
        for rule_class in text.classes:
            if (rule_class, text.name) in seen:
                errors.append(RuleSyntaxError(text.line, f"rule {text.name} is in {rule_class} twice"))
                continue
            seen.add((rule_class, text.name))
            try:
                rules.append(compiler.rule(text, rule_class, classes))
            except ValueError as error:
                errors.append(RuleSyntaxError(text.line, str(error)))
    if base:
        for name in source.removed:
            if not any(r.name == name for r in base.rules):
                errors.append(RuleSyntaxError(0, f"remove: no such rule: {name}"))
    return rules, values, declared, classes, errors


def load_text(text, vocabulary, base=None, failure=RuleFailed, path=None):
    """A RuleBase from rule text.  With `base`, the text is a variant of it (see RuleBase.overlay).  Raises RuleFileError
    with everything that's wrong."""
    source = parse(text)
    rules, values, declared, classes, errors = _build(source, vocabulary, base)
    if source.removed and not base:
        errors.append(RuleSyntaxError(0, "`remove rule` only makes sense in a variant of another rule file"))
    if errors:
        raise RuleFileError(errors, path)
    if base:
        return base.overlay(add=rules, remove=source.removed, parameters={p.key: p.value for p in source.parameters},
                            parameter_phrases=declared, classes=classes)
    return RuleBase(rules, values, declared, classes, source.rules, failure)


def load(path, vocabulary, base=None, failure=RuleFailed):
    """A RuleBase from a rule file."""
    path = Path(path)
    return load_text(path.read_text(), vocabulary, base, failure, path)
