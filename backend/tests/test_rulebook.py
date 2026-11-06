# Copyright (c) 2026 Athena Decisions Systems SAS.
"""The rulebook kernel, on a domain that isn't cards: a small loan desk."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

from rulebook import RuleFailed, RuleFileError, Session, Vocabulary, coverage, diff, listing, load_text, parse, phrases
from rulebook.__main__ import main

RULEBOOK = Path(__file__).resolve().parents[1] / "rulebook"


def vocabulary():
    v = Vocabulary()
    v.type("applicant")
    v.type("name")
    v.type("names", element="name")
    v.constant("gold", "gold", "name")
    v.constant("basic", "basic", "name")
    v.term("the applicant", "applicant", lambda me: me.applicant)
    v.term("the income of {applicant}", "number", lambda me, a: a.income)
    v.term("the debts of {applicant}", "number", lambda me, a: a.debts)
    v.term("the tiers of {applicant}", "names", lambda me, a: a.tiers)

    @v.term("{number} over {number}", "number")
    def over(me, a, b):
        if b == 0:
            raise RuleFailed("no income")
        return a / b

    v.action("refuse the application", lambda me: me.decide("refused"), goal="Decision")
    v.action("approve the application", lambda me: me.decide("approved"), goal="Decision")
    v.action("note the risk at {number}", lambda me, x: me.score.append(x) or True, goal="Risk")
    v.fact("the applicant is reliable", "Reliable")
    v.derived("the tier", "name", "Tier")
    return v


RULES = """
# The desk.
class loan.review: what to do with an application
class loan.risk: what makes an application risky

parameter MaxDebtRatio: the highest debt ratio = 0.4

rule too.much.debt in loan.review weight 100
  reason "The debts are too high."
  note "Credit committee."
  when
    let the ratio be the debts of the applicant over the income of the applicant
    the ratio is above the highest debt ratio
  then refuse the application

rule gold.tier in loan.review weight 90
  reason "A gold customer."
  when the tier is gold
  then approve the application

rule reliable in loan.review weight 80
  when
    the number of the tiers of the applicant is at least 2
  then conclude the applicant is reliable

rule approve.reliable in loan.review weight 70
  reason "Reliable."
  when the applicant is reliable
  then approve the application

rule work.out.tier in loan.review weight 60
  when gold is in the tiers of the applicant
  then the tier is gold

rule fallback in loan.review weight 0
  reason "Nothing else applied."
  then refuse the application

rule high in loan.risk weight 10
  when the debts of the applicant are at least 100
  then note the risk at 0.5

rule any in loan.risk weight 5
  then note the risk at 0.1
"""


class Desk:
    def __init__(self, income=100, debts=0, tiers=()):
        self.applicant = SimpleNamespace(income=income, debts=debts, tiers=list(tiers))
        self.score = []

    def decide(self, decision):
        return decision


def run(desk, rules=None):
    session = Session(rules or load_text(RULES, vocabulary()), desk)
    return session, session.first("loan.review", "Decision")


def test_the_first_rule_to_fire_by_weight_decides_and_gives_its_reason():
    session, (rule, value) = run(Desk(debts=50))
    assert (rule.name, value, session.reason) == ("too.much.debt", "refused", "The debts are too high.")
    session, (rule, value) = run(Desk())
    assert (rule.name, value, session.reason) == ("fallback", "refused", "Nothing else applied.")


def test_a_rule_that_fails_is_noted_and_the_next_is_tried():
    session, (rule, _) = run(Desk(income=0))
    assert session.errors == [("too.much.debt", "no income")]
    assert rule.name == "fallback"


def test_backward_chaining_reaches_rules_that_conclude_what_a_premise_asks():
    fired = []
    session = Session(load_text(RULES, vocabulary()), Desk(tiers=["gold"]), lambda rule, frame: fired.append(rule.name))
    rule, value = session.first("loan.review", "Decision")
    assert (rule.name, value) == ("gold.tier", "approved")
    assert fired == ["work.out.tier", "gold.tier"]  # The chained rule first.
    assert session.derive("Tier") == "gold"
    session = Session(load_text(RULES, vocabulary()), Desk(tiers=["a", "b"]))
    assert session.first("loan.review", "Decision")[0].name == "approve.reliable"
    assert session.prove("Reliable")
    session.forget("Reliable")
    assert session.known == {}


def test_a_query_for_all_fires_every_rule_that_holds():
    desk = Desk(debts=100)
    session = Session(load_text(RULES, vocabulary()), desk)
    assert [r.name for r in session.all("loan.risk", "Risk")] == ["high", "any"]
    assert desk.score == [0.5, 0.1]


def test_a_firing_can_be_explained():
    seen = {}
    session = Session(load_text(RULES, vocabulary()), Desk(debts=50),
                      lambda rule, frame: seen.update({rule.name: rule.bindings(frame)}))
    session.first("loan.review", "Decision")
    assert seen == {"too.much.debt": {"the ratio": 0.5}}


def errors_in(text, base=None):
    with pytest.raises(RuleFileError) as caught:
        load_text(text, vocabulary(), base)
    return str(caught.value)


CLASSES = "class c: a class\nparameter Limit: the limit = 1\n"


def test_a_phrase_nobody_knows_is_refused_and_it_says_where():
    message = errors_in(CLASSES + "rule r in c weight 1\n  when the incme of the applicant is above 1\n  then refuse the application\n")
    assert "line 3" in message and "rule r" in message and "stuck at `incme`" in message and "the income of" in message


def test_every_problem_in_a_file_is_reported_at_once():
    message = errors_in(CLASSES + "rule a in c weight 1\n  when nonsense\n  then refuse the application\n"
                        "rule b in nowhere weight 1\n  then refuse the application\n"
                        "rule d in c weight 1\n  when 1 is above 0\n"
                        "something else\n")
    assert "rule a" in message and "no such class: nowhere" in message and "rule d has no `then`" in message
    assert "expected a rule, class, parameter or remove" in message


def test_types_are_checked():
    assert "can't read this" in errors_in(CLASSES + "rule r in c weight 1\n  when the income of gold is above 1\n"
                                                    "  then refuse the application\n")


def test_a_line_with_two_readings_is_refused_until_parentheses_settle_it():
    ambiguous = CLASSES + ("rule r in c weight 1\n  when 8 over 4 over 2 is at least 1\n  then refuse the application\n")
    message = errors_in(ambiguous)
    assert "more than one way" in message and "[[8] over [4]] over [2]" in message and "[8] over [[4] over [2]]" in message
    settled = load_text(ambiguous.replace("8 over 4 over 2", "(8 over 4) over 2"), vocabulary())
    assert Session(settled, Desk()).first("c", "Decision")[1] == "refused"


def test_and_and_or_must_not_be_mixed_without_parentheses():
    mixed = CLASSES + "rule r in c weight 1\n  when 1 is 1 and 1 is 2 or 1 is 1\n  then refuse the application\n"
    assert "how `and` and `or` group" in errors_in(mixed)
    grouped = mixed.replace("1 is 1 and 1 is 2 or 1 is 1", "(1 is 1 and 1 is 2) or 1 is 1")
    assert Session(load_text(grouped, vocabulary()), Desk()).first("c", "Decision")[1] == "refused"
    chain = mixed.replace("1 is 1 and 1 is 2 or 1 is 1", "1 is 1 and 2 is 2 and not 1 is 2")
    assert Session(load_text(chain, vocabulary()), Desk()).first("c", "Decision")[1] == "refused"


def test_a_rule_must_conclude_one_thing():
    assert "must conclude one thing" in errors_in(CLASSES + "rule r in c weight 1\n  then\n    refuse the application\n"
                                                            "    note the risk at 1\n")


def test_a_line_continues_when_indented_further():
    rules = load_text(CLASSES + "rule r in c weight 1\n  when\n    1 is 1\n      and 2 is 2\n    3 is 3\n"
                                "  then refuse the application\n", vocabulary())
    assert rules.rules[0].text.when == ("1 is 1 and 2 is 2", "3 is 3")


def test_a_name_can_only_be_let_once():
    assert "the name `the x` is taken" in errors_in(CLASSES + "rule r in c weight 1\n  when\n    let the x be 1\n"
                                                              "    let the x be 2\n  then refuse the application\n")


VARIANT = """
remove rule too.much.debt
parameter MaxDebtRatio = 0.9

rule kinder in loan.review weight 100
  reason "Kinder."
  when
    let the ratio be the debts of the applicant over the income of the applicant
    the ratio is above the highest debt ratio
  then refuse the application

rule fallback in loan.review weight 0
  reason "Nothing else; say yes."
  then approve the application
"""


def test_a_variant_adds_replaces_removes_and_changes_parameters_and_leaves_its_base_alone():
    base = load_text(RULES, vocabulary())
    changed = load_text(VARIANT, vocabulary(), base)
    assert base.parameters["MaxDebtRatio"] == 0.4 and changed.parameters["MaxDebtRatio"] == 0.9
    assert "too.much.debt" in [r.name for r in base.rules] and "too.much.debt" not in [r.name for r in changed.rules]
    assert run(Desk(debts=50), base)[1][1] == "refused"
    assert run(Desk(debts=50), changed)[1][1] == "approved"  # Parameter and replaced fallback.
    assert run(Desk(debts=95), changed)[1][0].name == "kinder"


def test_a_variant_cant_remove_or_change_what_isnt_there():
    base = load_text(RULES, vocabulary())
    assert "no such rule: nope" in errors_in("remove rule nope\n", base)
    assert "no such parameter: Nope" in errors_in("parameter Nope = 1\n", base)
    assert "only makes sense in a variant" in errors_in("remove rule x\n")


def test_diff_sees_what_changed_and_not_how_it_was_laid_out():
    old = parse(RULES)
    reformatted = RULES.replace("  when the debts of the applicant are at least 100", "  when\n     the  debts of the applicant   are at least 100")
    assert diff(old, parse(reformatted)) == []
    new = parse(RULES.replace("= 0.4", "= 0.5").replace("weight 90", "weight 95").replace('"A gold customer."', '"Gold."')
                .replace("rule any in loan.risk weight 5\n  then note the risk at 0.1\n", "rule other in loan.risk weight 5\n  then note the risk at 0.2\n"))
    assert diff(old, new) == [
        "added rule other, in loan.risk, weight 5",
        "removed rule any, from loan.risk",
        "changed rule gold.tier: weight: 90 -> 95",
        "changed rule gold.tier: reason: A gold customer. -> Gold.",
        "changed parameter MaxDebtRatio: 0.4 -> 0.5"]


def test_listing_coverage_and_phrases():
    rules = load_text(RULES, vocabulary())
    lines = listing(rules)
    assert lines[0] == "loan.review: what to do with an application"
    assert lines.index("     100  too.much.debt") < lines.index("       0  fallback")
    assert coverage(rules, {"high": 3, "any": 1})["loan.risk"] == []
    assert "fallback" in coverage(rules, {})["loan.review"]
    assert "  the income of {applicant}" in phrases(vocabulary())


def test_the_command(tmp_path, capsys):
    good, bad = tmp_path / "good.rules", tmp_path / "bad.rules"
    good.write_text(RULES)
    bad.write_text(RULES.replace("= 0.4", "= 0.5"))
    assert main(["diff", str(good), str(bad)]) == 0
    assert "changed parameter MaxDebtRatio: 0.4 -> 0.5" in capsys.readouterr().out
    assert main(["diff", str(good), str(good)]) == 0
    assert "no change" in capsys.readouterr().out
    hearts = "hearts.players.expert.vocabulary:VOCABULARY"
    assert main(["phrases", "--vocabulary", hearts]) == 0
    assert "  play {card}" in capsys.readouterr().out
    bad.write_text("rule r in nowhere weight 1\n  then play the queen\n")
    assert main(["check", str(bad), "--vocabulary", hearts]) == 1
    assert "no such class" in capsys.readouterr().err


def test_the_kernel_imports_nothing_of_any_domain():
    allowed = {"argparse", "dataclasses", "difflib", "importlib", "pathlib", "re", "sys"}
    for path in RULEBOOK.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert {a.name.split(".")[0] for a in node.names} <= allowed, path
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                assert node.module.split(".")[0] in allowed, path
