;; HNET -- the 1986 network game over the Internet (not part of the 1986 system).
;;
;;   (FILESLOAD HEARTS HNET)
;;   (HNET.Connect "ROOM" "NAME")              join a room on the relay, as NAME
;;   On the guest:  (NetHearts (LIST (CP.Create) (CP.Create)))     offer two players
;;   On the house:  (Hearts (LIST (CP.Create) (CP.Create)))        the rest come from the net
;;   (HNET.Disconnect)
;;
;; In 1986 the HEARTS machines talked over the Xerox Ethernet: REMOTEVAL sent a Lisp form to
;; another machine, whose EVALSERVER evaluated it and sent back the value.  The 1986 network
;; code (HNET.Hello, HNET.Inform, CT.InformAll, ... in HEARTS) is unchanged; this file rebuilds
;; the three functions it used and Medley no longer has, REMOTEVAL, EVALSERVER and the host
;; address, on a relay that every machine dials out to (medley/hnetrelay.py), through a small
;; helper Medley runs as a child process (medley/hnetlink.py).
;;
;; Two things are new.  A machine evaluates only the HNET calls the game makes (HNET.Allowed),
;; never an arbitrary form, since anyone who knows the room's name can send one.  And what goes
;; over the wire is plain data: anything that can't be printed and read back (a window, an
;; Expert's unit) goes as NIL, and so does a list met again inside itself (a hand's owner's hand).

(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "HNET -- the 1986 network game over a relay (2026).  REMOTEVAL and EVALSERVER need nothing else; for the game, load HEARTS first.")

(FILESLOAD UNIXCOMM)

(* "Settings.  HNET.Relay is ws://HOST:PORT, or wss:// behind TLS; the HNET_RELAY environment variable overrides it.")
(RPAQ? HNET.Relay "ws://localhost:8765")
(RPAQ? HNET.Python "python3")
(RPAQ? HNET.Link NIL)
(RPAQ? HNET.CallTimeout NIL)
(RPAQ? HNET.Trace NIL)

(* "What a machine will evaluate when another asks.  GoodBye sends (SETQ HNET.MyPlayers), which is allowed as it is.")
(RPAQQ HNET.Allowed (HNET.Apply HNET.Inform HNET.DoIWantToPlay? HNET.CT.Open))

(* "State")
(RPAQ? HNET.Stream NIL)
(RPAQ? HNET.Name NIL)
(RPAQ? HNET.Room NIL)
(RPAQ? HNET.Peers NIL)
(RPAQ? HNET.PeersAt 0)
(RPAQ? HNET.Waiting NIL)
(RPAQ? HNET.Replies NIL)
(RPAQ? HNET.Queue NIL)
(RPAQ? HNET.NextId 0)
(RPAQ? HNET.Closed NIL)
(RPAQ? HNET.Served 0)
(RPAQ? HNET.Sent 0)
(RPAQ? HNET.Refused NIL)
(RPAQ? HNET.LastFrom NIL)
(RPAQ? HNET.LastCallAt NIL)
(RPAQ HNET.Lock (CREATE.MONITORLOCK (QUOTE HNET)))

(* "What comes over the wire is read with this readtable: the file readtable with # made an ordinary character.  Medley's Common Lisp readtables evaluate #. and #, while reading, and there is no *READ-EVAL* to stop them; the file readtable doesn't, but this makes sure.")
(RPAQ HNET.Rdtbl (LET ((R (COPYREADTABLE FILERDTBL)))
                      (SETSYNTAX 35 (QUOTE OTHER) R)
                      R))

(DEFINEQ

(HNET.Connect
  (LAMBDA (Room Name Relay)
    (* ; "Join ROOM on the relay as NAME.  Returns NAME, or (ERROR message).")
    (HNET.Disconnect)
    (LET ((Link (HNET.FindLink))
          (Relay (OR Relay (HNET.EnvRelay) HNET.Relay))
          S Line)
         (COND
            ((NOT Link)
             (LIST (QUOTE ERROR) "cannot find hnetlink.py: set HNET.Link or HEARTSDIR"))
            ((NOT (AND (HNET.Word? Room) (HNET.Word? Name)))
             (LIST (QUOTE ERROR) "a room and a name are 1 to 32 letters, digits, dots or dashes"))
            ((NOT (SETQ S (CREATE-PROCESS-STREAM (HNET.Sys (CONCAT HNET.Python " -u " Link " " Relay
                                                                   " " Room " " Name " 2>&1")))))
             (LIST (QUOTE ERROR) "cannot start a process: Medley needs the X11 path (MEDLEY-ISSUES M2)"))
            (T (SETQ Line (HNET.ReadLine S 20000))
               (if (AND Line (STRPOS "WELCOME " Line 1 NIL T))
                   then (SETQ HNET.Stream S)
                        (SETQ HNET.Room (MKSTRING Room))
                        (SETQ HNET.Name (SUBSTRING Line 9))
                        (SETQ HNET.Address HNET.Name)
                        (SETQ HNET.Closed NIL)
                        (SETQ HNET.Peers NIL)
                        (SETQ HNET.Waiting NIL)
                        (SETQ HNET.Replies NIL)
                        (SETQ HNET.Queue NIL)
                        (SETQ HNET.Refused NIL)
                        (ADD.PROCESS (LIST (QUOTE HNET.Listen)
                                           (KWOTE S))
                               (QUOTE NAME)
                               (QUOTE HNET.Listener))
                        (ADD.PROCESS (LIST (QUOTE HNET.Serve)
                                           (KWOTE S))
                               (QUOTE NAME)
                               (QUOTE HNET.Server))
                        HNET.Name
                 else (NLSETQ (CLOSEF S))
                      (LIST (QUOTE ERROR)
                            (if Line
                                then (if (STRPOS "CLOSED " Line 1 NIL T)
                                         then (SUBSTRING Line 8)
                                       else Line)
                              else "the link did not answer"))))))))

(HNET.Disconnect
  (LAMBDA NIL
    (LET ((S HNET.Stream))
         (SETQ HNET.Stream NIL)
         (SETQ HNET.Closed "disconnected")
         (for Name in (QUOTE (HNET.Listener HNET.Server)) do (DEL.PROCESS Name))
         (if S
             then (NLSETQ (HNET.Write S "QUIT"))
                  (NLSETQ (CLOSEF S)))
         NIL)))

(HNET.Connected?
  (LAMBDA NIL
    (AND HNET.Stream (NOT HNET.Closed) T)))

(HNET.PeerNames
  (LAMBDA (WaitMS)
    (* ; "The other machines in the room, in the order they joined, fresh from the relay.")
    (if (HNET.Connected?)
        then (LET ((Asked (CLOCK 0))
                   (Seen HNET.PeersAt))
                  (* ; "HNET.PeersAt counts the PEERS answers: wait for the next one.  (Not a time: CLOCK can be negative.)")
                  (HNET.Write HNET.Stream "PEERS")
                  (for I from 1 while (AND (EQ HNET.PeersAt Seen)
                                           (NOT HNET.Closed)
                                           (ILESSP (IDIFFERENCE (CLOCK 0) Asked) (OR WaitMS 5000)))
                     do (BLOCK 20))
                  HNET.Peers))))

(REMOTEVAL
  (LAMBDA (Form Host Flag Timeout)
    (* ; "1986: evaluate FORM on HOST and return its value.  As the game calls it: no HOST asks each machine in turn and returns the first answer that isn't NIL (HNET.Hello finding players); a third argument of 0 sends and doesn't wait (the informs); TIMEOUT is in milliseconds, and when it runs out the value is NIL.")
    (COND
       ((NULL Host)
        (for Peer in (HNET.PeerNames) bind V when (SETQ V (CAR (NLSETQ (HNET.Call Peer Form Timeout))))
           do (RETURN V)))
       ((EQ Flag 0)
        (HNET.Send Host 0 Form)
        NIL)
       (T (HNET.Call Host Form Timeout)))))

(EVALSERVER
  (LAMBDA NIL
    (* ; "1986: start answering other machines.  Here, being connected is enough.")
    (OR (HNET.Connected?)
        (ERROR "HNET: connect first, with (HNET.Connect room name)"))))

(HNET.Call
  (LAMBDA (Host Form Timeout)
    (* ; "Send FORM to HOST and wait for its value.  An error there is an error here.")
    (LET ((Id (add HNET.NextId 1))
          (Start (CLOCK 0))
          (Limit (OR Timeout HNET.CallTimeout))
          Got)
         (push HNET.Waiting Id)
         (CL:UNWIND-PROTECT
             (PROGN (HNET.Send Host Id Form)
                    (until (OR (SETQ Got (FASSOC Id HNET.Replies))
                               HNET.Closed
                               (AND Limit (IGREATERP (IDIFFERENCE (CLOCK 0) Start) Limit)))
                       do (BLOCK 20))
                    (COND
                       ((NULL Got)
                        (if HNET.Closed
                            then (ERROR "HNET: the link closed:" HNET.Closed))
                        NIL)
                       ((EQ (CDR Got) (QUOTE NOPEER))
                        (ERROR "HNET: not in the room:" Host))
                       (T (LET ((Answer (HNET.Decode (CDR Got))))
                               (if (AND (LISTP Answer) (EQ (CAR Answer) T))
                                   then (CDR Answer)
                                 else (ERROR (CONCAT "HNET: " Host " failed: ")
                                             (if (LISTP Answer) then (CDR Answer) else Answer)))))))
             (SETQ HNET.Waiting (DREMOVE Id HNET.Waiting))
             (SETQ HNET.Replies (for R in HNET.Replies unless (EQ (CAR R) Id) collect R))))))

(HNET.Send
  (LAMBDA (Host Id Form)
    (if (NOT (HNET.Connected?))
        then (ERROR "HNET: not connected" HNET.Closed))
    (add HNET.Sent 1)
    (HNET.Write HNET.Stream (CONCAT "CALL " Host " " Id " " (HNET.Encode Form)))))

(HNET.Listen
  (LAMBDA (S)
    (* ; "Read the link's lines: replies go to whoever is waiting, calls to the server, in order.")
    (bind Line until HNET.Closed
       do (SETQ Line (HNET.ReadLine S NIL))
          (if HNET.Trace then (printout HNET.Trace "<- " Line T) (FORCEOUTPUT HNET.Trace))
          (LET ((Kind (HNET.Word Line 1))
                (Who (HNET.Word Line 2))
                (Id (MKATOM (HNET.Word Line 3)))
                (Body (HNET.Rest Line 3)))
               (SELECTQ (MKATOM Kind)
                   (CALL (SETQ HNET.Queue (NCONC1 HNET.Queue (LIST Who Id Body))))
                   (REPLY (if (FMEMB Id HNET.Waiting)
                              then (push HNET.Replies (CONS Id Body))))
                   (NOPEER (if (FMEMB Id HNET.Waiting)
                               then (push HNET.Replies (CONS Id (QUOTE NOPEER)))))
                   (PEERS (SETQ HNET.Peers (for W in (HNET.Words (OR (HNET.Rest Line 1) ""))
                                              collect W))
                          (SETQ HNET.PeersAt (ADD1 HNET.PeersAt)))
                   (CLOSED (SETQ HNET.Closed (OR (HNET.Rest Line 1) "closed")))
                   NIL)))))

(HNET.Serve
  (LAMBDA (S)
    (* ; "Evaluate the calls one at a time, in the order they came, as the 1986 server did: a hand must arrive before the request to play from it.")
    (bind Call until HNET.Closed
       do (if HNET.Queue
              then (SETQ Call (pop HNET.Queue))
                   (HNET.Answer S (CAR Call) (CADR Call) (CADDR Call))
            else (BLOCK 20)))))

(HNET.Answer
  (LAMBDA (S From Id Body)
    (LET* ((Form (HNET.Decode Body))
           (Call (HNET.Check Form))
           Result)
          (add HNET.Served 1)
          (if Call
              then (SETQ HNET.LastFrom From)
                   (SETQ HNET.LastCallAt (CLOCK 0)))
          (SETQ Result (COND
                          ((NULL Call)
                           (push HNET.Refused (LIST From Form))
                           (CONS NIL "not an HNET call"))
                          ((AND (EQ (CAR Call) (QUOTE HNET.DoIWantToPlay?))
                                (NOT (AND (BOUNDP (QUOTE H.WaitingToPlay)) H.WaitingToPlay)))
                           (* ; "No players waiting: say no without asking.  In 1986 only a machine running EVALSERVER heard this; here every machine in the room does, and HNET.DoIWantToPlay? resets Player.Array, which would break a game this machine is running as the house.")
                           (CONS T NIL))
                          (T (LET ((V (NLSETQ (APPLY (CAR Call) (CDR Call)))))
                                  (if V
                                      then (CONS T (CAR V))
                                    else (CONS NIL "an error"))))))
          (if (AND (NUMBERP Id) (NOT (EQ Id 0)) (NOT HNET.Closed))
              then (HNET.Write S (CONCAT "REPLY " From " " Id " " (HNET.Encode Result)))))))

(HNET.Check
  (LAMBDA (Form)
    (* ; "(Fn . Args) if FORM is one of the calls the game makes, its arguments quoted or constants (KWOTE leaves a number, T and NIL bare); else NIL.")
    (COND
       ((EQUAL Form (QUOTE (SETQ HNET.MyPlayers)))
        (LIST (QUOTE SET) (QUOTE HNET.MyPlayers) NIL))
       ((AND (LISTP Form)
             (FMEMB (CAR Form) HNET.Allowed)
             (for A in (CDR Form) always (OR (NUMBERP A)
                                             (STRINGP A)
                                             (FMEMB A (QUOTE (T NIL)))
                                             (AND (LISTP A)
                                                  (EQ (CAR A) (QUOTE QUOTE))
                                                  (LISTP (CDR A))
                                                  (NULL (CDDR A))))))
        (CONS (CAR Form) (for A in (CDR Form) collect (if (LISTP A) then (CADR A) else A)))))))

(HNET.Encode
  (LAMBDA (X)
    (* ; "X printed on one line.")
    (CONCATCODES (for C in (CHCON (LET ((P (HNET.Plain X NIL)))
                                       (CL:WITH-OUTPUT-TO-STRING (Out)
                                              (PRIN2 P Out HNET.Rdtbl)))) collect (if (OR (EQ C 10) (EQ C 13))
                                                                                     then 32
                                                                                   else C)))))

(HNET.Plain
  (LAMBDA (X Path)
    (* ; "X with what can't travel replaced by NIL: anything but a list, symbol, number or string, and a list met again inside itself.  Walks along a list rather than down it, so a long list doesn't go deep.")
    (COND
       ((OR (NULL X) (LITATOM X) (NUMBERP X) (STRINGP X)) X)
       ((LISTP X) (if (FMEMB X Path)
                      then NIL
                    else (PROG ((P (CONS X Path))
                                (Tail X)
                                Seen Out)
                           LOOP
                               (COND
                                  ((NLISTP Tail)
                                   (RETURN (if Out
                                               then (RPLACD (LAST Out) (HNET.Plain Tail P))
                                                    Out
                                             else (HNET.Plain Tail P))))
                                  ((FMEMB Tail Seen) (RETURN Out)))
                               (push Seen Tail)
                               (SETQ Out (NCONC1 Out (HNET.Plain (CAR Tail) P)))
                               (SETQ Tail (CDR Tail))
                               (GO LOOP))))
       (T NIL))))

(HNET.Decode
  (LAMBDA (Body)
    (* ; "Read one form from BODY, with HNET.Rdtbl, so nothing is evaluated while reading.")
    (if (STRINGP Body)
        then (CAR (NLSETQ (CL:WITH-INPUT-FROM-STRING (In Body)
                                 (READ In HNET.Rdtbl)))))))

(HNET.Write
  (LAMBDA (S Line)
    (* ; "One line to the link.  Flushed every 256 bytes: a longer unflushed write to a child's stdin loses bytes (MEDLEY-ISSUES M10).")
    (WITH.MONITOR HNET.Lock (for C in (CHCON Line) as I from 1
                               do (BOUT S C)
                                  (if (EQ 0 (IREMAINDER I 256))
                                      then (FORCEOUTPUT S)))
           (BOUT S 10)
           (FORCEOUTPUT S))
    (if HNET.Trace then (printout HNET.Trace "-> " Line T) (FORCEOUTPUT HNET.Trace))
    Line))

(HNET.ReadLine
  (LAMBDA (S LimitMS)
    (* ; "One line, or NIL at the time limit (none: wait).  Polled, so the rest of Medley runs meanwhile.")
    (PROG ((Start (CLOCK 0))
           Codes B)
      LOOP
          (if (AND LimitMS (IGREATERP (IDIFFERENCE (CLOCK 0) Start) LimitMS))
              then (RETURN NIL))
          (if (OR HNET.Closed (NOT (OPENP S)))
              then (if (NULL LimitMS) then (RETURN "CLOSED the link stopped")))
          (if (EOFP S)
              then (BLOCK 20)
                   (GO LOOP))
          (SETQ B (BIN S))
          (if (EQ B 10)
              then (RETURN (CONCATCODES (REVERSE Codes))))
          (if (NEQ B 13) then (push Codes B))
          (GO LOOP))))

(HNET.Word
  (LAMBDA (Line N)
    (CAR (NTH (HNET.Words Line N) N))))

(HNET.Words
  (LAMBDA (Line N)
    (* ; "The first N words of LINE (all of them with no N).")
    (bind (Start _ 1) End (Len _ (NCHARS Line)) for I from 1 while (AND (ILEQ Start Len)
                                                                         (OR (NULL N) (ILEQ I N)))
       collect (SETQ End (OR (STRPOS " " Line Start) (ADD1 Len)))
               (PROG1 (SUBSTRING Line Start (SUB1 End))
                      (SETQ Start (ADD1 End))))))

(HNET.Rest
  (LAMBDA (Line N)
    (* ; "LINE after its first N words, or NIL.")
    (bind (Start _ 1) for I from 1 to N while Start do (SETQ Start (STRPOS " " Line Start))
                                                          (if Start then (add Start 1))
       finally (RETURN (AND Start (ILEQ Start (NCHARS Line)) (SUBSTRING Line Start))))))

(HNET.Word?
  (LAMBDA (X)
    (LET ((S (MKSTRING X)))
         (AND (ILEQ 1 (NCHARS S))
              (ILEQ (NCHARS S) 32)
              (for C in (CHCON S) always (OR (AND (IGEQ C (CHARCODE A)) (ILEQ C (CHARCODE Z)))
                                             (AND (IGEQ C (CHARCODE a)) (ILEQ C (CHARCODE z)))
                                             (AND (IGEQ C (CHARCODE 0)) (ILEQ C (CHARCODE 9)))
                                             (EQ C (CHARCODE %.))
                                             (EQ C (CHARCODE -))))))))

(HNET.EnvRelay
  (LAMBDA NIL
    (LET ((R (UNIX-GETENV (HNET.Sys "HNET_RELAY"))))
         (* ; "HNET.Sys: on a Mac the _ would reach getenv as an arrow, and nothing would be found.")
         (AND R (IGREATERP (NCHARS R) 0) R))))

(HNET.FindLink
  (LAMBDA NIL
    (* ; "HNET.Link if set, else the first hnetlink.py found beside the files or in the repo.")
    (OR HNET.Link
        (for Dir in (LIST (UNIX-GETENV "HEARTSDIR")
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/il"))
                          "/hearts/dist"
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/Development/hearts/dist")))
           when Dir
           do (LET ((Path (CONCAT Dir "/hnetlink.py")))
                   (if (INFILEP (CONCAT "{UNIX}" (HNET.Sys Path)))
                       then (RETURN (SETQ HNET.Link Path))))))))

(HNET.Sys
  (LAMBDA (Text)
    (* ; "A _ read from a file reaches Unix as an arrow under a UTF-8 locale (MEDLEY-ISSUES M11); give it the underscore the system sees.")
    (LET ((U (if (GETD (QUOTE SYSTOMSTRING))
                 then (CADR (CHCON (SYSTOMSTRING "a_a")))
               else 95)))
         (if (OR (EQ U 95) (NOT (STRPOS (CHARACTER 95) Text)))
             then Text
           else (CONCATCODES (for C in (CHCON Text) collect (if (EQ C 95) then U else C)))))))
)
