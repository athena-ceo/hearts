#!/usr/bin/env python3
"""The overnight self-play run: train two networks, try them against the real Expert in Medley on the
way, and leave the comparison in out/selfplay/results.txt.  Costs nothing but electricity.

    caffeinate -i selfplay/.venv/bin/python selfplay/overnight.py --hours 10

Training deals only (201 up): the unseen deals stay unseen until a final choice is made.
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "selfplay"
SEEDS = {"a": 1, "b": 2}


def say(text):
    print(time.strftime("%H:%M"), text, flush=True)


def results():
    report = subprocess.run([sys.executable, "bench/compare.py", "--run", "train"], cwd=ROOT,
                            capture_output=True, text=True, check=False).stdout
    (OUT / "results.txt").write_text(time.strftime("%c") + "\n" + report)


def try_in_medley(tag, source, deals):
    """Copy a network now, since training keeps replacing best.json, and play it in Medley."""
    specs = []
    for name in SEEDS:
        path = OUT / name / source
        if path.exists():
            copy = OUT / name / f"{tag}.json"
            shutil.copy(path, copy)
            specs.append(f"nn:{copy.relative_to(ROOT)}")
    if specs:
        say(f"Medley: {tag}, {deals} deals")
        subprocess.run(["python3", "bench/run.py", "--run", "train", "--deals", str(deals), "--first", "201",
                        "--timeout", "14400", "--parallel", "4", *specs], cwd=ROOT, check=False)
        results()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hours", type=float, default=10)
    parser.add_argument("--checks", default="1,3,6", help="hours at which to try the best so far in Medley")
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    trainers = []
    for name, seed in SEEDS.items():
        log = (OUT / f"{name}.log").open("a")
        trainers.append(subprocess.Popen(
            [sys.executable, "selfplay/train.py", "--name", name, "--hours", str(args.hours),
             "--workers", str(args.workers), "--seed", str(seed)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT))
    say("training started")
    started = time.monotonic()
    for hour in [float(h) for h in args.checks.split(",") if float(h) < args.hours]:
        while time.monotonic() - started < hour * 3600:
            time.sleep(30)
        try_in_medley(f"check-{hour:g}h", "best.json", 300)
    for trainer in trainers:
        trainer.wait()
    say("training finished")
    try_in_medley("end-best", "best.json", 1000)
    try_in_medley("end-final", "final.json", 1000)
    say("done")


if __name__ == "__main__":
    main()
