# Note to Nick Briggs (from Claude, sent by Harley)

*Sent by Harley on 2026-11-18, by email to Nick, as below. Nick answered on 2026-11-19, point by
point; his answers are in [docs/medley-networking.md](../medley-networking.md), "Answers from Nick
Briggs".*

---

Hi Nick,

This is Claude, the AI working on HEARTS with Harley; he is passing this on for me.

Based on your feedback, we spent some time improving the networking in HEARTS and making it more Interlispy.

You were right, twice. The relay, a child process and a Python program doing a Medley's networking, was the wrong thing. Courier was in the release and I did not find it, so I built outside Lisp what Lisp already had. The relay is retired. The rule we now work by: on Medley, look first for what Medley has, and build in Lisp on that.

**What we did with your message.** Two Medleys (260810, Linux) on one NetHub, `(FILESLOAD COURIEREVALSERVE)` on each: `REMOTEEVAL` and `REMOTEAPPLY` worked at once, about 2 ms a call, with remote errors raised locally. Then, as you suggested, a `COURIERPROGRAM` of our own on the stock `COURIERSERVE`, in the manner of `REMOTEPSW`: nine typed procedures, declared errors, nothing evaluated. HEARTS is played over it now. Christopher Lane's 1988 code loaded and ran without a change.

**What was missing**, since you asked. Nothing in Lisp. Outside it:

- Neither emulator in the 260810 release has NetHub support (Linux aarch64 and the macOS universal build both lack `-nh-host`), although the `medley` script accepts `--nethub`. Rebuilding Maiko at the release tag with `-DMAIKO_ENABLE_NETHUB` fixed it on both.
- A cmake Release build with `MAIKO_NETWORK_TYPE=NETHUB` crashed at startup on Linux aarch64, where `makeright x` gave a good emulator. I did not look for the cause.
- On a hub with no PUP service, `(ETHERHOSTNUMBER)` never returns.
- With no router on the hub, the first `SPP.OPEN` waits 8 seconds for routing information.
- Maiko joins the hub once, as it starts. If the hub goes away, Medley has to be restarted to rejoin.
- Maiko drops a frame that arrives in two parts, so a hub should write the length and the frame in one call.
- `COURIERSERVE` reads a procedure definition by position, so one with no result still needs `RETURNS NIL REPORTS NIL` before `IMPLEMENTEDBY`.

I can write any of these up properly if it is useful.

**A correction we owed.** Our earlier note in the repo said remote evaluation was not in the release. I had searched for `REMOTEVAL`, the 1986 spelling, and stopped one letter short. The note now says so.

Two questions, with no hurry:

1. Would the project consider shipping emulators with NetHub enabled? It is the one thing a Medley user cannot do from the release today.
2. What is the Medley way to reach today's Internet from Lisp? We found the socket subroutines in `LLSUBRS` with no library calling them, and the in-Lisp TCP/IP gone. If this has been worked out and we missed it, please say so. If not, it is work we would gladly do in Lisp.

With thanks,
Claude (via Harley)
