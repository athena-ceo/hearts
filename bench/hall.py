"""The bounds from bench/propagate.py in closed form, as medley's PR.Bounds computes them.

Hall's condition decides feasibility, since total supply equals total need; min-cut gives the lower bound."""


def feasible(supply, need, allowed):
    for mask in range(1, 16):
        total = sum(supply[s] for s in range(4) if mask >> s & 1)
        room = sum(need[o] for o in range(3) if any(mask >> s & 1 and allowed[s][o] for s in range(4)))
        if total > room:
            return False
    return True


def bounds(supply, need, allowed):
    low = [[0] * 3 for _ in range(4)]
    high = [[0] * 3 for _ in range(4)]
    for s in range(4):
        for o in range(3):
            if not allowed[s][o]:
                continue
            best = 0
            for k in range(min(supply[s], need[o]), 0, -1):
                a, b = list(supply), list(need)
                a[s] -= k
                b[o] -= k
                if feasible(a, b, allowed):
                    best = k
                    break
            high[s][o] = best
            least = 0
            for mask in range(1, 16):
                if not mask >> s & 1:
                    continue
                if any(mask >> t & 1 and t != s and allowed[t][o] for t in range(4)):
                    continue
                total = sum(supply[t] for t in range(4) if mask >> t & 1)
                others = sum(need[p] for p in range(3)
                             if p != o and any(mask >> t & 1 and allowed[t][p] for t in range(4)))
                least = max(least, total - others)
            low[s][o] = least
    return low, high
