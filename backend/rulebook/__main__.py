# Copyright (c) 2026 Athena Decision Systems SAS.
"""The rulebook command.

    python -m rulebook check FILE --vocabulary MODULE:NAME [--base FILE]
    python -m rulebook list FILE --vocabulary MODULE:NAME [--base FILE]
    python -m rulebook phrases --vocabulary MODULE:NAME
    python -m rulebook diff OLD NEW
"""
import argparse
import importlib
import sys
from pathlib import Path

from . import RuleFileError, diff, listing, load, parse, phrases


def _vocabulary(spec):
    module, _, name = spec.partition(":")
    return getattr(importlib.import_module(module), name)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="rulebook", description="Check, list and compare rule files.")
    parser.add_argument("command", choices=["check", "list", "phrases", "diff"])
    parser.add_argument("files", nargs="*")
    parser.add_argument("--vocabulary", help="MODULE:NAME of a Vocabulary")
    parser.add_argument("--base", help="the rule file that FILE varies")
    args = parser.parse_args(argv)
    if args.command == "diff":
        if len(args.files) != 2:
            parser.error("diff takes two files")
        old, new = (parse(Path(f).read_text()) for f in args.files)
        print("\n".join(diff(old, new)) or "no change to any rule or parameter")
        return 0
    if not args.vocabulary:
        parser.error(f"{args.command} needs --vocabulary")
    vocabulary = _vocabulary(args.vocabulary)
    if args.command == "phrases":
        print("\n".join(phrases(vocabulary)))
        return 0
    if len(args.files) != 1:
        parser.error(f"{args.command} takes one file")
    try:
        base = load(args.base, vocabulary) if args.base else None
        rulebase = load(args.files[0], vocabulary, base)
    except RuleFileError as error:
        print(error, file=sys.stderr)
        return 1
    if args.command == "check":
        print(f"{args.files[0]}: {len(rulebase.rules)} rules in {len(rulebase.classes)} classes, "
              f"{len(rulebase.parameters)} parameters, all read")
    else:
        print("\n".join(listing(rulebase)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
