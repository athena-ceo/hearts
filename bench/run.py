#!/usr/bin/env python3
"""Run players through the HEARTS benchmark in headless Medley, each on the same fixed deals against
the same opponents.  Runs that finished are kept and skipped, so players can be added later.

    python3 bench/run.py --run pilot --deals 40 expert conservative clown haiku mistral gemma2

Paid players need ANTHROPIC_API_KEY (or OPENAI_API_KEY) in the environment and stop at --budget
dollars each; list them all with --list.  Results go to out/bench/RUN/PLAYER/deals.jsonl, then see
bench/report.py.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OLLAMA = "http://host.docker.internal:11434/v1"

# price is dollars per million input and output tokens, from the provider's price list.
PLAYERS = {
    "expert": {"seat": "EP", "label": "Expert (1986 rules)"},
    "conservative": {"seat": "CP", "label": "Conservative (1986)"},
    "conservative-table": {"seat": "CP", "opponents": "CP CP CP", "label": "Four Conservatives (1986)"},
    "mixed-table": {"seat": "CP", "opponents": "EP CP EP", "label": "Conservatives and Experts in turn (1986)"},
    "clown": {"seat": "CLOWN", "label": "Clown (random legal)"},
    "stub": {"seat": "LP", "label": "Stub (first legal)", "provider": "anthropic", "model": "stub",
             "options": "--stub lowest", "price": (0, 0)},
    "haiku": {"seat": "LP", "label": "Claude Haiku 5.5, low effort", "provider": "anthropic",
              "model": "claude-haiku-5-5", "effort": "low", "price": (0.10, 0.50)},
    "sonnet": {"seat": "LP", "label": "Claude Sonnet 5.5, low effort", "provider": "anthropic",
               "model": "claude-sonnet-5-5", "effort": "low", "price": (2, 10)},
    "opus": {"seat": "LP", "label": "Claude Opus 5.5, low effort", "provider": "anthropic",
             "model": "claude-opus-5-5", "effort": "low", "price": (4, 20)},
    "opus-medium": {"seat": "LP", "label": "Claude Opus 5.5, medium effort", "provider": "anthropic",
                    "model": "claude-opus-5-5", "effort": "medium", "price": (4, 20)},
    "mistral": {"seat": "LP", "label": "Mistral 7B (local, Ollama)", "provider": "openai",
                "model": "mistral:latest", "base_url": OLLAMA, "price": (0, 0)},
    "gemma2": {"seat": "LP", "label": "Gemma 2 9B (local, Ollama)", "provider": "openai",
               "model": "gemma2:latest", "base_url": OLLAMA, "price": (0, 0)},
}

# bench/rules/x-*.lisp: an Expert in seat 1 with changed rules; the file's first line describes them.
for _path in sorted((ROOT / "bench" / "rules").glob("x-*.lisp")):
    PLAYERS[_path.stem] = {"seat": "EP", "extra": f"bench/rules/{_path.name}",
                           "label": "Expert with " + _path.stem[2:]}


def network_player(spec):
    """nn:PATH is a network trained by selfplay/train.py, playing through selfplay/nn_helper.py."""
    path = Path(spec[3:])
    name = "nn-" + path.parent.name + "-" + path.stem
    PLAYERS[name] = {"seat": "LP", "label": f"Self-play network ({path.parent.name}, {path.stem})",
                     "provider": "anthropic", "model": f"/hearts/{path}",
                     "helper": "/hearts/selfplay/nn_helper.py", "price": (0, 0)}
    return name


def lisp_network_player(spec):
    """np:PATH is a network file from selfplay/export_lisp.py, playing in pure Interlisp."""
    path = Path(spec[3:])
    name = "np-" + path.stem
    PLAYERS[name] = {"seat": "NP", "label": f"Self-play network in Lisp ({path.stem})", "net": f"/hearts/{path}"}
    return name


def lisp_string(text):
    return '"' + str(text).replace("%", "%%").replace('"', '%"') + '"'


def script_for(player, deals, budget, container_dir, first=1, trace=False):
    """The settings, then bench/bench.lisp: the harness reads one script, and a nested LOAD of a
    file without STOP is an error."""
    price_in, price_out = player.get("price", (0, 0))
    lines = [
        f"(SETQ BM.Seats (QUOTE ({player['seat']} {player.get('opponents', 'EP EP EP')})))",
        f"(SETQ BM.Count {deals})",
        f"(SETQ BM.First {first})",
        f"(SETQ BM.Extra {lisp_string(player['extra']) if player.get('extra') else 'NIL'})",
        f"(SETQ BM.TraceFile {lisp_string(container_dir + '/tricks.jsonl') if trace else 'NIL'})",
        f"(SETQ BM.Results {lisp_string(container_dir + '/deals.jsonl')})",
        f"(SETQ BM.PriceIn {float(price_in)})",
        f"(SETQ BM.PriceOut {float(price_out)})",
        f"(SETQ BM.Budget {float(budget)})",
        "(SETQ LP.Thoughts? NIL)",
        "(SETQ NP.Thoughts? NIL)",
        f"(SETQ NP.ModelFile {lisp_string(player['net']) if player.get('net') else 'NIL'})",
        f"(SETQ LP.LogFile {lisp_string(container_dir + '/decisions.jsonl')})",
        f"(SETQ LP.Provider {lisp_string(player.get('provider', 'anthropic'))})",
        f"(SETQ LP.Model {lisp_string(player.get('model', 'none'))})",
        f"(SETQ LP.Effort {lisp_string(player.get('effort', 'low'))})",
        f"(SETQ LP.HelperOptions {lisp_string(player.get('options', ''))})",
        f"(SETQ LP.Helper {lisp_string(player['helper']) if player.get('helper') else 'NIL'})",
    ]
    return "\n".join(lines) + "\n" + (ROOT / "bench" / "bench.lisp").read_text()


def child_environment(player):
    """Only the credential this player's provider uses; none for the others."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
                        "OPENAI_API_KEY", "OPENAI_BASE_URL")}
    if player.get("price", (0, 0)) != (0, 0):
        names = (("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")
                 if player["provider"] == "anthropic" else ("OPENAI_API_KEY", "OPENAI_BASE_URL"))
        env.update({k: os.environ[k] for k in names if k in os.environ})
    if player.get("base_url"):
        env["OPENAI_BASE_URL"] = player["base_url"]
    return env


def deals_done(directory):
    path = directory / "deals.jsonl"
    return sum(1 for _ in path.open(encoding="utf-8", newline=None)) if path.exists() else 0


def run_player(run, name, args, local_lock):
    player = PLAYERS[name]
    directory = ROOT / "out" / "bench" / run / name
    done = deals_done(directory)
    if done >= args.deals:
        print(f"{name}: already has {done} deals, skipped", flush=True)
        return True
    if directory.exists():
        shutil.rmtree(directory)  # A partial run can't be resumed: its game state is gone.
    directory.mkdir(parents=True)
    (directory / "player.json").write_text(json.dumps(
        {k: player[k] for k in player if k != "base_url"} | {"name": name}, indent=1))
    container_dir = f"/hearts/out/bench/{run}/{name}"
    script = directory / "script.lisp"
    script.write_text(script_for(player, args.deals, args.budget, container_dir, args.first, args.trace))
    command = ["tools/medley-headless", "--loops", "--timeout", str(args.timeout), "--out", container_dir,
               f"out/bench/{run}/{name}/script.lisp"]
    is_local = bool(player.get("base_url"))
    if is_local:
        local_lock.acquire()  # Two local models at once would only swap each other out of memory.
    try:
        print(f"{name}: started", flush=True)
        with (directory / "run.log").open("w") as log:
            status = subprocess.run(command, cwd=ROOT, env=child_environment(player), stdout=log,
                                    stderr=subprocess.STDOUT, check=False).returncode
    finally:
        if is_local:
            local_lock.release()
    print(f"{name}: exit {status}, {deals_done(directory)} of {args.deals} deals", flush=True)
    return status == 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("players", nargs="*")
    parser.add_argument("--run", default="pilot")
    parser.add_argument("--deals", type=int, default=40)
    parser.add_argument("--budget", type=float, default=1.0, help="dollars per player")
    parser.add_argument("--timeout", type=int, default=14400, help="seconds per player")
    parser.add_argument("--parallel", type=int, default=5)
    parser.add_argument("--first", type=int, default=1, help="deal number to start from")
    parser.add_argument("--trace", action="store_true", help="also log whole deals to tricks.jsonl")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for name, player in PLAYERS.items():
            print(f"{name:14} {player['label']}")
        return 0
    args.players = [network_player(p) if p.startswith("nn:")
                    else lisp_network_player(p) if p.startswith("np:") else p for p in args.players]
    unknown = [p for p in args.players if p not in PLAYERS]
    if unknown or not args.players:
        parser.error(f"choose players from: {', '.join(PLAYERS)}")
    local_lock = threading.Lock()
    with ThreadPoolExecutor(args.parallel) as pool:
        results = list(pool.map(lambda name: run_player(args.run, name, args, local_lock), args.players))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
