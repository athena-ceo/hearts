#!/usr/bin/env python3
"""One real play and one real pass through the LLM player's helper: does this credential, endpoint
and model work?  This calls the API and costs real money, a fraction of a cent on the default
model.  It is not part of tests/run-all.sh.

    ANTHROPIC_API_KEY=... python3 tests/real_api_check.py [--model M] [--effort E]
    OPENAI_API_KEY=... python3 tests/real_api_check.py --provider openai --model M

The variables the helper honours work here too: ANTHROPIC_AUTH_TOKEN, ANTHROPIC_BASE_URL and
OPENAI_BASE_URL.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HELPER = ROOT / "medley" / "llm_player.py"

PLAY = {
    "decision": "play", "seat": 3, "deal": 1, "direction": "Left",
    "hand": ["D9", "DK", "S3", "SQ", "H2", "C4", "C8", "HA", "H10", "S7", "D3", "D7"],
    "legal": ["D3", "D7", "D9", "DK"],
    "trick": {"leader": 1, "cards": ["D4", "D10"]},
    "hearts_broken": False, "first_trick": False,
    "history": [{"leader": 4, "cards": ["C2", "C9", "CK", "C5"], "winner": 2}],
    "scores": [0, 0, 0, 0], "over_score": 100,
}
PASS = {
    "decision": "pass", "seat": 2, "deal": 1, "direction": "Right",
    "hand": ["C2", "C3", "D4", "D8", "D10", "S2", "S10", "SQ", "SA", "H3", "H9", "HJ", "HA"],
    "scores": [0, 0, 0, 0], "over_score": 100,
}


def ask(request, args):
    with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
        json.dump(request, f)
        f.flush()
        result = subprocess.run(
            [sys.executable, str(HELPER), "--provider", args.provider,
             "--model", args.model, "--effort", args.effort,
             "--timeout", str(args.timeout), f.name],
            capture_output=True, text=True, check=False)
    return result.stdout.strip() or f"(ERROR no reply; stderr: {result.stderr.strip()[-300:]})"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    parser.add_argument("--model", help="required for openai; default claude-haiku-5-5")
    parser.add_argument("--effort", default="low")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if args.provider == "openai":
        if not args.model:
            parser.error("--provider openai needs --model")
        endpoint = os.environ.get("OPENAI_BASE_URL", "the OpenAI API")
    else:
        args.model = args.model or "claude-haiku-5-5"
        endpoint = os.environ.get("ANTHROPIC_BASE_URL", "the Anthropic API")
    print(f"Asking {args.model} at {endpoint}")
    failed = False
    for name, request in (("play", PLAY), ("pass", PASS)):
        reply = ask(request, args)
        print(f"{name}: {reply}")
        failed = failed or not reply.startswith("(OK")
    print("FAILED" if failed else "OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
