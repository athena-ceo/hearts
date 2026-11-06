# Comparing the network with the Expert

Can a trained network show where a rule base is weak, and can its advantage be turned back into explicit
rules? This round says yes to the first and only partly to the second: the comparison located the weakness
precisely, and the best of about 20 rule variants written from it recovered about 15% of the network's gain.

Every number is points per deal against the Expert in seat 1, against three Experts, on the same deals. Lower
is better. Intervals are 95% bootstrap.

## The method

1. **Ask both players about the same positions.** Whole games diverge at the first different card, so
   `bench/diff_positions.py` replays the Expert's games and asks the network about each position.
2. **Measure which disagreements matter.** A hybrid seat ([bench/rules/hy.lisp](../../bench/rules/hy.lisp))
   thinks as the Expert, then plays the network's card for one kind of decision. With every kind on, it scored
   the same as the pure network on all 1,000 deals, so the swap doesn't disturb the game.
3. **Write rules for the ones that matter,** and try them on training deals.
4. **Test the best on deals nothing has seen.**

## Where the disagreements are, and where they matter

They really disagree on 36% of 10,269 decisions with a real choice, counting two cards as the same when no
unplayed card lies between them. That ranges from 56% of leads to 14% of following last in a trick.

| The network chooses, on 1,000 training deals | Alone | The network with this part taken away |
|---|---|---|
| Everything | -3.58 | |
| The pass | +0.02 | -2.80 |
| Leads | -1.79 | -0.73 |
| Following suit | -0.63 | -3.31 |
| Discards | -0.28 | -3.02 |

| The network chooses only while the Expert holds this strategy | All plays | Leads | Following | Discards |
|---|---|---|---|---|
| Shooting | -1.89 | -1.11 | -0.38 | -0.12 |
| Minimizing | | -0.72 | -0.22 | 0.00 |
| Eclipsing | -0.19 | | | |

- **Leads carry most of it.** Without its own leads the network keeps only -0.73 of its -3.58.
- **The pass is worth nothing alone** and about -0.8 when the network also plays the hand.
- **The largest single area is how the Expert plays while shooting.** On the 215 deals where it enters that
  strategy, handing over from that point takes it from 8.13 points per deal to -0.68, from 18 moons to 46, and
  from 91 deals of 13 or more points to 32. The hands and the trigger are the Expert's own, so most of this
  gain comes from what happens after the decision to shoot. It was -1.44 on the fresh deals.

## Rules written from this

| Rules, on 1,000 training deals | Points (95% interval) |
|---|---|
| Lead the lowest non-winner while shooting (`x-sr-lead-low`) | -0.32 (-0.66, +0.02) |
| Keep the queen when going a little over (`x-sr-no-sq-over`) | -0.24 (-0.46, -0.05) |
| Dump the highest heart while shooting (`x-sr-dump-high`) | -0.13 (-0.26, -0.01) |
| Play high on the first trick while shooting (`x-sr-first-high`) | -0.13 (-0.48, +0.20) |
| Take a pointless trick cheaply when last (`x-sr-last-take`) | -0.09 (-0.37, +0.18) |
| Lead any winner while shooting (`x-sr-any-winner`) | -0.32 (-0.80, +0.17) |
| Four of these together (`x-sr-combo`) | -0.66 (-1.10, -0.24) |
| `x-sr-combo` plus three earlier non-shooting changes (`x-sr-plus`) | -1.03 (-1.50, -0.57) |

Copying the network's habits did not always carry over. It leads a winner 62% of the time in these positions,
yet "lead any winner" raised moons to 32 for little gain in points, and adding it to the other changes made them
worse. Small decision trees imitated its choice of lead only weakly (`bench/mine_rules.py`): on unseen positions,
36% while shooting and 48% while minimizing, where the Expert's rules match it 16% and 36%. They served as hints.

## The fair test: 2,000 fresh deals (4001-6000)

Which rule set to report was fixed in advance by the training deals: `x-sr-plus`.

| Player | Points per deal | Against the Expert (95% interval) | Moons shot |
|---|---|---|---|
| Expert, 1986 | 5.40 | | 41 |
| `x-sr-combo`, shooting rules only | 5.17 | -0.23 (-0.55, +0.09) | 38 |
| `x-combo`, gives up shooting | 4.97 | -0.44 (-0.76, -0.11) | 6 |
| **`x-sr-plus`** | **4.92** | **-0.49 (-0.82, -0.15)** | 38 |
| Expert with the network while shooting | 3.96 | -1.44 (-1.84, -1.07) | 76 |
| Network, in pure Lisp | 2.17 | -3.23 (-3.77, -2.72) | 137 |

- **The rules shrank on new deals,** from -1.03 to -0.49, as selected results do.
- **`x-sr-plus` recovers about 15% of the network's gain** (-0.49 of -3.23). The network still beats it by 2.74
  (-3.25, -2.25).
- **`x-sr-plus` can't be told apart from `x-combo` on points** (-0.05, interval -0.35 to +0.24). Its advantage
  is that it keeps shooting, and it takes 38 moons where `x-combo` takes 6.
- **The shooting rules don't explain the hybrid's gain.** Alone they give -0.23 and 38 moons, against -1.44 and
  76 moons for the network in the same positions. Most of what it knows while shooting is still uncaptured.

## Constraint propagation

Section 3.4 of the 1986 report proposed deducing the most possible about opponents' hands by propagating
constraints from voids, cards played and the player's own hand, then reasoning tightly from the result.
[bench/rules/pr.lisp](../../bench/rules/pr.lisp) does this in Lisp. It agreed with the Python version
(`bench/propagate.py`, checked against a linear program) on all 780 positions compared, and all 9,360 bounds
held against the real hands.

| Tricks | Positions with a newly deduced void | With a newly proved holding |
|---|---|---|
| 1-3 | 0.1% | 0.9% |
| 4-6 | 6% | 15% |
| 7-9 | 25% | 57% |
| 10-12 | 75% | 83% |

| On 1,000 training deals | Points (95% interval) |
|---|---|
| Propagated voids given to the existing rules (`x-pr-feed`) | -0.01 (-0.04, +0.01) |
| Oracle: true voids given to the existing rules (`x-or-voids`) | +0.12 (-0.16, +0.43) |
| Lead safe winners, using shown voids (`x-pr-cash-shown`) | +0.45 (+0.18, +0.72) |
| Lead safe winners, using propagated voids (`x-pr-cash`) | +0.42 (+0.16, +0.69) |
| Lead safe winners, using true voids (`x-pr-cash-true`) | +0.02 (-0.14, +0.17) |
| Avoid suits all opponents are void in, propagated (`x-pr-noall`) | -0.11 (-0.25, +0.02) |
| Avoid suits all opponents are void in, shown (`x-pr-noall-shown`) | +0.01 (-0.03, +0.09) |
| Lead low into a proved singleton (`x-pr-single`) | -0.01 (-0.07, +0.06) |

- **Better voids can't help the rules as written.** Only five rules read voids, and none of them is a
  Minimizing rule. No rule reads `HandCards`. Even true voids gain nothing.
- **Knowing the true voids does matter to a rule built on them.** On the "safe winners" rule, true voids beat
  shown ones by -0.43 (-0.69, -0.18). Propagated voids barely improve on shown ones (-0.03), since they arrive
  later than the rule mostly fires.
- **The useful knowledge looks probabilistic,** such as what an opponent's play suggests about its hand, which
  exact constraints can't express. This is an inference from these results, not something measured directly.
- **The report's second half is untested.** Propagation has most to say at tricks 10-12, where a complete search
  of the remaining cards becomes small enough to run.

## Limits

- **Opponents:** every result is one seat against three identical, deterministic Experts, which may be poor at
  stopping a moon. A rule or a network could be exploiting that.
- **Our reconstruction:** the 1986 knowledge base is lost, and some thresholds are reconstructed. The rule behind
  the largest disagreement in shooting leads, `slead.non.op.void.loser`, never fired in 1986 because of an undefined
  function; the revival supplied it. Removing it gave +0.17 (-0.14, +0.49), so it can't be said to help or hurt.
- **Effort:** this is one short round with about 20 hand-written variants. It shows what they recovered, not the
  most that rules can recover.
- **Where this applies:** it relied on a network trained on real outcomes and on replaying any change cheaply on
  the same deals. Where either is missing, a comparison can suggest where to look but can't confirm a rule's value.
