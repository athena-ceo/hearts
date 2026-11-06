#!/usr/bin/env python3
"""Train a Hearts network by self-play, with no search: masked policy, PPO, on the simulator.

    selfplay/.venv/bin/python selfplay/train.py --name a --hours 10 --workers 6 --seed 1

Half the deals are pure self-play, the rest are one learning seat against past versions of itself or
simple rule-based bots.  The reward is margin: minus (my score - the others' average) / 26, paid trick
by trick with a correction at the end for moons, so it sums to the true result.  Writes to
out/selfplay/NAME: log.csv, latest.pt (resumes from it), best.json and hour-N.json, for nn_helper.py.
"""
import argparse
import csv
import json
import multiprocessing as mp
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).resolve().parent))
import features  # noqa: E402
import hearts_sim as sim  # noqa: E402
from bots import DuckBot, RandomBot  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCALE = np.ones(features.SIZE, dtype=np.float32)
for _index, _value in features.SCALED.items():
    SCALE[_index] = _value
HIDDEN = 256
LAMBDA = 0.95


def to_numpy(model):
    return [p.detach().cpu().numpy().astype(np.float32) for p in model.parameters()]


class Net(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(features.SIZE, HIDDEN)
        self.layer2 = nn.Linear(HIDDEN, HIDDEN)
        self.policy = nn.Linear(HIDDEN, 52)
        self.value = nn.Linear(HIDDEN, 1)
        with torch.no_grad():
            self.policy.weight.mul_(0.01)

    def forward(self, x):
        h = torch.relu(self.layer2(torch.relu(self.layer1(x))))
        return self.policy(h), self.value(h).squeeze(-1)


def forward_numpy(weights, x):
    w1, b1, w2, b2, wp, bp, wv, bv = weights
    h = np.maximum(w1 @ x + b1, 0)
    h = np.maximum(w2 @ h + b2, 0)
    return wp @ h + bp, (wv @ h + bv).item()


class NetPlayer:
    """Samples moves from the policy, or takes the best when greedy, and records if asked."""

    def __init__(self, weights, rng, record=False, greedy=False):
        self.weights, self.rng, self.record, self.greedy = weights, rng, record, greedy
        self.obs, self.actions, self.logps, self.values, self.rewards = [], [], [], [], []
        self.pending = 0.0

    def forced(self):
        pass

    def add_reward(self, reward):
        if self.rewards:
            self.rewards[-1] += reward
        else:
            self.pending += reward

    def decide(self, request, selected=()):
        encoded, legal = features.encode(request, selected)
        raw = np.zeros(features.SIZE, dtype=np.uint8)
        for index, value in encoded.items():
            raw[index] = value
        logits, value = forward_numpy(self.weights, raw * SCALE)
        legal_logits = logits[legal]
        if self.greedy:
            choice = int(np.argmax(legal_logits))
            logp = 0.0
        else:
            legal_logits = legal_logits - legal_logits.max()
            probabilities = np.exp(legal_logits)
            probabilities /= probabilities.sum()
            choice = int(self.rng.choice(len(legal), p=probabilities))
            logp = float(np.log(probabilities[choice] + 1e-12))
        action = legal[choice]
        if self.record:
            self.obs.append(raw)
            self.actions.append(action)
            self.logps.append(logp)
            self.values.append(value)
            self.rewards.append(self.pending)
            self.pending = 0.0
        return sim.DECK[action]

    def choose_pass(self, request):
        selected = []
        for _ in range(3):
            selected.append(self.decide(request, selected))
        return selected

    def choose_play(self, request):
        return self.decide(request)


def margin(scores, seat):
    return scores[seat] - sum(s for i, s in enumerate(scores) if i != seat) / 3


def rollout(task):
    weights, opponent, deals, seed = task
    rng = np.random.default_rng(seed)
    python_rng = random.Random(seed)
    batches = []
    for _ in range(deals):
        deck = list(sim.DECK)
        python_rng.shuffle(deck)
        direction = python_rng.choice(sim.DIRECTIONS)
        mode = python_rng.random()
        if mode < 0.5:
            players = [NetPlayer(weights, rng, record=True) for _ in range(4)]
            learners = [0, 1, 2, 3]
        else:
            seat = python_rng.randrange(4)
            if mode < 0.7 and opponent is not None:
                players = [NetPlayer(opponent, rng) for _ in range(4)]
            else:
                players = [DuckBot(python_rng) if python_rng.random() < 0.85 else RandomBot(python_rng)
                           for _ in range(4)]
            players[seat] = NetPlayer(weights, rng, record=True)
            learners = [seat]
        potential = [0.0, 0.0, 0.0, 0.0]

        def on_trick(taken):
            for s in learners:
                now = -margin(taken, s) / 26
                players[s].add_reward(now - potential[s])
                potential[s] = now
        scores, _taken = sim.play_deal(players, deck, direction, on_trick)
        for s in learners:
            players[s].add_reward(-margin(scores, s) / 26 - potential[s])
            player = players[s]
            count = len(player.actions)
            if not count:
                continue
            advantages = np.zeros(count, dtype=np.float32)
            running = 0.0
            for t in reversed(range(count)):
                next_value = player.values[t + 1] if t + 1 < count else 0.0
                delta = player.rewards[t] + next_value - player.values[t]
                running = delta + LAMBDA * running
                advantages[t] = running
            batches.append((np.stack(player.obs), np.array(player.actions, dtype=np.int8),
                            np.array(player.logps, dtype=np.float32), advantages,
                            advantages + np.array(player.values, dtype=np.float32)))
    return [np.concatenate([b[i] for b in batches]) for i in range(5)], deals


def evaluate(task):
    """Fixed deals, greedy, seat 1 against three DuckBots: the same test every time."""
    weights, first, count = task
    total = moons = margins = 0
    for number in range(first, first + count):
        python_rng = random.Random(number)
        deck = list(sim.DECK)
        python_rng.shuffle(deck)
        players = [NetPlayer(weights, None, greedy=True), DuckBot(), DuckBot(), DuckBot()]
        scores, _ = sim.play_deal(players, deck, sim.DIRECTIONS[number % 4])
        total += scores[0]
        margins += margin(scores, 0)
        moons += scores[0] == -26
    return total, margins, moons, count


def export(model, path):
    def rows(layer):
        return [[round(v, 5) for v in row] for row in layer.weight.detach().numpy().tolist()], \
            [round(v, 5) for v in layer.bias.detach().numpy().tolist()]
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"hidden": [rows(model.layer1), rows(model.layer2)],
                                     "policy": rows(model.policy)}))
    temporary.rename(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", required=True)
    parser.add_argument("--hours", type=float, default=10)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--deals-per-task", type=int, default=300)
    parser.add_argument("--evaluate-every", type=int, default=25)
    args = parser.parse_args()
    out = ROOT / "out" / "selfplay" / args.name
    out.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    torch.set_num_threads(4)
    model = Net()
    optimizer = torch.optim.Adam(model.parameters(), lr=3e-4)
    state = {"iteration": 0, "deals": 0, "seconds": 0.0, "best": 1e9, "hour": 0, "pool": []}
    checkpoint = out / "latest.pt"
    if checkpoint.exists():
        saved = torch.load(checkpoint, weights_only=False)
        model.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        state = saved["state"]
    log_path = out / "log.csv"
    new_log = not log_path.exists()
    log_file = log_path.open("a", newline="")
    log = csv.writer(log_file)
    if new_log:
        log.writerow(["iteration", "hours", "deals", "samples", "policy_loss", "value_loss", "entropy",
                      "duck_points", "duck_margin", "duck_moons"])
    limit = args.hours * 3600
    started = time.monotonic() - state["seconds"]
    py_rng = random.Random(args.seed * 7919 + state["iteration"])
    with mp.get_context("spawn").Pool(args.workers) as pool:
        while time.monotonic() - started < limit:
            elapsed = time.monotonic() - started
            fraction = min(elapsed / limit, 1.0)
            for group in optimizer.param_groups:
                group["lr"] = 3e-4 * (1 - 0.9 * fraction)
            entropy_weight = 0.01 * (1 - 0.9 * fraction)
            weights = to_numpy(model)
            opponent = py_rng.choice(state["pool"]) if state["pool"] else None
            tasks = [(weights, opponent, args.deals_per_task, py_rng.randrange(2**31)) for _ in range(args.workers)]
            results = pool.map(rollout, tasks)
            obs, actions, logps, advantages, returns = [np.concatenate([r[0][i] for r in results]) for i in range(5)]
            state["deals"] += sum(r[1] for r in results)
            scale = torch.from_numpy(SCALE)
            obs_t = torch.from_numpy(obs.astype(np.float32)) * scale
            actions_t = torch.from_numpy(actions.astype(np.int64))
            logps_t = torch.from_numpy(logps)
            advantages_t = torch.from_numpy(advantages)
            advantages_t = (advantages_t - advantages_t.mean()) / (advantages_t.std() + 1e-8)
            returns_t = torch.from_numpy(returns)
            masks = obs_t[:, features.LEGAL:features.LEGAL + 52] > 0
            losses = []
            for _epoch in range(3):
                order = torch.randperm(len(obs_t))
                for start in range(0, len(order), 8192):
                    batch = order[start:start + 8192]
                    logits, values = model(obs_t[batch])
                    logits = logits.masked_fill(~masks[batch], -1e9)
                    log_probs = torch.log_softmax(logits, dim=-1)
                    new_logp = log_probs.gather(1, actions_t[batch].unsqueeze(1)).squeeze(1)
                    probs = log_probs.exp()
                    entropy = -(probs * log_probs.clamp(min=-30)).sum(-1).mean()
                    ratio = (new_logp - logps_t[batch]).exp()
                    adv = advantages_t[batch]
                    policy_loss = -torch.min(ratio * adv, ratio.clamp(0.8, 1.2) * adv).mean()
                    value_loss = ((values - returns_t[batch]) ** 2).mean()
                    loss = policy_loss + 0.5 * value_loss - entropy_weight * entropy
                    optimizer.zero_grad()
                    loss.backward()
                    nn.utils.clip_grad_norm_(model.parameters(), 0.5)
                    optimizer.step()
                    losses.append((policy_loss.item(), value_loss.item(), entropy.item()))
            state["iteration"] += 1
            state["seconds"] = time.monotonic() - started
            row = [state["iteration"], round(state["seconds"] / 3600, 3), state["deals"], len(obs_t),
                   *[round(float(np.mean([l[i] for l in losses])), 4) for i in range(3)]]
            if state["iteration"] % args.evaluate_every == 0:
                weights = to_numpy(model)
                parts = pool.map(evaluate, [(weights, 10**6 + i * 1000, 1000) for i in range(args.workers)])
                count = sum(p[3] for p in parts)
                points_mean = sum(p[0] for p in parts) / count
                margin_mean = sum(p[1] for p in parts) / count
                moons = sum(p[2] for p in parts)
                row += [round(points_mean, 3), round(margin_mean, 3), moons]
                if margin_mean < state["best"]:
                    state["best"] = margin_mean
                    export(model, out / "best.json")
                state["pool"] = (state["pool"] + [weights])[-20:]
                torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "state": state}, checkpoint)
                print(*row, flush=True)
            log.writerow(row)
            log_file.flush()
            hour = int(state["seconds"] // 3600)
            if hour > state["hour"]:
                state["hour"] = hour
                export(model, out / f"hour-{hour}.json")
    export(model, out / "final.json")
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "state": state}, checkpoint)
    print("finished", state["iteration"], "iterations", state["deals"], "deals", flush=True)


if __name__ == "__main__":
    main()
