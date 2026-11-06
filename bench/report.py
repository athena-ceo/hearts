#!/usr/bin/env python3
"""Turn a benchmark run (bench/run.py) into a report: docs/benchmarks/RUN/report.html, deals.csv and
compressed decision logs.

    python3 bench/report.py --run pilot

Everyone is compared with the Expert on the deals both played, and the cards are checked to be the
same.  Confidence intervals are bootstrapped over deals with a fixed seed, so a run always gives the
same report.
"""
import argparse
import csv
import gzip
import html
import json
import random
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = "expert"
RESAMPLES = 5000


def load_run(run):
    players = {}
    for directory in sorted((ROOT / "out" / "bench" / run).iterdir()):
        path = directory / "deals.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(line) for line in path.open(encoding="utf-8", newline=None) if line.strip()]
        if rows:
            info = json.loads((directory / "player.json").read_text())
            players[directory.name] = {"info": info, "rows": rows, "directory": directory}
    return players


def check_same_cards(players):
    hands = {}
    for name, player in players.items():
        for row in player["rows"]:
            if hands.setdefault(row["deal"], row["hand"]) != row["hand"]:
                sys.exit(f"{name} was dealt different cards on deal {row['deal']}")


def interval(values):
    """Mean and 95% bootstrap interval of the mean."""
    rng = random.Random(1986)
    count = len(values)
    means = sorted(sum(rng.choices(values, k=count)) / count for _ in range(RESAMPLES))
    return statistics.fmean(values), means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES)]


def margin(row):
    """Seat 1's points minus the average of the others: an opponent's moon counts against you."""
    return row["scores"][0] - sum(row["scores"][1:]) / 3


def summarize(players):
    baseline = {r["deal"]: r["scores"][0] for r in players[BASELINE]["rows"]}
    summaries = []
    for name, player in players.items():
        rows = player["rows"]
        points = [r["scores"][0] for r in rows]
        last = rows[-1]
        price_in, price_out = player["info"].get("price", (0, 0))
        decisions = last["decisions"]
        differences = [r["scores"][0] - baseline[r["deal"]] for r in rows if r["deal"] in baseline]
        base_rows = {r["deal"]: r for r in players[BASELINE]["rows"]}
        margins = [margin(r) - margin(base_rows[r["deal"]]) for r in rows if r["deal"] in base_rows]
        summaries.append({
            "name": name,
            "label": player["info"]["label"],
            "deals": len(rows),
            "mean": interval(points),
            "difference": interval(differences) if name != BASELINE else None,
            "margin": interval(margins) if name != BASELINE else None,
            "others_moons": sum(-26 in r["scores"][1:] for r in rows),
            "paired": len(differences),
            "spread": statistics.stdev(points) if len(points) > 1 else 0,
            "difference_spread": statistics.stdev(differences) if len(differences) > 1 else 0,
            "queen": sum(r["queen"] == 1 for r in rows) / len(rows),
            "moons": sum(r["scores"][0] == -26 for r in rows),
            "decisions": decisions,
            "fallbacks": last["fallbacks"],
            "input_tokens": last["input_tokens"],
            "output_tokens": last["output_tokens"],
            "cost": (last["input_tokens"] * price_in + last["output_tokens"] * price_out) / 1e6,
            "seconds_per_deal": statistics.fmean(r["ms"] for r in rows) / 1000,
        })
    return sorted(summaries, key=lambda s: s["mean"][0])


def finding(summary):
    low, high = summary["difference"][1:]
    gap = abs(summary["difference"][0])
    if high < 0:
        return f"scored {gap:.1f} fewer points per deal than the Expert: better, beyond the noise"
    if low > 0:
        return f"scored {gap:.1f} more points per deal than the Expert: worse, beyond the noise"
    return f"can't be told apart from the Expert on {summary['paired']} deals (difference {summary['difference'][0]:+.1f})"


def dot_chart(rows, title_id, reference, reference_label, x_label):
    """Horizontal dots with interval whiskers.  rows: (label, mean, low, high, tip)."""
    width, row_height, left, right, top, bottom = 760, 38, 230, 70, 16, 44
    height = top + bottom + row_height * len(rows)
    low = min([r[2] for r in rows] + [reference])
    high = max([r[3] for r in rows] + [reference])
    ticks_from, ticks_to = int(low // 2 * 2), int(-(-high // 2) * 2)
    step = 2 if ticks_to - ticks_from <= 20 else 5
    ticks_from = ticks_from // step * step
    ticks_to = -(-ticks_to // step) * step

    def x(value):
        return left + (value - ticks_from) / (ticks_to - ticks_from) * (width - left - right)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-labelledby="{title_id}" class="dots">']
    for tick in range(ticks_from, ticks_to + 1, step):
        parts.append(f'<line class="grid" x1="{x(tick):.1f}" x2="{x(tick):.1f}" y1="{top}" y2="{height - bottom}"/>')
        parts.append(f'<text class="axis" x="{x(tick):.1f}" y="{height - bottom + 18}" text-anchor="middle">{tick}</text>')
    parts.append(f'<line class="reference" x1="{x(reference):.1f}" x2="{x(reference):.1f}" y1="{top - 6}" y2="{height - bottom}"/>')
    parts.append(f'<text class="axis" x="{(left + width - right) / 2:.1f}" y="{height - 6}" text-anchor="middle">{html.escape(x_label)}</text>')
    if reference_label:
        parts.append(f'<text class="axis" x="{x(reference) + 5:.1f}" y="{top + 2}">{html.escape(reference_label)}</text>')
    for index, (label, mean, lo, hi, tip) in enumerate(rows):
        y = top + row_height * index + row_height / 2
        parts.append(f'<g class="row" data-tip="{html.escape(tip, quote=True)}">'
                     f'<rect class="hit" x="0" y="{y - row_height / 2:.1f}" width="{width}" height="{row_height}"/>'
                     f'<text class="label" x="{left - 12}" y="{y + 4:.1f}" text-anchor="end">{html.escape(label)}</text>'
                     f'<line class="whisker" x1="{x(lo):.1f}" x2="{x(hi):.1f}" y1="{y:.1f}" y2="{y:.1f}"/>'
                     f'<circle class="dot" cx="{x(mean):.1f}" cy="{y:.1f}" r="6"/>'
                     f'<text class="value" x="{x(hi) + 10:.1f}" y="{y + 4:.1f}">{value_text(mean, reference)}</text>'
                     + '</g>')
    parts.append("</svg>")
    return "".join(parts)


def value_text(mean, reference):
    return f"{mean:+.1f}" if reference == 0 else f"{mean:.1f}"


STYLE = """
.viz-root { color-scheme: light; --surface: #fcfcfb; --page: #f9f9f7; --ink: #0b0b0b; --ink2: #52514e;
  --muted: #6f6d68; --grid: #e1e0d9; --base: #c3c2b7; --series: #2a78d6; --hover: rgba(11,11,11,.04);
  font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--ink); background: var(--page);
  margin: 0; padding: 32px 20px 64px; }
@media (prefers-color-scheme: dark) { .viz-root { color-scheme: dark; --surface: #1a1a19; --page: #0d0d0d;
  --ink: #f0efec; --ink2: #c3c2b7; --muted: #a09e97; --grid: #2c2c2a; --base: #4a4a46; --series: #3987e5;
  --hover: rgba(255,255,255,.05); } }
main { max-width: 820px; margin: 0 auto; }
h1 { font-size: 1.6rem; line-height: 1.25; margin: 0 0 8px; }
h2 { font-size: 1.15rem; margin: 36px 0 6px; }
p, li { color: var(--ink2); }
.lead { font-size: 1.05rem; color: var(--ink); }
figure { margin: 12px 0 0; background: var(--surface); border: 1px solid var(--grid); border-radius: 8px; padding: 12px; }
figcaption { font-size: .85rem; color: var(--muted); margin-top: 6px; }
svg.dots { width: 100%; height: auto; display: block; }
.grid { stroke: var(--grid); stroke-width: 1; }
.reference { stroke: var(--ink2); stroke-width: 1.5; stroke-dasharray: 4 3; }
.axis { fill: var(--muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.label { fill: var(--ink); font-size: 13px; }
.value { fill: var(--ink2); font-size: 13px; font-variant-numeric: tabular-nums; }
.whisker { stroke: var(--series); stroke-width: 2; stroke-linecap: round; }
.dot { fill: var(--series); stroke: var(--surface); stroke-width: 2; }
.hit { fill: transparent; }
.row:hover .hit { fill: var(--hover); }
#tip { position: fixed; pointer-events: none; display: none; background: var(--surface); color: var(--ink);
  border: 1px solid var(--base); border-radius: 6px; padding: 6px 10px; font-size: 13px; max-width: 320px;
  box-shadow: 0 2px 8px rgba(0,0,0,.15); }
.scroll { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin-top: 10px; }
th, td { padding: 6px 8px; border-bottom: 1px solid var(--grid); text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--ink2); font-weight: 600; }
code { font-size: .9em; }
"""

SCRIPT = """
const tip = document.getElementById('tip');
document.querySelectorAll('.row').forEach(row => {
  row.addEventListener('mousemove', e => {
    tip.textContent = row.dataset.tip; tip.style.display = 'block';
    tip.style.left = Math.min(e.clientX + 14, innerWidth - 340) + 'px'; tip.style.top = (e.clientY + 14) + 'px';
  });
  row.addEventListener('mouseleave', () => { tip.style.display = 'none'; });
});
"""


def build_html(summaries, run):
    others = [s for s in summaries if s["name"] != BASELINE]
    by_difference = sorted(others, key=lambda s: s["difference"][0])
    best = by_difference[0]
    expert = next(s for s in summaries if s["name"] == BASELINE)
    paid = [s for s in summaries if s["cost"] > 0]
    llms = [s for s in others if s["decisions"] and s["name"] != "stub"]
    if llms:
        top = min(llms, key=lambda s: s["difference"][0])
        headline = f"{top['label']}: {finding(top)}"
    else:
        headline = f"{best['label']} {finding(best)}"
    difference_rows = [(s["label"], s["difference"][0], s["difference"][1], s["difference"][2],
                        f"{s['label']}: {s['difference'][0]:+.2f} points per deal against the Expert on the same "
                        f"{s['paired']} deals; 95% interval {s['difference'][1]:+.2f} to {s['difference'][2]:+.2f}")
                       for s in by_difference]
    mean_rows = [(s["label"], s["mean"][0], s["mean"][1], s["mean"][2],
                  f"{s['label']}: {s['mean'][0]:.2f} points per deal over {s['deals']} deals; "
                  f"95% interval {s['mean'][1]:.2f} to {s['mean'][2]:.2f}")
                 for s in summaries]
    table = ["<tr><th>Player</th><th>Deals</th><th>Points per deal</th><th>95% interval</th><th>Vs Expert</th><th>Margin vs Expert</th>"
             "<th>Took Q♠</th><th>Moons shot</th><th>Moons by others</th><th>API calls</th><th>Fallbacks</th><th>Input tokens</th>"
             "<th>Output tokens</th><th>Cost</th><th>Seconds per deal</th></tr>"]
    for s in summaries:
        versus = "" if s["difference"] is None else f"{s['difference'][0]:+.2f}"
        margin_text = "" if s["margin"] is None else f"{s['margin'][0]:+.2f}"
        table.append(
            f"<tr><td>{html.escape(s['label'])}</td><td>{s['deals']}</td><td>{s['mean'][0]:.2f}</td>"
            f"<td>{s['mean'][1]:.2f} to {s['mean'][2]:.2f}</td><td>{versus}</td><td>{margin_text}</td><td>{s['queen']:.0%}</td>"
            f"<td>{s['moons']}</td><td>{s['others_moons']}</td><td>{s['decisions'] or ''}</td><td>{s['fallbacks'] if s['decisions'] else ''}</td>"
            f"<td>{s['input_tokens'] or ''}</td><td>{s['output_tokens'] or ''}</td>"
            f"<td>{'$%.3f' % s['cost'] if s['cost'] else ''}</td><td>{s['seconds_per_deal']:.1f}</td></tr>")
    findings = "".join(f"<li><strong>{html.escape(s['label'])}</strong> {html.escape(finding(s))}.</li>" for s in by_difference)
    spreads = [s["difference_spread"] for s in others if s["paired"] > 1]
    spread_note = (f"Comparing on the same deals, the difference from the Expert varies by {min(spreads):.1f} to "
                   f"{max(spreads):.1f} points from deal to deal, so" if spreads else "So")
    needed = max(spreads) if spreads else 7
    deals_for_one = round((1.96 * needed) ** 2)
    total_cost = sum(s["cost"] for s in paid)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HEARTS benchmark: {html.escape(run)}</title><style>{STYLE}</style></head>
<body class="viz-root"><main>
<h1>LLM players against the 1986 Hearts Expert</h1>
<p class="lead">{html.escape(headline)}.</p>
<p>Each player sat in seat 1 against three copies of the Expert, on the same fixed deals. Hearts is a game
of avoiding points, so lower is better. API spend for this run was ${total_cost:.2f}.</p>

<h2 id="t1">Points per deal compared with the Expert, on the same cards</h2>
<figure>{dot_chart(difference_rows, "t1", 0, "same as the Expert", "points per deal, difference from the Expert (left of the line is better)")}
<figcaption>Dots are mean differences and lines are 95% bootstrap intervals over deals. An interval that
crosses the dashed line can't be told apart from the Expert.</figcaption></figure>
<ul>{findings}</ul>

<h2 id="t2">Points per deal</h2>
<figure>{dot_chart(mean_rows, "t2", 6.5, "6.5: an even share", "points per deal, in seat 1 against three Experts (lower is better)")}
<figcaption>A deal holds 26 points, so four equal players would average about 6.5 each. Players ran different
numbers of deals, which is why some intervals are wider.</figcaption></figure>

<h2>All the numbers</h2>
<div class="scroll"><table>{"".join(table)}</table></div>

<h2>How it was run</h2>
<ul>
<li><strong>The game:</strong> the 1986 code running in headless Medley, unchanged except for test advice: fixed shuffles
in place of <code>H.Shuffle</code> and no pause at the end of each trick. The report checks that every player was dealt the same cards.</li>
<li><strong>One long game:</strong> the pass direction follows the deal number, and the Expert opponents keep modelling
the other players across deals. The over score is set out of reach, so nobody plays for the end of a game, and this doesn't measure that skill.</li>
<li><strong>Scoring:</strong> a player's points for the deal, with a shot moon scoring -26 and nothing added to the others, as in the 1986 code.</li>
<li><strong>Margin:</strong> a player's points minus the average of the other three, compared with the Expert on the same deal. Points alone ignore an opponent's moon, which in a real game hurts you.</li>
<li><strong>Fallbacks:</strong> when a model gave no usable answer the seat played a safe legal card, and that deal still counts.</li>
<li><strong>Cost:</strong> tokens at each provider's listed price. Local models cost nothing here, apart from the machine.</li>
</ul>

<h2>What this can't tell you</h2>
<ul>
<li><strong>Small differences.</strong> {spread_note} telling apart players 1 point per deal apart would take about {deals_for_one} deals.</li>
<li><strong>What the models could do with more effort.</strong> Claude ran at low effort, and the local models are old.</li>
<li><strong>How a model plays against other opponents.</strong> The field here is three Experts, and results against people or a mixed table could differ.</li>
<li><strong>Repeatability of a single run.</strong> The models aren't deterministic, and each ran once.</li>
</ul>
<div id="tip" role="status"></div>
</main><script>{SCRIPT}</script></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", default="pilot")
    args = parser.parse_args()
    players = load_run(args.run)
    if BASELINE not in players:
        sys.exit(f"the run has no {BASELINE} baseline yet")
    check_same_cards(players)
    summaries = summarize(players)
    out = ROOT / "docs" / "benchmarks" / args.run
    (out / "decisions").mkdir(parents=True, exist_ok=True)
    with (out / "deals.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["player", "deal", "pass", "points", "seat2", "seat3", "seat4", "queen_taken_by_seat", "seconds"])
        for name, player in players.items():
            for r in player["rows"]:
                writer.writerow([name, r["deal"], r["pass"], *r["scores"], r["queen"], r["ms"] / 1000])
    for name, player in players.items():
        log = player["directory"] / "decisions.jsonl"
        if log.exists():
            with gzip.GzipFile(out / "decisions" / f"{name}.jsonl.gz", "wb", mtime=0) as f:
                f.write(log.read_bytes())
    (out / "report.html").write_text(build_html(summaries, args.run), encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summaries, indent=1))
    for s in summaries:
        print(f"{s['name']:13} n={s['deals']:<4} mean {s['mean'][0]:6.2f} [{s['mean'][1]:.2f},{s['mean'][2]:.2f}]  "
              f"diff {(s['difference'] or ('-',))[0] if s['difference'] is None else round(s['difference'][0], 2)} "
              f"Q {s['queen']:.0%} moons {s['moons']} fb {s['fallbacks']}/{s['decisions']} ${s['cost']:.3f} {s['seconds_per_deal']:.1f}s")
    print(out / "report.html")
    return 0


if __name__ == "__main__":
    sys.exit(main())
