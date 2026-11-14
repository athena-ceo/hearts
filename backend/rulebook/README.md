<!-- Copyright (c) 2026 Athena Decision Systems SAS. -->
# rulebook

A small business rules kernel: rules as text that people can read, change and review. It has no dependencies, and
nothing in it knows about any domain. It lives here until a second real user needs it in its own repository.

HEARTS is its proof. The 97 rules of the 1986 Expert are in
[`hearts/players/expert/expert.rules`](../hearts/players/expert/expert.rules), and played against Medley's traces on 6,000
deals they give the same cards, passes, reasons and scores, with the same 1,282,913 rule firings in the same order.

## A rule

```
rule follow.last.must.win in follow.play weight 110
  reason "Playing last; must win trick; will play high."
  when
    the trick has 3 cards
    my legal cards in the lead suit lower than the trick's highest card are empty
    let the nice cards be my legal cards except the queen
  then play the lowest card equivalent to the highest of the nice cards among the nice cards
```

- A rule belongs to one or more classes and has a weight. Rules are tried by descending weight, and among equals in the
  order written.
- `when` lines all have to hold, in order. `let NAME be ...` names a value for the lines after it. A line indented further
  than the one above continues it. `and`, `or`, `not` and parentheses work inside a line.
- `then` lines are conclusions. If a conclusion comes to nothing (no such card, say), the rule hasn't fired.
- `reason` says why, for whoever asks. `note` is for the people who keep the rules.
- `#` at the start of a line is a comment.

A file declares its classes and its parameters, the values someone might want to tune:

```
class follow.play: minimizing, following suit
parameter SpadeProtLen: the spade protection length = 4
```

## A vocabulary

Rules use only the phrases a domain declares. Each one is typed and backed by a Python function, so the people who write
rules never see the code, and the code can't be reached except through phrases someone chose to offer.

```python
v = Vocabulary()
v.type("card")
v.type("cards", element="card")   # Also gives: {cards} is empty, the number of {cards}, {card} is in {cards}...
v.term("the highest of {cards}", "card", lambda me, cards: max_card(cards))
v.test("{card} is higher than {card}", lambda me, a, b: higher(a, b))
v.action("play {card}", lambda me, card: card, goal="PlayCard")
v.fact("my spade protection is poor", "Poor Spades Protection")   # Backward chaining.
v.derived("the weakest suit", "suit", "WeakestSuit")              # A value worked out when asked for.
```

A rule file either compiles or is refused with every problem it has, each with its line. A phrase the vocabulary doesn't
have is refused, with the closest ones it does have. So is a type that doesn't fit, a class nobody declared, and any line
with two readings: the rule's author sees both and adds parentheses, so a rule can't mean something its author didn't see.

## Running rules

```python
rules = load("expert.rules", VOCABULARY)
session = Session(rules, subject, on_fire=lambda rule, frame: ...)
rule, value = session.first("follow.play", "PlayCard")   # The first rule to fire.
session.all("opponent.trick.evaluation", "Certainty")    # Every rule that holds.
session.reason                                           # The last reason given.
session.errors                                           # Rules that failed, and why.
rule.bindings(frame)                                     # What each `let` came to, to explain a firing.
```

Rules compile to closures, and a rule base is immutable and shared, so a session is cheap. The Expert plays about 580 deals a
second this way, on one core, where its hand-written Python functions played about 780.

## Governing rules

Rules are text in git, so history, review and rollback are git's. These add what a line diff can't say:

```bash
python -m rulebook check FILE --vocabulary MODULE:NAME [--base FILE]   # Does it all read?
python -m rulebook list FILE --vocabulary MODULE:NAME [--base FILE]    # What runs in what order?
python -m rulebook diff OLD NEW                                        # What changed, whatever the layout or order?
python -m rulebook phrases --vocabulary MODULE:NAME                    # All a rule may say, for a person or a model.
```

`coverage(rulebase, fired)` lists the rules that never fired over a corpus, which is how the dead rules in the 1986 listing
show up. See `scripts/rule_coverage.py`.

A variant is a file that says only what differs, and it can be tried for one seat without touching the original:

```
remove rule sfol.little.over
parameter SpadeProtLen = 5

rule sr.first.high in shoot.follow weight 110
  reason "SR - shooting, taking the first trick."
  when the trick number is 1
  then play the highest of my legal cards
```

## Not here yet

Versions and approvals as data, effective dates, decision tables, a rule editor, forward chaining with a working memory.
