# Benchmark results

Each player sat in seat 1 against three 1986 Experts, on the same fixed deals. Lower is better. The
difference is the player's points per deal minus the Expert's on the same deals, with a 95% bootstrap
interval. Margin is seat 1's points minus the average of the other three, so an opponent's moon counts
against you.

| Player | Deals | Difference in points | Difference in margin | Cost per deal | Seconds per deal |
|---|---|---|---|---|---|
| Neural network, in pure Lisp | 2,800 held out | **-3.09** (-3.55 to -2.65) | -3.64 (-4.14 to -3.15) | none | 1.1 |
| Rule changes (`x-combo`) | 2,800 held out | -0.40 (-0.69 to -0.12) | -0.70 (-1.02 to -0.36) | none | 1.7 |
| Expert, 1986 | 2,800 held out | 5.31 points per deal | | none | 1.7 |
| Opus 5.5, medium effort | 75 pilot deals | +0.53 (-1.31 to +2.67) | +0.94 | about $0.19 | 76 |
| Haiku 5.5, low effort | 100 pilot deals | +3.18 | | under $0.01 | |

The LLM rows come from different deals (the pilot, 1-200) and far fewer of them, so compare them with the
network only roughly. Opus can't be told apart from the Expert on 75 deals. The $15 cap stopped that run.

Reports: [held-out 1201-2000](test/report.html), [held-out 2001-4000](test2/report.html),
[pilot, with the LLMs](pilot/report.html).

## The network

- **What was tested:** `dist/HEARTSNET` itself, playing in pure Interlisp. It was chosen from four networks
  on the training deals (201-1200) and then tested once on the 2,800 held-out deals. The two held-out sets
  agree: -3.23 on 800 and -3.03 on 2,000.
- **How it was trained:** 10 hours on one Mac, about 83 million deals, against itself, its past snapshots
  and two simple bots. It never played the Expert in training. The Expert results were used only to choose
  among the four finalists.
- **Most of the gain is the moon:** the network shot the moon on 191 deals against the Expert's 69. Those
  191 deals alone account for -2.24 of the -3.09. Ordinary deals, with no moon by the network and none
  against it, account for -0.74, and deals where it was hit by a moon for -0.11. It also took the queen less
  often, 19% of deals against 25%.
- **Lisp and Python agree:** the same network played the same 300 deals both ways with identical scores.

## Turning the network's gain back into rules

Comparing the network with the Expert located where the rules are weakest, and the best rules written from that
scored -0.49 (-0.82 to -0.15) on 2,000 fresh deals, where the network scored -3.23. See
[differential.md](differential.md), and the [report on those deals](fresh/report.html).

## What this doesn't show

- It sat at one seat against three Experts, which all play alike and are deterministic. Those Experts may
  be poor at stopping a moon, and these results can't tell how much of the gain depends on that.
- It hasn't been tested against people, against a mix of opponents, or over whole games to 100 points.
- The gain from moons is measured by splitting on what the network did, so it describes where the points
  came from. It doesn't show what a change to the moon play alone would be worth.
