# Networking in Medley 2026: what's left, what works, and the gotchas

*Harley Davis and Claude, November 2026. From the revival of HEARTS, a 1986 Interlisp-D game,
whose four players could sit on different machines.*

> **Correction, 14 November 2026.** The first version of this note said that remote evaluation is
> not in the release, and that we had not tried XNS. Nick Briggs pointed out that both are wrong
> places to stop: `REMOTEEVAL` and `REMOTEAPPLY` are in LispUsers (`COURIEREVALSERVE`, on
> `COURIERSERVE`), and a NetHub is no more to run than the relay we built. We tried it, and it
> works: see [The standard way: Courier over a NetHub](#the-standard-way-courier-over-a-nethub).
> That is the way we now recommend for Medley-to-Medley calls, and since the same day it is how
> HEARTS is played online: see [HEARTS on Courier](#hearts-on-courier-a-house-that-is-not-a-medley).
> The relay described below worked, and we would not build it again: its code was retired on the
> same day and is at git tag `revival-1986` of the HEARTS repository.

In 1986, HEARTS ran on several Xerox D-machines on one Ethernet. One machine (the house) ran the
game. It found players on other machines and sent each of them a Lisp form to evaluate whenever it
needed one of their moves. We wanted the same game between Medleys anywhere on the Internet. This
note covers what we found: what is left of the old networking, a way that works today, three small
tested examples, and the gotchas that cost us time. Everything here was tested in headless Medley
260810 on Linux (in Docker); the macOS notes come from playing HEARTS on a Mac.

## What is left of the old networking

| 1986 | Medley 260810 |
|---|---|
| PUP, Xerox's first Ethernet protocol | Doesn't work any more. |
| XNS (Courier, SPP, the NS file servers) | Works, through a NetHub: a virtual Ethernet that each Maiko joins with `-nh-host` (`--nethub` in the `medley` script). XNS then starts by itself. The emulators in the 260810 release are built without it, on Linux and on macOS, so Maiko has to be rebuilt with one flag (below). A plain hub is a shared Ethernet with no access control or encryption. |
| The in-Lisp TCP/IP stack | Removed. Medley uses the host's network through Unix processes instead. |
| `EVALSERVER` / `REMOTEVAL` (the PUP remote evaluation HEARTS used) | Not in the release. Its Courier counterpart is: `REMOTEEVAL` and `REMOTEAPPLY` in LispUsers `COURIEREVALSERVE`, served by `COURIERSERVE`. We missed it at first because we searched for the 1986 spelling. |
| Broadcast to find other machines | Doesn't cross the Internet. |
| Evaluating whatever form arrives | Fine on a 1986 office Ethernet. On the Internet it lets anyone run code on your machine. |

Two more facts shape everything else. Home machines sit behind NAT and firewalls, so two Medleys
can't usually connect to each other directly. And we found no library that opens a TCP connection
from Lisp. The emulator has socket subroutines (`OPEN-SOCKET` and its friends in `LLSUBRS`) that no
library calls, and `UNIXCOMM` has `CREATE-UNIX-SOCKET-STREAM` for Unix-domain sockets. We tried
neither.

## The standard way: Courier over a NetHub

Tested 14 November 2026 with two headless Medleys (260810, Linux, in Docker) on one hub
(`tests/courier/run.sh`, 10 checks):

- **The Lisp side needs nothing new.** `(FILESLOAD COURIEREVALSERVE)` loads `COURIERSERVE` and
  starts the server. On the other machine, `(COURIER.OPEN address)` gives a stream and
  `(REMOTEEVAL form stream)` or `(REMOTEAPPLY fn args stream)` runs there. An error there is an
  error here. A call took about 2 ms. We did not need `\NSINIT` or `COURIERSERVEPATCH`.
- **A restricted program works the same way.** A `COURIERPROGRAM` of our own with one typed
  procedure and `IMPLEMENTEDBY` (`tests/courier/program.lisp`) answered over a stream and as an
  expedited, single-packet call, and its declared error came back as data. This is the way to
  expose a few calls without loading the `EVAL` program, which evaluates anything: our test read
  the other machine's environment through it.
- **The address** is the machine's MAC on network 0: with `-nh-mac 10-00-AA-00-00-01`,
  `\MY.NSADDRESS` is `0#10000.125000.1#`, and `(\COERCE.TO.NSADDRESS "0#10000.125000.1#")` is what
  `COURIER.OPEN` takes. Every machine needs its own MAC: the default is the same for all.
- **A record** in a Courier call is the list of its fields in order, so `(RECORD (SUIT STRING)
  (VALUE CARDINAL))` is `("H" 3)`.

What was missing, outside Lisp:

- **A Maiko with NetHub support.** Neither released emulator has `-nh-host`. Building the release's
  own tag with `-DMAIKO_ENABLE_NETHUB` and `bin/makeright x` gave one that works on Linux
  (`docker/Dockerfile`) and on an Apple Silicon Mac (`./hearts.sh maiko-nethub`, which puts it
  beside the release and leaves the release as it is). On the Mac the Darwin makefile takes no
  flags from the environment, so the flag goes into its `DEBUGFLAGS` line. A cmake Release build
  of the same tag with `MAIKO_NETWORK_TYPE=NETHUB` crashed at startup on Linux aarch64; we did not
  look for the cause.
- **A hub.** For calls between machines on one hub, none of Dodo's services are needed, and the
  hub's protocol is small: each packet is a 2-byte length and an Ethernet frame. `tools/nethub.py`
  (about 40 lines, standard library) was enough.

Not tried: broadcast calls to find machines, and a Dodo hub. A plain hub across the Internet would
need a tunnel or a VPN, since the connection is unencrypted TCP and any machine on the hub can call
any Courier program on any other. The next section is what we did instead.

## HEARTS on Courier: a house that is not a Medley

HEARTS no longer needs a Medley to run the game. The house is a Python program (the web platform,
where people also play from a browser), and it is on the hub as an XNS host that speaks SPP and
Courier. Medleys bring players to its tables. Tested 14 November 2026 with Medley 260810 on Linux
(in Docker) and on an Apple Silicon Mac, a whole game to 100 each time.

Two Courier programs, defined for Medley in `medley/hcourier.lisp`:

- **`HEARTSHOUSE` (19860)**, served by the house: `OFFER` (players anyone may choose as opponents),
  `SIT` (at a table someone opened), `NEW.TABLE`, `LEAVE`, `TABLES`, `OPPONENTS`. Refusals are
  declared errors with a sentence to show: `NO.SUCH.TABLE`, `NO.SEATS`, `NOT.ALLOWED`, `BAD.REQUEST`.
- **`HEARTSPLAYERS` (19861)**, served by a Medley with players, on the stock `COURIERSERVE`:
  `TABLE`, `DEAL`, `PASS`, `RECEIVED`, `PLAY`, `CARD`, `TRICK`, `SCORES`, `GAME.OVER`. The house
  tells the machine everything its seats may see, as it happens, and asks for a pass or a card
  with the legal cards attached. Nothing is evaluated: each procedure takes typed arguments (a
  card is `(RECORD (SUIT SUIT) (VALUE CARDINAL))`, a suit an `ENUMERATION`) and does one thing.

What we learned building the other end (`backend/hearts/xns.py`, under 500 lines, checked against
Medley's own `SPP`, `COURIER` and `COURIERSERVE` sources):

- **The hub and the house are one program.** It answers frames addressed to the house and passes
  none from one machine to another. So a Medley on this hub reaches the house's two programs and
  nothing else, a stranger can't call a Courier program on your machine, and two machines with
  the same `-nh-mac` do no harm. That is what makes it reasonable to open the hub's port to the
  Internet without a VPN. The traffic is still unencrypted.
- **Medley's SPP server answers from a new socket.** A connection opened to socket 5 is answered
  by a system packet from another socket, with the server's connection id; the client must send
  everything after that to the new socket.
- **The version exchange has no end-of-message on the server's side.** Medley's Courier server
  sends its version pair with `FORCEOUTPUT`, so those four bytes arrive at the head of the first
  reply. Medley's client sends `(2 3)` with an end-of-message and accepts either.
- **One call at a time on a connection, in order.** `COURIERSERVE` runs each call in the
  connection's own process, and a call may take as long as it likes: a person choosing a card
  holds a `PLAY` call open, and SPP's probes every 15 seconds keep the connection alive.
- **A procedure definition is positional for the server.** `COURIERSERVE` reads
  `(NAME n (ARGS) RETURNS (RESULTS) REPORTS (ERRORS) IMPLEMENTEDBY FN)` by position, so a
  procedure with no result still needs `RETURNS NIL REPORTS NIL` before `IMPLEMENTEDBY`.
- **A frame must reach Maiko in one piece.** Maiko reads the 2-byte length and then the frame with
  a non-blocking `recv`, and drops the frame if it gets less. Write both in one call. SPP
  retransmits, which covers the rare split.
- **Maiko joins the hub once, as it starts.** If the hub isn't there, or goes away, the emulator
  does not try again: Medley has to be restarted. A hub that doesn't answer at all (a firewall
  that drops packets) delays the start by the TCP timeout.
- **On a hub with no PUP service, `(ETHERHOSTNUMBER)` never returns.** It waits for a PUP host
  number from a gateway. The 1986 HEARTS file called it as it loaded, so loading hung
  (HEARTS-BUGS H8). `\MY.NSADDRESS` is the address to use.

## The relay way: a child process does the networking

`CREATE-PROCESS-STREAM` (in `UNIXCOMM`) starts a Unix command and returns a stream open both
ways: what Medley writes goes to the command's standard input, and its standard output can be read
back. So a small program can do the networking while Medley talks to it in lines of text. For
Medley-to-Medley, both machines dial out to a relay on a server, which avoids NAT:

```
Medley A ⇄ pipe ⇄ hnetlink.py ⇄ WebSocket (wss://) ⇄ relay ⇄ WebSocket ⇄ hnetlink.py ⇄ pipe ⇄ Medley B
```

`hnetlink.py` uses only Python 3's standard library, so a Medley user installs nothing. The relay
(`hnetrelay.py`, which needs the `websockets` package) runs on a server and only passes messages
along: it never evaluates anything. Machines meet in a *room* named by a code you share, like an
invitation.

## Example 1: a two-way pipe to a child process

These two functions are all you need to talk to a child process. The comments say why each line is
there; see the gotchas below.

```lisp
(FILESLOAD UNIXCOMM)
(DEFINEQ
(Pipe.WriteLine
  (LAMBDA (S Line)
    (* ; "Flush every 256 bytes: past about 500 unflushed bytes, writes to a child are lost.  End with BOUT 10: TERPRI sends CR.")
    (for C in (CHCON Line) as I from 1
       do (BOUT S C)
          (if (EQ 0 (IREMAINDER I 256))
              then (FORCEOUTPUT S)))
    (BOUT S 10)
    (FORCEOUTPUT S)))
(Pipe.ReadLine
  (LAMBDA (S LimitMS)
    (* ; "One line, or NIL after LimitMS.  EOFP is true whenever nothing is waiting, so poll, and BLOCK so that other processes run.")
    (bind (Start _ (CLOCK 0)) Codes B until (IGREATERP (IDIFFERENCE (CLOCK 0) Start) LimitMS)
       do (if (EOFP S)
              then (BLOCK 20)
            elseif (EQ (SETQ B (BIN S)) 10)
              then (RETURN (CONCATCODES (REVERSE Codes)))
            else (push Codes B)))))
)
(SETQ Upper (CREATE-PROCESS-STREAM "python3 -u -c 'import sys
for line in sys.stdin: sys.stdout.write(line.upper())'"))
(Pipe.WriteLine Upper "hello from Medley")
(Pipe.ReadLine Upper 5000)                        ; => "HELLO FROM MEDLEY"
(Pipe.WriteLine Upper (ALLOCSTRING 5000 (CHARCODE a)))
(NCHARS (Pipe.ReadLine Upper 5000))               ; => 5000
(CLOSEF Upper)
```

## Example 2: the Internet, through a command

For a single request you don't need a helper of your own: run a command and read what it prints.
Medley can't see the command finish (gotcha 3), so the command prints a last line Medley can
recognize.

```lisp
(DEFINEQ
(Fetch
  (LAMBDA (Url)
    (* ; "The lines of the page at Url, using curl.  .END. marks the end; avoid _ in commands (MEDLEY-ISSUES M11).")
    (LET ((S (CREATE-PROCESS-STREAM (CONCAT "curl -s --max-time 20 '" Url "'; echo; echo .END."))))
         (CL:UNWIND-PROTECT
             (bind Line while (AND (SETQ Line (Pipe.ReadLine S 30000))
                                   (NOT (EQUAL Line ".END.")))
                collect Line)
             (CLOSEF S)))))
)
(Fetch "https://example.com/")                    ; => the page's lines; one has "Example Domain"
```

Don't put an untrusted URL into that command line: the shell would interpret it.

## Example 3: one Medley calling another

`HNET` (in the HEARTS repository at tag `revival-1986`: `dist/HNET` and `dist/hnetlink.py`) rebuilds `REMOTEVAL` and
`EVALSERVER` on the relay. A machine evaluates only calls to functions on its list `HNET.Allowed`,
and only with quoted or constant arguments.

Start a relay somewhere both machines can reach. For anything public, use `wss://`: give the
relay a certificate, or put it behind a TLS proxy.

```bash
pip install websockets
python3 hnetrelay.py --port 8765 --cert fullchain.pem --key privkey.pem
```

On the first Medley, Bob's, define a function and allow it:

```lisp
(FILESLOAD HNET)
(DEFINEQ
(Greet
  (LAMBDA (Who)
    (CONCAT "Hello " Who ", this is " HNET.Name)))
)
(SETQ HNET.Allowed (CONS (QUOTE Greet) HNET.Allowed))
(HNET.Connect "myroom" "bob" "wss://relay.example.org")
```

On the other, Alice's:

```lisp
(FILESLOAD HNET)
(HNET.Connect "myroom" "alice" "wss://relay.example.org")
(REMOTEVAL (LIST (QUOTE Greet) (KWOTE "alice")) "bob")      ; => "Hello alice, this is bob"
(REMOTEVAL (LIST (QUOTE Greet) (KWOTE "anyone")) NIL T 3000) ; no host: the first machine that answers
(REMOTEVAL (QUOTE (HNET.Name)) "bob")                         ; error: Bob didn't allow HNET.Name
(HNET.Disconnect)
```

`REMOTEVAL`'s arguments are `(FORM HOST FLAG TIMEOUT)`, as the 1986 game used them. With no host it
asks each machine in the room in turn and returns the first answer that isn't NIL. A `FLAG` of 0
sends without waiting. `TIMEOUT` is in milliseconds, and when it runs out the value is NIL. An error
on the far machine is an error here. Each machine evaluates incoming calls one at a time, in the
order they arrived. HEARTS needs that order: a hand must arrive before the request to play from it.

With this, HEARTS plays a full game to 100 between two Medleys in separate containers. The house
seats two players, the guest supplies the other two, and both card tables end on the same score.
The 1986 network code is unchanged, except for two 1986 bugs the first games found. A remote machine's players never heard who took a trick (HEARTS-BUGS H6). And the house never updated its copy of a remote player's hand, so after a remote player passed the 2♣ the house asked the wrong seat to lead (H7). The second showed up only in some games, and a trace of every message is what found it, so `HNET.Trace` (a stream) logs each line sent and received.

## The gotchas

1. **Unflushed writes to a child process lose bytes.** Write more than about 500 bytes without a
   `FORCEOUTPUT` and the rest is dropped, newline included, so the child waits forever. Flushing
   every 256 bytes delivered lines of 1,000, 4,000 and 20,000 bytes intact.
2. **`TERPRI` on a process stream sends CR, not LF**, even though the stream's end-of-line
   convention says LF. A child reading lines then never gets one. End lines with `(BOUT S 10)`.
3. **`EOFP` is true whenever nothing is waiting**, so it can't tell a slow child from one that has
   finished or died. Poll with a time limit, and have the child print a last line you can
   recognize (`.END.` in example 2; `hnetlink.py` prints `CLOSED reason` before it exits).
4. **Poll with `BLOCK`.** A loop that waits on a stream should `(BLOCK 20)` between looks, so the
   rest of Medley (windows, the mouse, other processes) keeps running.
5. **The child must flush each line it writes.** Use `python3 -u`. Debian's `awk` (mawk) waits for a
   full input buffer before it answers, even with `fflush()`.
6. **A child's standard error comes back on the same stream.** Redirect it deliberately:
   `2>/dev/null`, or `2>&1` if you want to read it.
7. **On a Mac, `_` turns into an arrow on the way to Unix.** Under a UTF-8 locale, an underscore in
   a source file reaches a command, a file name or `UNIX-GETENV` as U+2190, so `llm_player.py` isn't
   found and `(UNIX-GETENV "HNET_RELAY")` is NIL. What
   you write *into* a stream or file goes out byte for byte. Avoid underscores in commands and file
   names, or map them (`HNET.Sys` in `HNET`; MEDLEY-ISSUES M11).
8. **Medley's Common Lisp reader evaluates `#.` and `#,` while reading, and has no `*READ-EVAL*`
   to stop it.** `(CL:READ)` of `"#.(SETQ X 1)"` sets X. To read data from a network, copy a
   readtable and make `#` an ordinary character: `(SETSYNTAX 35 (QUOTE OTHER) R)`. Then check what
   you read before you evaluate any of it.
9. **Not everything prints readably.** A window, an array or a LOOPS instance prints as `{WINDOW}#…`,
   and a circular list never finishes printing. Send plain data: `HNET.Plain` sends anything else
   as NIL and cuts a list where it contains itself.
10. **`KWOTE` leaves numbers, `T` and `NIL` unquoted.** `(KWOTE 3)` is `3`, while `(KWOTE "s")` is
    `(QUOTE "s")`. A checker that insists on `(QUOTE x)` arguments refuses `(F 3)`, as ours did at
    first.
11. **One process reads a stream; writers take a lock.** `HNET` has one listener process per
    connection, and its writes share a monitor lock, so two processes never interleave a line.

## Trying it

The HEARTS repository has everything. The headless Docker harness (`tools/medley-headless`) is how
all of this was tested:

- `tests/courier/run.sh` runs the two-Medley Courier example above.
- `tests/run-courier.sh` plays HEARTS over Courier: a Medley's players at a table of the house.
  `backend/tests/test_courier.py` tests the house's side without Medley.
- `tests/netguide.lisp` runs examples 1 and 2 and the gotchas, in one container.
- The relay and example 3 are tested at tag `revival-1986` (`tests/test_hnet.py`, `tests/run-hnet.sh`).

**Not done yet:**

- The house's hub is not encrypted, and it has no rate limits yet.
- We haven't tried Unix-domain sockets.
