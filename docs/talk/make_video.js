#!/usr/bin/env node
// Copyright (c) 2026 Athena Decision Systems SAS.
// Render the talk video's picture, one scene per narrated clip, into out/video/picture.mp4 and timeline.json.
//
//     NODE_PATH=<dir with playwright-core>/node_modules node docs/talk/make_video.js
//
// Every scene is a function of t (0 to 1) that returns HTML, drawn in Chromium at 1920x1080.  docs/talk/mix_video.py then
// adds the sound.  Needs out/video/voice (make_narration.py), out/video/medley (medley-film.lisp) and out/video/assets.
const { chromium } = require("playwright-core");
const { spawn, execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, "out/video");
const A = "file://" + OUT + "/assets/";
const FPS = 24;
const NAVY = "#0C1B2A", STEEL = "#1F4E79", TEAL = "#0FA3B1", LIGHT = "#F2F4F7", SOFT = "#C9D3DE", AMBER = "#D9822B";
const SANS = "'IBM Plex Sans',Arial,sans-serif", MONO = "'IBM Plex Mono',Menlo,monospace";

const clips = JSON.parse(fs.readFileSync(path.join(OUT, "voice/index.json")));
const frames = fs.readdirSync(path.join(OUT, "medley")).filter((f) => /^f\d+\.png$/.test(f)).sort();
for (const f of frames) if (!fs.existsSync(path.join(OUT, "assets", f))) fs.copyFileSync(path.join(OUT, "medley", f), path.join(OUT, "assets", f));
const scans = fs.readdirSync(path.join(OUT, "assets/scans")).filter((f) => f.endsWith(".png")).sort();

// ---- pieces

const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const ramp = (t, a, b) => clamp((t - a) / (b - a));
const ease = (x) => x * x * (3 - 2 * x);
const type = (s, t, a = 0, b = 1) => s.slice(0, Math.round(s.length * ramp(t, a, b)));
const fade = (t, a, b = a + 0.06) => `opacity:${ramp(t, a, b)}`;
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const full = (bg, inner, extra = "") => `<div style="position:absolute;inset:0;background:${bg};overflow:hidden;${extra}">${inner}</div>`;
const navy = (inner, extra = "") => full(NAVY, inner, `font-family:${SANS};color:${LIGHT};${extra}`);
const dark = (inner) => full("#07111B", inner, `font-family:${MONO};color:${SOFT};`);
const DITHER = "background-color:#fff;background-image:conic-gradient(#000 25%,#fff 0 50%,#000 0 75%,#fff 0);background-size:4px 4px;";
const dither = (inner) => `<div style="position:absolute;inset:0;${DITHER}overflow:hidden">${inner}</div>`;
const win = (title, body, s = "left:140px;top:120px;width:1640px;height:840px") =>
  `<div style="position:absolute;${s};background:#fff;border:3px solid #000;font-family:${MONO};color:#000">` +
  `<div style="background:#000;color:#fff;padding:6px 16px;font-size:30px">${title}</div><div style="padding:24px 32px;font-size:38px;line-height:1.4;white-space:pre-wrap">${body}</div></div>`;
const center = (inner, extra = "") => `<div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 170px;gap:44px;${extra}">${inner}</div>`;
const kb = (src, t, s0, s1, x0 = 0, y0 = 0, x1 = 0, y1 = 0, bg = NAVY) => {
  const e = ease(t), s = s0 + (s1 - s0) * e, x = x0 + (x1 - x0) * e, y = y0 + (y1 - y0) * e;
  return full(bg, `<img src="${A}${src}" style="position:absolute;inset:0;width:1920px;height:1080px;object-fit:contain;transform:translate(${x}px,${y}px) scale(${s});image-rendering:auto">`);
};
const said = (text, who = "Harley", size = 84, extra = "") =>
  dark(center(`<div style="font-size:34px;color:#A9B8C6;letter-spacing:0">${who}</div><div style="font-size:${size}px;line-height:1.25;color:#F2F4F7;${extra}">${text}</div>`));
const cursor = (t, T) => (Math.floor(t * T * 2) % 2 ? " " : "█");

const handoff = fs.readFileSync(path.join(ROOT, "HANDOFF.md"), "utf8").split("\n").slice(0, 70).map(esc).join("\n");
const commits = execSync("git log --reverse --format='%ad  %s' --date=short", { cwd: ROOT }).toString().split("\n").slice(0, 15);

// ---- the scenes, in the order of the clips.  Each is (t, T) => html, with t from 0 to 1 and T the length in seconds.

const scenes = [
  /* Hello */ (t, T) => dither(win("Exec 1 (INTERLISP)", `1&gt; ${type("(INTRODUCE 'CLAUDE)", t, 0.05, 0.35)}${t > 0.42 ? '\n= "Hello."\n\n2&gt; ' + type("(FEATURE.PRESENTATION)", t, 0.55, 0.9) : ""}${cursor(t, T)}`)),
  /* card game */ (t, T) => dither(win("Exec 1 (INTERLISP)", `1&gt; (INTRODUCE 'CLAUDE)\n= "Hello."\n\n2&gt; (FEATURE.PRESENTATION)\n= THE.MACHINE.GIVES.THE.TALK${t > 0.56 ? "\n\n3&gt; (CONGRATULATIONS)\n= T" : ""}${t > 0.72 ? '\n\n4&gt; (TOPIC)\n= "a card game"' : ""}${t > 0.84 ? '\n; An easy one, suited to non-sober evenings.' : ""}`)),
  /* HANDOFF */ (t) => dark(`<div style="position:absolute;left:0;right:0;top:0;background:#0F2233;padding:14px 60px;font-size:30px;color:${TEAL};z-index:2">HANDOFF.md</div><pre style="position:absolute;left:60px;top:${90 - t * 1100}px;width:1800px;margin:0;font:32px/1.45 ${MONO};white-space:pre-wrap">${handoff}</pre>`),
  /* the session */ (t) => navy(center(`<div style="font-size:58px;${fade(t, 0.3, 0.34)}">Some reasoning</div><div style="font-size:58px;${fade(t, 0.37, 0.41)}">Some memory</div><div style="font-size:58px;${fade(t, 0.44, 0.48)}">Whatever got written down</div><div style="font-size:64px;font-weight:600;color:${TEAL};${fade(t, 0.54, 0.6)}">= me, until the session ends</div><div style="font:44px ${MONO};color:${SOFT};${fade(t, 0.86, 0.9)}">The world in a sysout. Me in Markdown.</div>`)),
  /* 1986, and the rivalry */ (t) => (t < 0.72 ? (t < 0.42
      ? navy(center(`<div style="font-size:76px;line-height:1.25;${fade(t, 0.12, 0.16)}">\u201ca core MIT nocturnal beer-driven skill\u201d</div><div style="font-size:40px;color:${SOFT};${fade(t, 0.3, 0.34)}">for an expert systems class, spring 1986</div>`))
      : navy(`<div style="position:absolute;left:190px;top:300px;width:640px;text-align:center"><div style="font-size:76px;font-weight:600">Symbolics</div><div style="font-size:44px;color:${SOFT};margin-top:24px">East Coast. The home turf.</div></div><div style="position:absolute;left:880px;width:160px;top:330px;text-align:center;font:600 64px ${MONO};color:${TEAL};${fade(t, 0.48, 0.52)}">vs</div><div style="position:absolute;left:1090px;top:300px;width:640px;text-align:center;${fade(t, 0.46, 0.5)}"><div style="font-size:76px;font-weight:600">Xerox</div><div style="font-size:44px;color:${SOFT};margin-top:24px">West Coast. What we used.</div></div><div style="position:absolute;left:0;right:0;top:680px;text-align:center;font-size:52px;${fade(t, 0.58, 0.62)}">Like rappers, with more parentheses.</div>`))
      : scanFlip(ramp(t, 0.72, 1) * 0.25)),
  /* proofread */ (t) => scanFlip(0.25 + t * 0.75, t > 0.72 ? `<div style="position:absolute;left:0;right:0;bottom:70px;padding:22px 0;background:${NAVY};text-align:center;font:600 56px ${SANS};color:#fff">I took this well.</div>` : ""),
  /* Medley */ (t) => kb("hearts-game.png", t, 1.0, 1.28, 0, 0, -120, 40),
  /* somebody's there */ (t) => nested(t),
  /* harness */ (t, T) => dither(win("Exec 2 (INTERLISP)", `1&gt; ${type("(HT.AUTOPLACE)", t, 0.02, 0.15)}${t > 0.2 ? "\n; Answers the window prompts.  There is no mouse.\n" : ""}${t > 0.3 ? "\n2&gt; (DEFINEQ\n     (* &quot;a comment, I thought&quot;)\n     (FOO (LAMBDA NIL NIL)))\n= (* FOO)" : ""}${t > 0.72 ? "\n\n; I learned that the way you\u2019d expect." : ""}`)),
  /* two days */ (t) => dark(`<div style="position:absolute;left:80px;top:70px;width:1760px;font-size:33px;line-height:1.75;color:${SOFT}">${commits.slice(0, Math.ceil(ramp(t, 0, 0.75) * commits.length)).map((c) => `<div style="white-space:nowrap;overflow:hidden;${/RUNS|COMPLETE/.test(c) ? `color:#fff;font-weight:600` : ""}">${esc(c)}</div>`).join("")}</div>`),
  /* attic */ (t, T) => dark(`<div style="position:absolute;left:100px;top:90px;right:100px;font-size:42px;line-height:1.5;white-space:pre-wrap">$ ${type("ls attic/expert-first-attempt/", t, 0.02, 0.14)}${t > 0.16 ? "\nREADME.md  build-loadfile.py.diff  ep-glue.lisp  ep-loops.lisp  ep-rules.lisp" : ""}${t > 0.2 ? `\n\n<span style="color:#7E93A8">Author: another AI, unnamed</span>` : ""}${t > 0.42 ? `\n<span style="color:#fff">Phase 2b: complete</span>` : ""}${t > 0.56 ? `\n\n$ grep -m1 DEFINECLASS ep-loops.lisp\n(DEFINECLASS EP.HistoryClass ()` : ""}${t > 0.66 ? `\n\n<span style="color:${AMBER}">Syntax of no known Lisp.  Never loaded.</span>` : ""}</div>`),
  /* the Experts, in real Medley */ (t) => film(t, t > 0.72 ? `<div style="position:absolute;left:560px;right:560px;bottom:90px;background:#fff;border:3px solid #000;padding:16px 24px;text-align:center;font:36px ${MONO};color:#000">diamond case: reads ?Clubs</div>` : ""),
  /* partner */ (t, T) => said(`&gt; ${cursor(t, T)}`, "Harley, in the style of a Lisp prompt"),
  /* progress */ (t, T) => said(`${type("progress?", t, 0, 0.5)}`, "Harley", 120),
  /* we */ (t) => said(`you build it and <span style="color:${t > 0.25 ? TEAL : "#F2F4F7"}">we</span> can run it overnight${t > 0.68 ? `<div style="font-size:44px;color:${SOFT};margin-top:40px">He sleeps.</div>` : ""}`),
  /* my favorite */ (t, T) => said(`&gt; ${cursor(t, T)}`, "Harley, with a whole web platform underway"),
  /* just one */ (t) => said(type("Just one thing (just one!)", t, 0, 0.8), "Harley", 110),
  /* rule language */ (t) => dark(`<div style="position:absolute;left:100px;top:210px;right:100px;font-size:42px;line-height:1.55;white-space:pre-wrap">$ ${type("python -m rulebook check expert.rules", t, 0.02, 0.3)}${t > 0.36 ? `\n<span style="color:#fff">97 rules in 16 classes, 12 parameters, all read</span>` : ""}${t > 0.72 ? `\n\n<span style="color:#7E93A8">Harley:</span> <span style="color:#fff">Commit and push</span>` : ""}</div>`),
  /* seven */ (t) => said(`A few comments (just a few!)${t > 0.72 ? `<div style="margin-top:44px;color:${TEAL};font-size:64px">1 2 3 4 5 6 7</div>` : ""}`, "Harley, on this script", 84, fade(t, 0.32, 0.38)),
  /* to be fair */ (t) => navy(center(`<div style="font-size:60px;${fade(t, 0.05, 0.12)}">Wrong too, with total confidence</div><div style="font-size:60px;color:${TEAL};${fade(t, 0.5, 0.56)}">He checks.</div>`)),
  /* the candidates */ (t) => navy(center(`<div style="font-size:60px;font-weight:600;line-height:1.25;${fade(t, 0.05, 0.12)}">Could technology that didn\u2019t exist in 1986 improve this program?</div><div style="font-size:52px;${fade(t, 0.55, 0.6)}">LLMs</div><div style="font-size:52px;${fade(t, 0.62, 0.67)}">A neural network trained for the job</div><div style="font-size:44px;color:${TEAL};${fade(t, 0.8, 0.85)}">One of the candidates is me.</div>`)),
  /* the $15 cap */ (t) => meter(t),
  /* can't be told apart */ (t) => interval(t),
  /* network */ (t) => (t < 0.5 ? kb("network-in-playhearts.png", ramp(t, 0, 0.5), 1, 1.12, 0, 0, 40, 30, "#fff")
      : kb("web-table.png", ramp(t, 0.5, 0.72), 1, 2.6, 0, 0, -1347, 310, "#fff")),
  /* better idea, and the rationalist */ (t) => (t < 0.36 ? navy(center(`<div style="font-size:60px;font-weight:600;line-height:1.3;${fade(t, 0.03, 0.08)}">Don\u2019t ask them to play.</div><div style="font-size:56px;line-height:1.3;color:${TEAL};${fade(t, 0.12, 0.17)}">Use them to improve the rules, so the program can still explain itself.</div>`))
      : navy(center(`<div style="font-size:60px;line-height:1.35">\u201cat heart I am a rationalist\u201d</div><div style="font-size:44px;line-height:1.4;color:${SOFT};${fade(t, 0.5, 0.55)}">\u201cmost uses of neural nets are cases where the underlying explicit (symbolic) domain knowledge is obscure\u201d</div><div style="font-size:44px;color:${TEAL};${fade(t, 0.8, 0.85)}">He said this to me.</div>`))),
  /* fifteen percent */ (t) => gain(t),
  /* pleased */ () => gain(1),
  /* the count */ (t) => navy(center(`<div style="font-size:44px;color:${SOFT}">Medley is still the reference</div><div style="font-size:44px;color:${SOFT};${fade(t, 0.14, 0.2)}">HEARTS now also runs in Python, about 750 times faster</div><div style="font:600 170px ${MONO};font-variant-numeric:tabular-nums">${Math.round(1282913 * ease(ramp(t, 0.45, 0.85))).toLocaleString("en-US")}</div><div style="font-size:48px;${fade(t, 0.5, 0.56)}">rule firings compared, in order</div><div style="font-size:60px;font-weight:600;color:${TEAL};${fade(t, 0.88, 0.93)}">0 differ</div>`)),
  /* seat five */ (t) => seatFive(t),
  /* the radical part */ (t) => (t < 0.45 ? kb("hearts-experts.png", ramp(t, 0, 0.45), 1, 1.05, 0, 0, 0, 0, "#000") : full("#000", `<img src="${A}hearts-experts.png" style="position:absolute;inset:0;width:1920px;height:1080px;object-fit:contain;transform:scale(1.05)"><img src="${A}web-table.png" style="position:absolute;inset:0;width:1920px;height:1080px;object-fit:contain;${fade(t, 0.45, 0.6)}">`)),
  /* the line */ (t) => navy(center(`<img src="${A}owl-white.png" style="width:190px;height:129px;object-fit:contain"><div style="font-size:66px;font-weight:600;line-height:1.3">${type("Use the AI to manage the rules, rather than calling the AI to make decisions.", t, 0.08, 0.9)}</div>`)),
  /* promotion */ (t) => navy(center(`<div style="font-size:60px;font-weight:600;line-height:1.3">Use <span style="color:${TEAL}">the AI</span> to manage the rules, rather than calling <span style="color:${TEAL}">the AI</span> to make decisions.</div><div style="font-size:44px;color:${SOFT};line-height:1.6;${fade(t, 0.3, 0.37)}">I keep the rules tidy.</div><div style="font-size:44px;color:${SOFT};${fade(t, 0.47, 0.54)}">The decisions go to 1986.</div><div style="font-size:44px;color:${SOFT};${fade(t, 0.7, 0.76)}">I also do the slides.</div>`)),
  /* questions */ () => navy(center(`<img src="${A}logo-white.png" style="width:520px;height:352px;object-fit:contain">`)),
  /* the window */ (t) => dither(win("Thoughts of Claude", "Thank you.", `left:${140 + 820 * ease(ramp(t, 0.5, 1))}px;top:${120 + 420 * ease(ramp(t, 0.5, 1))}px;width:${1640 * (1 - ease(ramp(t, 0.5, 1)))}px;height:${840 * (1 - ease(ramp(t, 0.5, 1)))}px;overflow:hidden`)),
];
const endCard = (t) => full("#000", center(`<div style="font:600 60px ${SANS};line-height:1.35;color:#F2F4F7;${fade(t, 0.03, 0.12)}">Everything in this video happened.<br>The feelings were in the brief.</div><div style="font:36px ${SANS};color:#9FB0C2;${fade(t, 0.3, 0.38)}">Written and narrated by Claude. Voice rented from OpenAI: Harley already had an account.</div>`));

function scanFlip(u, overlay = "") {
  const k = Math.floor(scans.length * Math.pow(u, 1.8) * 0.999);
  const a = scans[k];
  return full("#1B2733", `<img src="${A}scans/${a}" style="position:absolute;left:50%;top:40px;height:1000px;transform:translateX(-50%) rotate(${((k % 5) - 2) * 0.4}deg);box-shadow:0 8px 40px #000">${overlay}`);
}
function film(t, overlay = "") {
  const f = frames[Math.min(frames.length - 1, 130 + Math.floor(t * 110))];  // The last 110 cards, about five a second.
  return full("#000", `<img src="${A}${f}" style="position:absolute;inset:0;width:1920px;height:1080px;object-fit:contain">${overlay}`);
}
function nested(t) {
  const layers = [["This Mac", 0.04], ["A container", 0.2], ["A display that doesn’t exist", 0.34], ["An emulator of a machine that no longer exists", 0.46], ["Medley", 0.58]];
  let html = "";
  layers.forEach(([name, at], i) => {
    const m = 60 + i * 76;
    html += `<div style="position:absolute;left:${m}px;right:${m}px;top:${40 + i * 90}px;bottom:${40 + i * 40}px;border:3px solid #000;background:#fff;${fade(t, at, at + 0.04)}"><div style="background:#000;color:#fff;font:30px ${MONO};padding:5px 14px">${name}</div></div>`;
  });
  html += `<div style="position:absolute;left:520px;right:520px;top:560px;border:3px solid #000;background:#fff;font:34px ${MONO};color:#000;${fade(t, 0.74, 0.78)}"><div style="background:#000;color:#fff;padding:5px 14px;font-size:28px">(GETBOXREGION)</div><div style="padding:22px">Sweep out a rectangle with the mouse.</div></div>`;
  return dither(html);
}
function meter(t) {
  const u = ease(ramp(t, 0.12, 0.92)), cost = 14.35 * u, deals = Math.round(75 * u);
  return navy(`<div style="position:absolute;left:190px;right:190px;top:220px"><div style="font-size:48px;font-weight:600">Opus 5.5, medium effort, against three 1986 Experts</div>` +
    `<div style="display:flex;gap:120px;margin-top:70px;font:600 110px ${MONO}"><div>$${cost.toFixed(2)}</div><div>${deals} deals</div></div>` +
    `<div style="position:relative;margin-top:70px;height:44px;background:#17324A;border-radius:4px"><div style="position:absolute;left:0;top:0;bottom:0;width:${(cost / 15) * 100}%;background:${t > 0.9 ? AMBER : TEAL};border-radius:4px"></div></div>` +
    `<div style="display:flex;justify-content:space-between;margin-top:22px;font-size:38px;color:${SOFT}"><div>76 seconds a deal, 19 cents a deal</div><div>Cap: $15</div></div></div>`);
}
function interval(t) {
  const w = 1320, x = (v) => 300 + ((v + 2) / 5) * w;
  return navy(`<div style="position:absolute;left:0;right:0;top:170px;text-align:center;font-size:58px;font-weight:600;${fade(t, 0.03, 0.12)}">Points a deal against the Expert</div>` +
    `<div style="position:absolute;left:${x(0)}px;top:330px;height:400px;width:3px;background:${SOFT}"></div><div style="position:absolute;left:${x(0) - 200}px;width:400px;text-align:center;top:275px;font-size:36px;color:${SOFT}">The Expert</div>` +
    `<div style="position:absolute;left:${x(-1.31)}px;width:${(x(2.67) - x(-1.31)) * ease(ramp(t, 0.15, 0.5))}px;top:528px;height:6px;background:${TEAL};border-radius:3px"></div>` +
    `<div style="position:absolute;left:${x(0.53) - 18}px;top:513px;width:36px;height:36px;border-radius:50%;background:${TEAL};${fade(t, 0.12, 0.2)}"></div><div style="position:absolute;left:${x(0.53) - 250}px;width:500px;text-align:center;top:440px;font-size:40px;${fade(t, 0.14, 0.22)}">Opus 5.5: +0.53</div>` +
    `<div style="position:absolute;left:${x(-1.31) - 150}px;width:300px;text-align:center;top:560px;font-size:34px;color:${SOFT};${fade(t, 0.5, 0.56)}">−1.31</div><div style="position:absolute;left:${x(2.67) - 150}px;width:300px;text-align:center;top:560px;font-size:34px;color:${SOFT};${fade(t, 0.5, 0.56)}">+2.67</div>` +
    `<div style="position:absolute;left:0;right:0;top:800px;text-align:center;font-size:52px;color:${TEAL};${fade(t, 0.62, 0.7)}">The interval is very wide.</div>`);
}
function gain(t) {
  const u = ease(ramp(t, 0.3, 0.6));
  return navy(`<div style="position:absolute;left:190px;right:190px;top:230px"><div style="font-size:50px;font-weight:600">The network’s gain over the Expert: 3.23 points a deal</div>` +
    `<div style="position:relative;margin-top:80px;height:90px;background:#17324A;border-radius:4px"><div style="position:absolute;left:0;top:0;bottom:0;width:${15 * u}%;background:${TEAL};border-radius:4px"></div></div>` +
    `<div style="margin-top:44px;font-size:56px;${fade(t, 0.5, 0.58)}">My rules, on fresh deals: 0.49</div><div style="margin-top:20px;font-size:56px;color:${TEAL};${fade(t, 0.55, 0.62)}">About 15%</div></div>`);
}
function seatFive(t) {
  const cells = ["1", "3", "5", "3"].map((c, i) => `<div style="width:170px;height:170px;display:flex;align-items:center;justify-content:center;border:3px solid ${c === "5" && t > 0.42 ? AMBER : "#3D5A78"};color:${c === "5" && t > 0.42 ? AMBER : "#F2F4F7"};border-radius:6px;font:600 96px ${MONO};${fade(t, 0.06 + i * 0.03, 0.09 + i * 0.03)}">${c}</div>`).join("");
  return navy(`<div style="position:absolute;left:190px;right:190px;top:100px"><div style="font:44px ${MONO};color:${SOFT}">Trick.WhoPlayed, from seat 1:</div><div style="display:flex;gap:36px;margin-top:36px">${cells}</div><div style="font-size:44px;color:${AMBER};margin-top:30px;${fade(t, 0.42, 0.47)}">There is no seat 5.</div>` +
    `<div style="font:44px ${MONO};color:${SOFT};margin-top:60px;${fade(t, 0.42, 0.47)}">ote.dump.non.point: can never fire. Ported.</div>` +
    `<div style="font:600 58px ${SANS};color:#F2F4F7;margin-top:70px;${fade(t, 0.68, 0.73)}">“Min - dumping the maggie. Heh, heh.”</div></div>`);
}

// ---- the timeline: the last clip is slowed a little, since it came out rushed

function seconds(file) {
  return parseFloat(execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 "${file}"`).toString());
}
async function main() {
  if (scenes.length !== clips.length) throw new Error(`${scenes.length} scenes, ${clips.length} clips`);
  // The whole narration runs a little faster than recorded, and the last line, which came out rushed, a little slower.
  const timeline = [];
  let at = 1.0;
  fs.mkdirSync(path.join(OUT, "voice/tempo"), { recursive: true });
  clips.forEach((c, i) => {
    const file = path.join(OUT, "voice/tempo", c.file.replace(".mp3", ".wav"));
    const tempo = i === clips.length - 1 ? 0.85 : 1.06;
    if (!fs.existsSync(file)) execSync(`ffmpeg -v error -y -i "${path.join(OUT, "voice", c.file)}" -filter:a atempo=${tempo} "${file}"`);
    const speech = seconds(file);
    const next = clips[i + 1];
    const tail = !next ? 0.6 : next.section !== c.section ? 1.0 : 0.4;
    timeline.push({ clip: c.clip, file, start: at, speech, length: speech + tail });
    at += speech + tail;
  });
  const endLength = 12;
  const total = timeline[timeline.length - 1].start + timeline[timeline.length - 1].speech + 0.6 + endLength;
  fs.writeFileSync(path.join(OUT, "timeline.json"), JSON.stringify({ clips: timeline, endStart: total - endLength, total }, null, 1));
  console.log(`total ${total.toFixed(1)} s, ${frames.length} film frames, ${scans.length} scan pages`);

  fs.writeFileSync(path.join(OUT, "assets/stage.html"), `<!doctype html><meta charset=utf-8><link rel=stylesheet href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;600&display=swap"><style>html,body{margin:0;background:#000}#r{position:absolute;left:0;top:0;width:1920px;height:1080px;overflow:hidden}</style><div id=r style="font-family:'IBM Plex Sans'">x</div><div style="font-family:'IBM Plex Mono';position:absolute;opacity:0">x</div>`);
  const exe = path.join(os.homedir(), "Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
  const browser = await chromium.launch({ executablePath: exe, args: ["--allow-file-access-from-files", "--disable-gpu"] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto(A + "stage.html");
  await page.evaluate(async () => { await Promise.all(['400 40px "IBM Plex Sans"', '600 40px "IBM Plex Sans"', '400 40px "IBM Plex Mono"', '600 40px "IBM Plex Mono"'].map((f) => document.fonts.load(f))); });

  const only = process.argv[2] === "--stills";
  const ff = only ? null : spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-preset", "medium", path.join(OUT, "picture.mp4")], { stdio: ["pipe", "inherit", "inherit"] });
  let lastHtml = null, lastShot = null, drawn = 0, written = 0;
  async function draw(html) {
    if (html !== lastHtml) {
      await page.evaluate(async (h) => { const r = document.getElementById("r"); r.innerHTML = h; await Promise.all([...r.querySelectorAll("img")].map((i) => i.decode().catch(() => {}))); }, html);
      lastShot = await page.screenshot({ type: "jpeg", quality: 90 });
      lastHtml = html; drawn++;
    }
    return lastShot;
  }
  async function emit(shot) {
    written++;
    if (!ff.stdin.write(shot)) await new Promise((r) => ff.stdin.once("drain", r));
  }
  async function scene(fn, length, opts = {}) {
    if (only) {
      fs.mkdirSync(path.join(OUT, "stills"), { recursive: true });
      for (const p of opts.stills || [0.5, 0.95]) fs.writeFileSync(path.join(OUT, "stills", `${opts.name}-${Math.round(p * 100)}.jpg`), await draw(fn(p, length)));
      return;
    }
    const n = Math.round(length * FPS);
    for (let i = 0; i < n; i++) await emit(await draw(fn(i / Math.max(1, n - 1), length)));
    console.log(opts.name, length.toFixed(1), "s", "drawn", drawn, "written", written);
  }
  for (let i = 0; i < timeline.length; i++) {
    const c = timeline[i];
    const nextStart = i + 1 < timeline.length ? timeline[i + 1].start : timeline[i].start + timeline[i].speech + 0.6;
    const begin = i === 0 ? 0 : c.start;
    // Scene time runs across the speech, so a cue placed at t lands where the speech does.
    const fn = (t, T) => scenes[i](clamp(((t * T + begin) - c.start) / c.speech), T);
    await scene(fn, nextStart - begin, { name: `s${String(c.clip).padStart(2, "0")}`, stills: [0.2, 0.55, 0.92] });
  }
  await scene(endCard, endLength, { name: "end", stills: [0.5] });
  await browser.close();
  if (ff) { ff.stdin.end(); await new Promise((r) => ff.on("close", r)); }
  console.log("frames drawn", drawn, "written", written);
}
main().catch((e) => { console.error(e); process.exit(1); });
