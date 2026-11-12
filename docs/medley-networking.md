# Networking in Medley 2026: what's left, what works, and the gotchas

*Harley Davis and Claude, November 2026. From the revival of HEARTS, a 1986 Interlisp-D game,
whose four players could sit on different machines.*

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
| XNS (Courier, SPP, the NS file servers) | Works only through emulation. You run a [Dodo](https://github.com/devhawala/dodo) NetHub, start Maiko with `-nh-host`, and call `\NSINIT`. The `medley` script has `--nethub` for this, but the macOS emulator we used (`ldex`) doesn't list the NetHub flags. It is a shared virtual Ethernet with no security, so across the Internet it would need a VPN as well. |
| The in-Lisp TCP/IP stack | Removed. Medley uses the host's network through Unix processes instead. |
| `EVALSERVER` / `REMOTEVAL` (a LispUsers package for remote evaluation) | Not in the release at all. |
| Broadcast to find other machines | Doesn't cross the Internet. |
| Evaluating whatever form arrives | Fine on a 1986 office Ethernet. On the Internet it lets anyone run code on your machine. |

Two more facts shape everything else. Home machines sit behind NAT and firewalls, so two Medleys
can't usually connect to each other directly. And we found no library that opens a TCP connection
from Lisp. The emulator has socket subroutines (`OPEN-SOCKET` and its friends in `LLSUBRS`) that no
library calls, and `UNIXCOMM` has `CREATE-UNIX-SOCKET-STREAM` for Unix-domain sockets. We tried
neither.

## What works: a child process does the networking

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
    (PROG ((Start (CLOCK 0)) Codes B)
      LOOP
          (if (IGREATERP (IDIFFERENCE (CLOCK 0) Start) LimitMS)
              then (RETURN NIL))
          (if (EOFP S)
              then (BLOCK 20)
                   (GO LOOP))
          (SETQ B (BIN S))
          (if (EQ B 10)
              then (RETURN (CONCATCODES (REVERSE Codes))))
          (push Codes B)
          (GO LOOP))))
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

`HNET` (from the HEARTS repository: `dist/HNET` and `dist/hnetlink.py`) rebuilds `REMOTEVAL` and
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

- `tests/netguide.lisp` runs examples 1 and 2 and the gotchas, in one container.
- `tests/test_hnet.py` tests the relay and the link without Medley, `wss://` included.
- `tests/run-hnet.sh` starts a relay and two Medleys on a private Docker network. They play the game
  and run example 3, and then an intruder joins the room and sends forms that must be refused.

**Not done yet:**

- There is no public relay. The room name is the only access control, so a public relay should
  rate-limit and use `wss://`.
- We haven't tried the NetHub (XNS) route or Unix-domain sockets.
