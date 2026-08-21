#!/usr/bin/env python3
"""Rough Interlisp paren/bracket balance checker.

Interlisp super-paren semantics (approx):
  '('  opens a round group
  '['  opens a super group
  ')'  closes the nearest open round group
  ']'  closes everything up to and including the nearest open '['
  '%'  escapes the next character (Interlisp escape)
  "..."  string literal
This is an AID, not proof — the authoritative test is loading in Medley.
"""
import sys, re

def check(path):
    text = open(path, encoding="utf-8").read()
    stack = []            # list of ('(' or '[', line, col)
    i, line, col = 0, 1, 1
    n = len(text)
    in_str = False
    errors = []
    while i < n:
        c = text[i]
        if c == "\n":
            line += 1; col = 1; i += 1; continue
        # strip our own line comments (;; ...) only at line start-ish
        if not in_str and c == ";" and i+1 < n and text[i+1] == ";":
            # skip our own ;; annotation line to end of line
            while i < n and text[i] != "\n":
                i += 1
            continue
        # skip our own #| ... |# transcription annotations (not Interlisp syntax)
        if not in_str and c == "#" and i+1 < n and text[i+1] == "|":
            i += 2
            while i < n-1 and not (text[i] == "|" and text[i+1] == "#"):
                if text[i] == "\n":
                    line += 1
                i += 1
            i += 2
            continue
        if not in_str and c == "%":   # Interlisp escape: skip next char
            i += 2; col += 2; continue
        if c == '"':
            in_str = not in_str; i += 1; col += 1; continue
        if in_str:
            i += 1; col += 1; continue
        if c in "([":
            stack.append((c, line, col))
        elif c == ")":
            # Interlisp: ) closes the innermost open bracket of EITHER type.
            if stack:
                stack.pop()
            else:
                errors.append(f"  unmatched ) at {line}:{col}")
        elif c == "]":
            # pop until we remove a '['
            found = False
            while stack:
                top = stack.pop()
                if top[0] == "[":
                    found = True; break
            if not found:
                errors.append(f"  unmatched ] at {line}:{col}")
        i += 1; col += 1
    return stack, errors

if __name__ == "__main__":
    for path in sys.argv[1:]:
        stack, errors = check(path)
        print(f"=== {path} ===")
        print(f"  leftover open groups: {len(stack)}")
        for kind, l, c in stack[-8:]:
            print(f"    unclosed {kind} at {l}:{c}")
        if errors:
            print(f"  {len(errors)} anomalies:")
            for e in errors[:20]:
                print(e)
        if not stack and not errors:
            print("  BALANCED")
