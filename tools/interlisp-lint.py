#!/usr/bin/env python3
"""InterLisp-D bracket linter that LOCALIZES errors per top-level form.

Interlisp prettyprint puts every top-level form — (DEFINEQ, each (FnName [LAMBDA..]),
(RECORD ..), (RPAQ ..) — flush at column 0. Each such form is independently balanced in
correct code (a function nets to zero; (DEFINEQ opens, its lone ) closes). By checking
each column-0 block on its own, a bracket slip in one function can't mask another — every
broken form is reported, with the line where its balance first goes wrong.

Super-bracket semantics:  ( [ open;  ) closes innermost open (either kind);
  ] closes to and including the nearest [ (or to top if none).  % escapes next char.
This is an AID; the authoritative test is loading in Medley.
Usage: interlisp-lint.py FILE...
"""
import sys, re

def scan(text, base=0):
    """Return (final_stack, anomalies) for a chunk. Stack entries: (kind,line,col)."""
    stack, anomalies = [], []
    i, line, col, n = 0, base+1, 1, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; col = 1; i += 1; continue
        if not in_str and c == ";" and i+1 < n and text[i+1] == ";":
            while i < n and text[i] != "\n": i += 1
            continue
        if not in_str and c == "#" and i+1 < n and text[i+1] == "|":
            i += 2
            while i < n-1 and not (text[i]=="|" and text[i+1]=="#"):
                if text[i]=="\n": line += 1
                i += 1
            i += 2; continue
        if not in_str and c == "%":
            i += 2; col += 2; continue
        if c == '"':
            in_str = not in_str; i += 1; col += 1; continue
        if in_str:
            i += 1; col += 1; continue
        if c in "([":
            stack.append((c, line, col))
        elif c == ")":
            if stack: stack.pop()
            else: anomalies.append(("extra )", line, col))
        elif c == "]":
            found = False
            while stack:
                if stack.pop()[0] == "[": found = True; break
            if not found: anomalies.append(("extra ]", line, col))
        i += 1; col += 1
    return stack, anomalies

def blocks(lines):
    """Yield (start_line_index, text) for each column-0 '(' top-level block."""
    idxs = [i for i,l in enumerate(lines) if l[:1] == "("]
    for k, s in enumerate(idxs):
        e = idxs[k+1] if k+1 < len(idxs) else len(lines)
        yield s, "\n".join(lines[s:e])

def main(paths):
    bad = 0
    for path in paths:
        lines = open(path, encoding="utf-8").read().split("\n")
        print(f"=== {path} ===")
        clean = True
        for start, text in blocks(lines):
            stack, anom = scan(text, base=start)
            name = lines[start].strip()[:48]
            if stack or anom:
                clean = False; bad += 1
                print(f"  L{start+1}: {name}")
                for kind,l,c in anom: print(f"      {kind} at {l}:{c}")
                for kind,l,c in stack[-4:]: print(f"      unclosed {kind} at {l}:{c}")
        if clean: print("  all top-level forms balanced ✓")
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
