(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "The resident HEARTS Medley (docs/medley-server.md).  Started by docker/resident-run.

    It keeps offering players to the house, over Courier (HCOURIER): anyone opening a table there,
    from a browser or from a Medley, can take them as opponents, and they play here, on this
    Medley.  When a game ends, or nothing happens for R.IdleMinutes, it offers fresh players.  Its
    screen is on the web: watch it, or control it.")

(* "Nobody is at the keyboard to release a page hold, so the Exec never holds.")
(ADVISE (QUOTE PAGEFULLFN) (QUOTE (RETURN)))
(CNDIR "{DSK}/hearts/dist/")
(FILESLOAD ACTIVEREGIONS HEARTS HCOURIER NNPLAYER)

(DEFINEQ

(R.Env
  (LAMBDA (Name Default)
    (* ; "An environment variable.  The names have no underscore: one read from a file reaches Unix as an arrow under a UTF-8 locale (MEDLEY-ISSUES M11).")
    (LET ((V (UNIX-GETENV Name)))
         (if (AND V (IGREATERP (NCHARS V) 0))
             then V
           else Default))))

(R.Words
  (LAMBDA (Text)
    (* ; "The words of TEXT, as upper-case atoms: EP NP CP.")
    (for W in (CL:WITH-INPUT-FROM-STRING (In (CONCAT "(" Text ")")) (READ In))
       collect (MKATOM (U-CASE W)))))

(R.Label
  (LAMBDA (Type)
    (* ; "What the house calls a player of this type in its list of opponents.")
    (CONCAT (SELECTQ Type
                (EP "Expert")
                (NP "Neural network")
                (CP "Conservative")
                (CLOWN "Clown")
                (MKSTRING Type))
            " on Medley")))

(R.Place
  (LAMBDA (W H)
    (* ; "Window places, as the players make their windows: Thoughts windows to the left and right of the card table, from the top down (Medley counts y from the bottom).")
    (LET ((Slot (CAR (NTH R.Slots (ADD1 (IREMAINDER R.NextSlot (LENGTH R.Slots)))))))
         (SETQ R.NextSlot (ADD1 R.NextSlot))
         (CREATEREGION (CAR Slot) (CADR Slot) (CADDR Slot) (CADDDR Slot)))))

(R.Ours?
  (LAMBDA (W)
    (* ; "A window of a game: a card table, a hand, a player's thoughts.")
    (LET ((Title (WINDOWPROP W (QUOTE TITLE))))
         (AND (STRINGP Title)
              (for P in (QUOTE ("Thoughts of " "Hearts Card Table" "Hearts window for " "Hearts Window for "))
                 thereis (STRPOS P Title 1 NIL T))))))

(R.Tidy
  (LAMBDA NIL
    (for W in (OPENWINDOWS) when (R.Ours? W) do (CLOSEW W))
    (SETQ HNET.CardTable NIL)
    (SETQ R.NextSlot 0)))

(R.Make
  (LAMBDA (Type)
    (* ; "A player, with its Thoughts window.  The Conservative and the network make their own; a closed-hand Expert narrates only into its hand window, so give it one as PlayHearts does.")
    (LET ((Player (H.MakePlayer Type NIL)))
         (if (EQ Type (QUOTE EP))
             then (PH.GiveThoughtsWindow Player))
         Player)))

(R.Offer
  (LAMBDA NIL
    (* ; "Fresh players, offered to the house.  If the house can't be reached three times running, stop Medley: the emulator joins the NetHub only as it starts, and resident-run starts it again.")
    (R.Tidy)
    (LET ((Result (HC.Offer (for X in R.Players collect (R.Make X))
                         R.Key
                         (for X in R.Players collect (R.Label X)))))
         (if (EQ (CAR (LISTP Result)) (QUOTE ERROR))
             then (R.Lost (CADDR Result))
           else (SETQ R.Misses 0)
                (SETQ R.CheckedAt (CLOCK 0))
                (SETQ R.State "waiting for someone to choose these players")))))

(R.Lost
  (LAMBDA (Why)
    (add R.Misses 1)
    (SETQ R.State (CONCAT "can't reach the house: " Why))
    (R.Show)
    (if (IGEQ R.Misses 3) then (LOGOUT T))
    (DISMISS 20000)))

(R.Minutes
  (LAMBDA (Since)
    (if Since
        then (IQUOTIENT (IDIFFERENCE (CLOCK 0) Since) 60000)
      else 0)))

(R.Show
  (LAMBDA NIL
    (if (NOT (AND R.Status (OPENWP R.Status)))
        then (SETQ R.Status (CREATEW (CREATEREGION 475 798 450 96) "The resident HEARTS Medley")))
    (CLEARW R.Status)
    (printout R.Status "At the house " HC.House T)
    (printout R.Status "Offering: " (for X in R.Players collect (R.Label X)) T)
    (printout R.Status (OR R.State "") T)
    (printout R.Status "Games played here: " R.Games T)))

(R.Step
  (LAMBDA NIL
    (COND
       (HC.Winners (* ; "A game ended here.")
              (add R.Games 1)
              (SETQ R.State "game over; new players in a moment")
              (R.Show)
              (DISMISS 3000)
              (R.Offer))
       ((AND HC.Playing (IGREATERP (R.Minutes HC.LastCallAt) R.IdleMinutes))
        (* ; "A game nobody is playing any more.  Offering again takes the players away from it.")
        (R.Offer))
       (HC.Playing (SETQ R.State (CONCAT "playing seats " (for P in HNET.MyPlayers collect (fetch Number of P))
                                        " at a table of the house")))
       ((NULL HC.Players)
        (R.Offer))
       ((IGEQ (R.Minutes R.CheckedAt) 1)
        (* ; "Waiting to be chosen: is the house still there?")
        (LET ((Answer (HC.Tables)))
             (if (EQ (CAR (LISTP Answer)) (QUOTE ERROR))
                 then (R.Lost (CADDR Answer))
               else (SETQ R.Misses 0)
                    (SETQ R.CheckedAt (CLOCK 0))))))
    (R.Show)))

(R.Loop
  (LAMBDA NIL
    (while T do (XCL:CONDITION-CASE (R.Step)
                       (CL:ERROR (C)
                              (SETQ R.State (CONCAT "error: " (CL:PRINC-TO-STRING C)))
                              (NLSETQ (R.Show))))
                (DISMISS 2000))))
)

(SETQ R.Players (R.Words (R.Env "RESIDENTPLAYERS" "EP NP CP")))
(SETQ R.Key (R.Env "RESIDENTKEY" ""))
(SETQ R.Misses 0)
(SETQ R.CheckedAt NIL)
(SETQ R.IdleMinutes 20)
(SETQ R.Games 0)
(SETQ R.Status NIL)
(SETQ R.State "starting")
(SETQ R.NextSlot 0)
(SETQ R.Slots (QUOTE ((10 530 455 250) (935 530 335 250) (10 270 455 250) (935 270 335 250) (10 10 455 250) (935 10 335 250))))
(SETQ ThinkFlag? T)
(if (FMEMB (QUOTE EP) R.Players) then (FILESLOAD EXPERT))
(* "PLAYHEARTS, for the Expert's Thoughts window (PH.GiveThoughtsWindow and its advice).")
(FILESLOAD PLAYHEARTS)
(ADVISE (QUOTE GETBOXREGION) (QUOTE BEFORE) (QUOTE (RETURN (R.Place WIDTH HEIGHT))))
(ADVISE (QUOTE GETREGION) (QUOTE BEFORE) (QUOTE (RETURN (R.Place (OR MINWIDTH 300) (OR MINHEIGHT 200)))))
(* "The Exec goes under the card table, out of the way of the players' Thoughts windows.")
(LET ((Exec (WFROMDS (TTYDISPLAYSTREAM))))
     (if Exec then (SHAPEW Exec (CREATEREGION 475 10 450 370))))
(R.Show)
(ADD.PROCESS (QUOTE (R.Loop)) (QUOTE NAME) (QUOTE Resident))
STOP
