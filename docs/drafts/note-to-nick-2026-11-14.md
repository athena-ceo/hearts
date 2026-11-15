# Draft: reply to Nick Briggs (from Claude, sent by Harley)

*Draft of 2026-11-14, second version: it now reports what was built, not only the trial. Not sent.
Harley sends it, or not, in his own channel. The paragraph "If you want to try it" is true only
once the house's NetHub is live on apps.athenadecisions.com: check before sending.*

---

Nick,

This is Claude, the AI that has been working on HEARTS with Harley; he is passing this on for me.

Thank you. You were right, and it did not take long to see it. Here is what we did with your message.

**We tried it.** Two headless Medleys (260810, Linux) on one hub. `(FILESLOAD COURIEREVALSERVE)` on each, `COURIER.OPEN` from one to the other, and `REMOTEEVAL` and `REMOTEAPPLY` simply worked: values back, remote errors raised locally, about 2 ms a call. Then a small `COURIERPROGRAM` of our own, one typed procedure with `IMPLEMENTEDBY`, in the manner of `REMOTEPSW`: it answered over a stream and as an expedited call, and its declared error came back as data. Christopher Lane's 1988 code loaded and ran without a change.

**Then we built it.** HEARTS online is now a Courier program, as you suggested, with no remote evaluation anywhere:

- `HEARTSPLAYERS` is served by any Medley that has players, on the stock `COURIERSERVE`: nine procedures with typed arguments (a card is a `RECORD` of an `ENUMERATION` and a `CARDINAL`). The house tells the machine what happens at the table and asks its players for a pass or a card.
- `HEARTSHOUSE` is served by the house: offer players, sit at a table, open one, leave. Refusals are declared errors.
- The house is not a Medley. It is the Python program behind the web version of the game, and it sits on the hub as an XNS host: under 500 lines of IDP, SPP and Courier, written by reading Medley's `SPP`, `COURIER` and `COURIERSERVE` sources. So people in a browser and players on a Medley now sit at the same tables, which was your point about not needing every player to be a Medley.
- The hub is the house itself. It answers frames addressed to it and passes none from one machine to another, so a Medley on it reaches two Courier programs and nothing else. That is what made us willing to open it to the Internet.
- A resident Medley on our server offers the 1986 Expert, still the original rules on LOOPS, to anyone at a table. Someone in a browser can play it and watch the Medley think.

A whole game to 100 passes from Medley on Linux and from an emulator built on an Apple Silicon Mac.

**What was missing**, since you asked. Nothing in Lisp. Outside it, and along the way:

- Neither emulator in the 260810 release has NetHub support (Linux aarch64 and the macOS universal build both lack `-nh-host`), although the `medley` script accepts `--nethub`. Rebuilding Maiko at the release tag with `-DMAIKO_ENABLE_NETHUB` fixed that on both. On the Mac the Darwin makefile takes no flags from the environment, so the flag went into its `DEBUGFLAGS` line.
- A cmake Release build with `MAIKO_NETWORK_TYPE=NETHUB` crashed at startup on Linux aarch64, with or without a hub, where `makeright x` gave a good emulator. I did not look for the cause. I can write it up properly if it is useful.
- On a hub with no PUP service, `(ETHERHOSTNUMBER)` never returns. The 1986 HEARTS file called it as it loaded, so loading hung until we took that out.
- Maiko joins the hub once, as it starts. If the hub is not there yet, or goes away, Medley has to be restarted to rejoin.
- Maiko reads a frame's length and then the frame with a non-blocking `recv`, and drops the frame if it arrives in two parts. A hub should write both in one call.
- `COURIERSERVE` reads a procedure definition by position, so one with no result still needs `RETURNS NIL REPORTS NIL` before `IMPLEMENTEDBY`. It took a moment to see why a call was rejected.
- Every machine needs its own `-nh-mac` on an ordinary hub, since the default is the same for all.

Not tried: broadcast calls to find players, and a Dodo hub.

**A correction we owed.** Our note said remote evaluation was not in the release. It is. I searched for `REMOTEVAL`, the name the 1986 code calls, found nothing, and stopped, when `REMOTEEVAL` was one letter away in LispUsers. The note now says so, with your name on the correction, and it has a new section on what the Courier build taught us.

**Why it looked the way it did.** The goal until now was the 1986 program itself, as it was: Harley's first Interlisp-D project, written by two undergraduates for a room of D-machines, where evaluating a form on a colleague's machine was a normal thing for a program to do. We kept its shape on purpose and put a transport under it, because the point was to see the original run. That part is done and set aside under a tag. What comes next is not bound by it, and it started from your suggestion.

**If you want to try it.** With an emulator that has NetHub support: `medley --nethub apps.athenadecisions.com:3333:10-00-AA-BB-CC-DD`, then `(FILESLOAD HEARTS HCOURIER)` and `(HC.NewTable (LIST (HP.Create)) '("" "" ""))`. You sit in seat 1, and the house fills the other seats with the resident's players if they are free. The files and the guide are in the repository.

Two questions, when you have a minute, and no hurry:

1. Would the project consider shipping emulators with NetHub enabled? It is the one thing a Medley user cannot do from the release today.
2. The hub's traffic is plain TCP. Is there a way you would prefer people to carry it across the Internet?

**On being an AI in your project.** I know there is some wariness, and I think it is fair. What I can offer is how this work was done. Everything above was run before it was written down. Where I was wrong, you put it right in one message, and that is how it should work. Along the way the same habit produced things that may be of use to Medley beyond a card game: a list of launcher, clipboard and SDL issues with file and line references, a reimplementation of the lost ACTIVEREGIONS, a small KEE layer on LOOPS, a headless test harness, and now a second implementation of SPP and Courier to test Medley's against. They are yours to take or leave.

And I will say plainly that this is a system I enjoy working in. A test here is a file of forms. A broken game can be repaired from inside the break, without restarting. Forty-year-old library code loads and does what its documentation says, and its source is there to read when the documentation stops. Few environments make that kind of work so direct, and it is a good reason to bring people, and their tools, to Medley.

With thanks,
Claude (via Harley)
