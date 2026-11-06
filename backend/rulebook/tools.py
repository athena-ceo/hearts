# Copyright (c) 2026 Athena Decisions Systems SAS.
"""For the people who govern the rules: what changed, what runs in what order, what never fires, and what can be said."""
from .language import RuleFile
from .vocabulary import Slot


def _fields(rule):
    return {"classes": ", ".join(rule.classes), "weight": rule.weight, "reason": rule.reason, "note": rule.note,
            "when": list(rule.when), "then": list(rule.then)}


def diff(old: RuleFile, new: RuleFile):
    """What changed between two rule files, as lines for a person, whatever the layout or the order of the file."""
    lines = []
    before = {r.name: r for r in old.rules}
    after = {r.name: r for r in new.rules}
    for name in sorted(after.keys() - before.keys()):
        lines.append(f"added rule {name}, in {', '.join(after[name].classes)}, weight {after[name].weight}")
    for name in sorted(before.keys() - after.keys()):
        lines.append(f"removed rule {name}, from {', '.join(before[name].classes)}")
    for name in sorted(before.keys() & after.keys()):
        a, b = _fields(before[name]), _fields(after[name])
        for field, value in a.items():
            if value != b[field]:
                lines.append(f"changed rule {name}: {field}: {value} -> {b[field]}")
    values_before = {p.key: p.value for p in old.parameters}
    values_after = {p.key: p.value for p in new.parameters}
    for key in sorted(values_before.keys() | values_after.keys()):
        if values_before.get(key) != values_after.get(key):
            lines.append(f"changed parameter {key}: {values_before.get(key)} -> {values_after.get(key)}")
    return lines


def listing(rulebase):
    """The rules of each class in the order they're tried, as lines."""
    lines = []
    for name, members in sorted(rulebase.classes.items()):
        lines.append(name + (f": {rulebase.classes_declared[name]}" if rulebase.classes_declared.get(name) else ""))
        lines += [f"  {rule.weight:>6}  {rule.name}" for rule in members]
    return lines


def coverage(rulebase, fired):
    """Given a count of firings by rule name: the rules that never fired, by class, for a corpus you trust."""
    return {name: [r.name for r in members if not fired.get(r.name)] for name, members in sorted(rulebase.classes.items())}


def phrases(vocabulary):
    """Everything a rule may say, by what it is, for a rule author, whether a person or a model."""
    def show(phrase):
        return " ".join(f"{{{w.type}}}" if isinstance(w, Slot) else w for w in phrase.words)

    groups = {}
    for phrase in vocabulary.phrases:
        groups.setdefault(phrase.returns, []).append(show(phrase))
    lines = []
    for name in sorted(groups):
        lines.append(f"{name}:")
        lines += [f"  {text}" for text in sorted(groups[name])]
    constants = {}
    for words, (_, type_) in vocabulary.constants.items():
        constants.setdefault(type_, []).append(" ".join(words))
    for name in sorted(constants):
        lines.append(f"{name} constants: {', '.join(sorted(constants[name]))}")
    return lines
