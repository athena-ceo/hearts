#!/usr/bin/env python3
"""Generate the Medley-loadable Expert Player (Phase 2b) from the 1986 listings.

Outputs:
  dist/KEELOOPS   KEE compatibility layer on LOOPS          (from medley/keeloops.lisp)
  dist/EXPERT     the Expert Player: reconstructed KB (medley/expert-kb.lisp)
                  + the ORIGINAL EP.* code (transcription/kee-expert-player.txt)
                  + the ORIGINAL rules as data (transcription/kee-expert-rules.txt, plus
                    the rules page that was bound into the EXPERT listing).
                  Starts with (FILESLOAD KEELOOPS).
  medley/EXPERT   dev build: the same, with KEELOOPS inlined (one file to load).

Load order in Medley:  LOOPS, then (FILESLOAD CLIPBOARD ACTIVEREGIONS HEARTS EXPERT).

Like build-loadfile.py, the transcription stays faithful to the paper; every change
needed to run it is a labelled revival patch here (see HEARTS-BUGS.md, section K), and
each patch asserts it matched exactly once, so a transcription edit can't silently
disable one.  The rules are parsed with a small Interlisp reader (super-brackets,
% escapes, (* ...) comments) and re-emitted as plain s-expressions.
"""
import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PLAYER_TXT = ROOT / "transcription" / "kee-expert-player.txt"
RULES_TXT = ROOT / "transcription" / "kee-expert-rules.txt"
FILEINFO = '(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)\n\n'


# ---------------------------------------------------------------- Interlisp reader

class Sym(str):
    """An Interlisp symbol (kept distinct from strings)."""


class Str(str):
    """An Interlisp string."""


def read_all(text):
    """Parse Interlisp text into a list of forms. Super-bracket semantics: ']' closes
    back to the matching '[' (or to top level); '%' escapes the next char in symbols
    and strings. (* ...) comments are kept as lists (callers strip them)."""
    forms, stack = [], []  # stack of (bracket_kind, list)
    i, n = 0, len(text)

    def push_atom(a):
        (stack[-1][1] if stack else forms).append(a)

    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "([":
            stack.append((c, []))
            i += 1
        elif c == ")":
            if not stack:
                raise SyntaxError(f"extra ) at {i}: {text[max(0,i-60):i+20]!r}")
            _, lst = stack.pop()
            push_atom(lst)
            i += 1
        elif c == "]":
            if not stack:
                raise SyntaxError(f"extra ] at {i}")
            while stack:
                kind, lst = stack.pop()
                push_atom(lst)
                if kind == "[":
                    break
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while text[j] != '"':
                if text[j] == "%":
                    j += 1
                buf.append(text[j])
                j += 1
            push_atom(Str("".join(buf)))
            i = j + 1
        elif c == "'":
            # quote-char shorthand: read the next form and wrap it
            sub, used = read_one(text[i + 1:])
            push_atom([Sym("QUOTE"), sub])
            i += 1 + used
        else:
            j, buf = i, []
            while j < n and text[j] not in " \t\r\n()[]\"":
                if text[j] == "%":
                    j += 1
                buf.append(text[j])
                j += 1
            push_atom(atom("".join(buf)))
            i = j
    if stack:
        raise SyntaxError(f"{len(stack)} unclosed bracket(s)")
    return forms


def read_one(text):
    """Read the first form of text -> (form, chars consumed)."""
    depth, i, n = 0, 0, len(text)
    while i < n and text[i] in " \t\r\n":
        i += 1
    start = i
    if text[i] not in "([":
        while i < n and text[i] not in " \t\r\n()[]":
            i += 1
        return read_all(text[start:i])[0], i
    stack = []
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == "%":
                i += 1
            elif c == '"':
                in_str = False
        elif c == "%":
            i += 1
        elif c == '"':
            in_str = True
        elif c in "([":
            stack.append(c)
        elif c == ")":
            stack.pop()
        elif c == "]":
            while stack and stack.pop() != "[":
                pass
        i += 1
        if not stack and not in_str:
            break
    return read_all(text[start:i])[0], i


def atom(tok):
    if re.fullmatch(r"[-+]?\d+", tok):
        return int(tok)
    if re.fullmatch(r"[-+]?(\d+\.\d*|\.\d+)", tok):
        return float(tok)
    return Sym(tok)


def strip_comments(form):
    """Drop (* ...) comment forms (and any comment in a list position)."""
    if isinstance(form, list):
        return [strip_comments(f) for f in form
                if not (isinstance(f, list) and f and f[0] == "*")]
    return form


def emit(form):
    """Print a form with plain round parens, escaping for the Interlisp reader."""
    if isinstance(form, list):
        return "(" + " ".join(emit(f) for f in form) + ")"
    if isinstance(form, Str):
        return '"' + form.replace("%", "%%").replace('"', '%"') + '"'
    if isinstance(form, float):
        return repr(form)
    if isinstance(form, int):
        return str(form)
    return re.sub(r"([()\[\]\"%'])", r"%\1", form)


# ---------------------------------------------------------------- the listings

HEADER_RE = re.compile(r"^\{MITFS1-E40:.*Page \d+\s*$")


def pages(path):
    """-> list of (marker, text) with the per-page printer header line removed."""
    parts = re.split(r"^=== page (\d+) ===\n", path.read_text(encoding="utf-8"), flags=re.M)
    out = [("preamble", parts[0])]
    for k in range(1, len(parts), 2):
        lines = parts[k + 1].split("\n")
        out.append((lines[0], "\n".join(l for l in lines if not HEADER_RE.match(l))))
    return out


def clean(text):
    text = re.sub(r"#\|.*?\|#", "", text, flags=re.S)  # our transcription notes
    text = "\n".join(l for l in text.split("\n") if not re.match(r"\s*;;", l))
    return text.replace("←", "_")


def expert_code():
    """The EXPERT.;25 listing minus the bound-in HRULES page."""
    return clean("\n".join(t for hdr, t in pages(PLAYER_TXT)[1:] if "HRULES" not in hdr))


def rules_text():
    """HRULES.OUT in printed-page order: its printed Page 8 lives in the EXPERT PDF."""
    rp = pages(RULES_TXT)
    stray = [t for hdr, t in pages(PLAYER_TXT)[1:] if "HRULES" in hdr]
    assert len(stray) == 1
    out = []
    for hdr, t in rp[1:]:
        out.append(t)
        if re.search(r"Page 7\s*$", hdr):
            out.append(stray[0])
    return clean("\n".join(out))


# ---------------------------------------------------------------- revival patches

def patch(text, label, old, new, count=1, regex=False):
    n = len(re.findall(old, text)) if regex else text.count(old)
    assert n == count, f"patch {label}: expected {count} match(es), found {n}"
    return re.sub(old, new, text) if regex else text.replace(old, new)


def escape_colons(text):
    """%-escape ':' inside symbol tokens (outside strings), except real package prefixes
    (CL:, XCL:) and keywords.  -> (text, number escaped)."""
    out, i, n, count = [], 0, len(text), 0
    while i < n:
        c = text[i]
        if c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "%" else 1
            out.append(text[i:j + 1]); i = j + 1
        elif c == "%":
            out.append(text[i:i + 2]); i += 2
        elif c in " \t\r\n()[]":
            out.append(c); i += 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()[]\"":
                j += 2 if text[j] == "%" else 1
            tok = text[i:j]
            if ":" in tok and not re.match(r"(CL|XCL|IL):[^:]", tok) and not tok.startswith(":"):
                count += len(re.findall(r"(?<!%):", tok))
                tok = re.sub(r"(?<!%):", "%:", tok)
            out.append(tok); i = j
    return "".join(out), count


def patch_code(code):
    # K0: the 1986 FILECREATED header names the file {MITFS1-E40:SLOAN% SCHOOL:...}<...>.
    # Under the INTERLISP readtable (DEFINE-FILE-INFO) ':' is a package separator, so
    # escape the colons in those host names (HEARTS is header-less and read the old way).
    # Same for 'changes to:' / 'previous date:' in that header and words like 'includes:'
    # in (* ...) comments -- Medley writes those as to%: when it prettyprints a file.
    # K0b: the listing ends with STOP (end of file for LOAD); the rules follow it here.
    code = patch(code, "K0b", r"(?m)^STOP\s*$", "", regex=True)
    # K0c: the 1986 FILECREATED header has no byte count (the listing wraps the file name),
    # and Medley's FILESLOAD dies on that ("NIL is not a NUMBER").  Keep it as a comment;
    # the build writes a fresh FILECREATED at the top of the file.
    code = patch(code, "K0c", "(FILECREATED \" 5-May-86 02:14:32\"",
                 "(* \"1986 header\" FILECREATED \" 5-May-86 02:14:32\"")
    code, n = escape_colons(code)
    assert n >= 4, f"K0: expected the FILECREATED colons, escaped {n}"
    # K1: 1986 environment settings that would change the user's session.
    code = patch(code, "K1a", "(RPAQQ AUTOBACKTRACEFLG ALWAYS)",
                 "(* \"revival K1: dropped (RPAQQ AUTOBACKTRACEFLG ALWAYS)\")")
    code = patch(code, "K1b", "(RPAQQ INITIALS hed)", "(* \"revival K1: dropped (RPAQQ INITIALS hed)\")")
    # K2: NumberWithPoints counted players with MORE THAN ONE point. The 1986 overview
    # (4.2.2, Example 2) diagnoses exactly this and says it was changed to >= 1.
    code = patch(code, "K2", r"count \(GREATERP \(GET\.VALUE Self slot\)\s+1\]",
                 "count (GREATERP (GET.VALUE Self slot) 0]", regex=True)
    # K3: EP.ShootPlay cleared WeakestSuit on the strategy unit (self), not the player,
    # so rule compute.weak.suit ran once and its answer stuck for the rest of the game.
    code = patch(code, "K3", "(REMOVE.ALL.LOCAL.VALUES self (QUOTE WeakestSuit))",
                 "(REMOVE.ALL.LOCAL.VALUES Player (QUOTE WeakestSuit))")
    # K4: EP.Init folds this deal's points into the totals but never zeroes them, so a
    # player's points kept accumulating deal to deal and NumberWithPoints (eclipse.success,
    # te.go.for.it, ote.no.shooting) was wrong from the second deal on.
    code = patch(code, "K4", "      (UNITMSG self (QUOTE ComputeWinnersAndLosers])",
                 "      (for PSlot in (QUOTE (MyPoints LeftPoints RightPoints AcrossPoints))\n"
                 "         do (PUT.VALUE self PSlot 0))    (* revival FIX K4)\n"
                 "      (UNITMSG self (QUOTE ComputeWinnersAndLosers])")
    # K5: EP.PrintLastGameReasons ended with (CLOSEALL), which in Medley closes every open
    # stream (including a DRIBBLE). Close only the per-player files PrintReasons opened.
    code = patch(code, "K5a", "(UNITMSG hist (QUOTE PrintReasons)))\n    (CLOSEALL])",
                 "(UNITMSG hist (QUOTE PrintReasons)))])")
    code = patch(code, "K5b", r"(\.TAB 10 \(CADR reason\)\s+T)\]\)",
                 r"\1))\n      (if (NOT (STREAMP filename)) then (CLOSEF Stream))])", regex=True)
    # K7: rules ask EP.Equivalent? about cards of different suits -- directly (e.g.
    # edump.hope.to.screw.shooter: is the shooter's card, possibly an off-suit dump, NOT the
    # lead-suit winner?) and via HighestEquivalent over multi-suit candidate lists (e.g.
    # dump.non.winner).  The original answers with SHOULDNT, which is a break, not an error,
    # so the game hangs.  Cards of different suits are never equivalent: answer Not?.
    code = patch(code, "K7",
                 r'\(SHOULDNT \(CONCAT "EP\.Equivalent: Cards " Card1 " and " Card2 " not of same suit\."\]',
                 "(PROGN (* revival FIX K7 -- different suits are never equivalent) Not?)]", regex=True)
    # K8: once a suit is played out its winner is NIL, and EP.FewestWinners (rule
    # compute.weak.suit, via SuitWithFewestWinners) asks for the cards equivalent to it:
    # Hand.CardsInSuit of suit NIL is a SHOULDNT break.  No card has no equivalents.
    code = patch(code, "K8", r"(\(\* hed \" 3-May-86 15:06\"\)\s+)\(for c in \(OR LimitingCards",
                 r"\1(AND Card (for c in (OR LimitingCards", regex=True)
    code = patch(code, "K8b", r"(\(QUOTE Equivalent\?\)\s+Card c)\]", r"\1)]", regex=True)
    # K6: reasons are stored newest-first (ADD.VALUE pushes), print them in play order.
    code = patch(code, "K6", "(for reason in (GET.VALUES self (QUOTE Reasons))",
                 "(for reason in (REVERSE (GET.VALUES self (QUOTE Reasons)))")
    return code


RULE_PATCHES = [
    # (rule, label, old, new) -- slips in the 1986 rules that made them never fire.
    ("lead.single.diamond", "K10", "(CAR ?Clubs)", "(CAR ?Diamonds)"),
    ("sfol.last.dump.loser", "K11", "Card.Tricks", "Trick.Cards"),
    ("slead.hearts", "K12", "(QUOTE LowestEquivalent?)", "(QUOTE LowestEquivalent)"),
    ("edump.useless", "K13", "(Not.Null ?ShooterVoids)", "(Not.Null ?AllCardSuitCards)"),
    ("dump.loser", "K14", re.compile(r"\(QUOTE Losers\)\s+\?Self NIL"), "(QUOTE Losers) NIL"),
    # ?Shooter was bound to the shooter unit, then re-used for the shooter's PlayerNum.
    ("edump.hope.to.screw.shooter", "K15",
     re.compile(r"(\(THE PlayerNum OF \(THE Shooter OF \?Self\)\s+IS )\?Shooter\)"), r"\1?ShooterNum)"),
    ("edump.hope.to.screw.shooter", "K15", "(Trick.PlayOf ?Shooter ", "(Trick.PlayOf ?ShooterNum "),
    ("edump.screw.shooter", "K15",
     re.compile(r"(\(THE PlayerNum OF \(THE Shooter OF \?Self\)\s+IS )\?Shooter\)"), r"\1?ShooterNum)"),
    ("edump.screw.shooter", "K15", "(Trick.PlayOf ?Shooter ", "(Trick.PlayOf ?ShooterNum "),
    ("edump.screw.shooter", "K15", "(NEQ ?Shooter ", "(NEQ ?ShooterNum "),
    # ?Mag is never bound in this rule (its siblings bind it to the QS), and LowerCards
    # without a suit matches nothing.
    ("follow.highest.below.QS", "K16", re.compile(r"\(CardList\.LowerCards \?Legals\s+\?Mag\)"),
     "(CardList.LowerCards ?Legals (Card.Create (QUOTE Q) (QUOTE S)) (QUOTE S))"),
]


# ---------------------------------------------------------------- rules

def parse_rules():
    """-> list of (class, parent_path, name, weight, if_form)."""
    lines = rules_text().split("\n")
    rules, cls, cur, path = [], None, None, []
    for ln in lines:
        m = re.match(r"^(\s*)Rule Class (\S+)\s*$", ln)
        r = re.match(r"^\s*Rule (\S+) - Weight is (-?\d+)\s*$", ln)
        if m:
            cls, cur = m.group(2), None
            path.append(cls)
        elif r:
            cur = [cls, r.group(1), int(r.group(2)), []]
            rules.append(cur)
        elif cur is not None:
            cur[3].append(ln)
    out = []
    for cls, name, weight, body in rules:
        text = "\n".join(body)
        for rname, label, old, new in RULE_PATCHES:
            if rname == name:
                n = len(old.findall(text)) if isinstance(old, re.Pattern) else text.count(old)
                assert n == 1, f"rule patch {label} on {name}: {n} matches"
                text = old.sub(new, text) if isinstance(old, re.Pattern) else text.replace(old, new)
        forms = strip_comments(read_all(text))
        assert len(forms) == 1, f"rule {cls}/{name}: {len(forms)} forms"
        form = forms[0]
        assert form[0] == "IF" and "THEN" in form, f"rule {name} is not IF..THEN"
        out.append((cls, name, weight, form))
    return out


def check_code(code):
    """Parse every top-level form; check LET/LET* binding lists look like bindings (the
    kind of bracket slip the linter can't see, e.g. EP.UpdateModel's)."""
    forms = read_all(code)

    def comment_in_bindings(f, where):
        """A (* ...) inside a LET/PROG variable list is a variable named * whose initial value
        gets evaluated -- how three Dealer.* functions died with 'rao is unbound' (an edit-date
        comment transcribed one line too low)."""
        if isinstance(f, list) and f:
            if f[0] in ("LET", "LET*", "PROG", "PROG*") and len(f) > 1 and isinstance(f[1], list):
                for b in f[1]:
                    assert not (isinstance(b, list) and b and b[0] == "*"), \
                        f"{where}: comment inside a {f[0]} variable list: {emit(b)[:60]}"
            for x in f:
                comment_in_bindings(x, where)

    def walk(f, where):
        if isinstance(f, list) and f:
            if f[0] in ("LET", "LET*") and len(f) > 1:
                binds = [] if f[1] == "NIL" else f[1]
                assert isinstance(binds, list), f"{where}: LET without bindings"
                for b in binds:
                    ok = isinstance(b, Sym) or (isinstance(b, list) and len(b) in (1, 2) and isinstance(b[0], Sym))
                    assert ok, f"{where}: suspicious LET binding {emit(b)[:80]}"
            for x in f:
                walk(x, where)

    def let_vars(f):
        return {b if isinstance(b, Sym) else b[0] for b in ([] if f[1] == "NIL" else f[1])
                if isinstance(b, Sym) or (isinstance(b, list) and b)}

    def mentions(f, vs):
        if isinstance(f, list):
            if f and f[0] == "QUOTE":
                return set()
            return set().union(*[mentions(x, vs) for x in f]) if f else set()
        return {f} & vs if isinstance(f, Sym) else set()

    def early_close(f, where):
        """A LET whose variables are still used by the forms AFTER it was closed too
        early (EP.ComputeStats' and EP.UpdateModel's transcription slips)."""
        if not isinstance(f, list):
            return
        for i, x in enumerate(f):
            if isinstance(x, list) and x and x[0] in ("LET", "LET*") and len(x) > 1 \
                    and isinstance(x[1], list):
                used = mentions(f[i + 1:], let_vars(x))
                assert not used, f"{where}: LET variables {sorted(used)} used after the LET closes"
            early_close(x, where)

    names = []
    for f in forms:
        if isinstance(f, list) and f and f[0] == "DEFINEQ":
            for d in f[1:]:
                # A (* ...) here would DEFINE the comment function * itself.
                assert isinstance(d, list) and len(d) == 2 and d[1][0] in ("LAMBDA", "NLAMBDA"), \
                    f"bad DEFINEQ entry {emit(d)[:80]}"
                names.append(d[0])
                comment_in_bindings(d[1], d[0])
                walk(strip_comments(d[1]), d[0])
                early_close(strip_comments(d[1]), d[0])
    return names


# ---------------------------------------------------------------- assembly

def lisp_src(name):
    return clean((HERE / name).read_text(encoding="utf-8")).replace(FILEINFO.strip(), "").replace("\nSTOP\n", "\n")


def build_rules_block(rules):
    out = ["(* \"The 1986 KEE rules (HRULES.OUT), filed by class and weight.  Generated by"
           " medley/build_expert.py from transcription/kee-expert-rules.txt.\")"]
    for cls, name, weight, form in rules:
        out.append(f"(KEE.DEFRULE (QUOTE {cls}) (QUOTE {emit(Sym(name))}) {weight}\n"
                   f"   (QUOTE {emit(form)}))")
    return "\n".join(out)


def build_expert(dev):
    code = patch_code(expert_code())
    names = check_code(code)
    rules = parse_rules()
    kb = lisp_src("expert-kb.lisp")
    parts = ["(* \"EXPERT -- the HEARTS Expert Player (Harley Davis and Ramana Rao, 1986),"
             " revived on LOOPS via KEELOOPS.  Generated by medley/build_expert.py; do not"
             " edit.  Needs LOOPS and HEARTS loaded.\")\n"]
    if dev:
        parts.append(lisp_src("keeloops.lisp"))
        parts.append("(KEE.HoldPages NIL)\n")   # no page holds while EXPERT loads
    else:
        # Turn page holds off BEFORE loading KEELOOPS: by then HEARTS may already have filled
        # the Exec window.  So the dist file carries its own copy of KEE.HoldPages.
        kl = lisp_src("keeloops.lisp")
        fn = kl[kl.index("(KEE.HoldPages\n"):kl.index("(KEE.EnsureLOOPS\n")].rstrip()
        parts.append("(DEFINEQ\n" + fn + "\n)\n(KEE.HoldPages NIL)\n(FILESLOAD KEELOOPS)\n")
    parts += [kb, "\n(* \"---- The 1986 EXPERT.;25 listing (EP.* functions), with revival patches"
                  " K1-K5 --------\")\n", code,
              "\n", build_rules_block(rules), "\n",
              "(EP.BuildKB)\n", "(KEE.HoldPages T)\n", "STOP\n"]
    return with_header("EXPERT", "\n".join(parts)), names, rules


def with_header(name, body):
    """DEFINE-FILE-INFO + a FILECREATED whose byte count is the file's own length (Medley's
    file loader requires the number -- see build-loadfile.py's ACTIVEREGIONS header)."""
    mk = lambda n: (FILEINFO + f'(FILECREATED "26-Sep-2026 12:00:00" {name}.;1 {n})\n\n' + body)
    n = 0
    while n != len(mk(n).encode("utf-8")):
        n = len(mk(n).encode("utf-8"))
    return mk(n)


def build_keeloops():
    return with_header("KEELOOPS", lisp_src("keeloops.lisp") + "\nSTOP\n")


def main():
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    kl = build_keeloops()
    (dist / "KEELOOPS").write_text(kl, encoding="utf-8", newline="\n")
    for path, dev in ((dist / "EXPERT", False), (HERE / "EXPERT", True)):
        text, names, rules = build_expert(dev)
        assert "←" not in text and "#|" not in text
        assert not any(re.match(r"\s*;;", l) for l in text.split("\n"))
        check_code(text)  # whole file must parse; every DEFINEQ entry a real definition
        path.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {path}  ({len(text.splitlines())} lines; {len(names)} EP fns, {len(rules)} rules)")
    classes = {}
    for cls, *_ in rules:
        classes[cls] = classes.get(cls, 0) + 1
    print("rule classes:", ", ".join(f"{c}:{n}" for c, n in classes.items()))
    print(f"wrote {dist / 'KEELOOPS'}  ({len(kl.splitlines())} lines)")


if __name__ == "__main__":
    main()
