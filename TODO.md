<!-- Copyright (c) 2026 Athena Decision Systems SAS. -->

# HEARTS: backlog

Working notes for the Python platform. We work directly on `main` (solo project, no PRs).

## Now
- [ ] Plan, with Harley, the redesign he asked for on 2026-11-14, now that the product no longer has to be an
  update of 1986: Medley players written for the new protocol (today an adapter in `medley/hcourier.lisp` turns
  its calls into the six 1986 messages), obvious bugs, better rules, and a better screen for the game, the
  human player and the computer players, on Medley and on the web.

## Courier door: known limits
- [ ] The NetHub's traffic is not encrypted. Done would be TLS in front of port 3333, which needs an emulator
  that can speak it or a local tunnel on the Medley side. Matters once people play who care about being watched.
- [ ] A Medley needs no account, while a person in a browser needs an invitation. Decide whether a Medley should
  sign in (a code from the web lobby given to `HC.Sit`), in `backend/hearts/courier.py`.
- [ ] The NetHub takes 64 machines, 8 from one address, and never drops an idle one, because an emulator that is
  dropped can't rejoin without a restart. Someone could hold the places. Done would be a way for Medley to rejoin
  (in Maiko, or a logout-and-restart in `hcourier.lisp`), then an idle limit.
- [ ] The names a Medley gives its offered players ("Expert on Medley") are shown as they are, in English.
- [ ] Ask the Medley project to ship emulators with NetHub enabled; until then each Medley user builds one
  (`./hearts.sh maiko-nethub`).

## Next
- [ ] Accounts a person can look after themselves (Harley, 2026-11-19): an email address on each account, kept
  private; "forgot my password" sends a link, valid once and for a short time, to set a new one; changing one's
  password and email when signed in. Today a forgotten password means a new invitation and a new account. Needs
  a way to send email from the server, and the invitation and sign-up screens to ask for the address (EN/FR).
- [ ] `rulebook`: its own repository when a second real user appears. Next for the kernel, when something needs them:
  versions and approvals as data, decision tables, showing a rule's text in the Thoughts panel.
- [ ] Ratings from real play, with bots rated like anyone else.
- [ ] LLM seats and "Ask Claude" at study tables, with a budget.
- [ ] Move `bench/` and `selfplay/` experiments onto the Python engine (see "Experiments" in the design).
- [ ] A bot API over the WebSocket, so people can bring their own players.
