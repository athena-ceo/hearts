(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "The resident HEARTS Medley (docs/medley-server.md).  Started by docker/resident-run.

    It joins a room on the network game's relay and offers players there, so anyone with a Medley
    can play it: connect to the same room and start a game with fewer than four players, and the
    rest come from here.  When a game ends, or the house leaves, or nothing happens for
    R.IdleMinutes, it offers fresh players.  Its screen is on the web: watch it, or control it.")

(* "Nobody is at the keyboard to release a page hold, so the Exec never holds.")
(ADVISE (QUOTE PAGEFULLFN) (QUOTE (RETURN)))
(CNDIR "{DSK}/hearts/dist/")
(FILESLOAD ACTIVEREGIONS HEARTS HNET NNPLAYER)

(DEFINEQ

(R.Env
  (LAMBDA (Name Default)
    (LET ((V (UNIX-GETENV (HNET.Sys Name))))
         (if (AND V (IGREATERP (NCHARS V) 0))
             then V
           else Default))))

(R.Words
  (LAMBDA (Text)
    (for W in (HNET.Words Text) when (IGREATERP (NCHARS W) 0) collect (MKATOM (U-CASE W)))))

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
    (* ; "Fresh players, offered on the net.")
    (R.Tidy)
    (SETQ HNET.MyPlayers NIL)
    (SETQ H.WaitingToPlay NIL)
    (NetHearts (for X in R.Players collect (R.Make X)))
    (SETQ R.OfferedAt (CLOCK 0))
    (SETQ R.State "waiting for someone to start a game")))

(R.GameOver?
  (LAMBDA NIL
    (AND HNET.CardTable
         (OPENWP HNET.CardTable)
         (for S in (WINDOWPROP HNET.CardTable (QUOTE Score)) thereis (AND (NUMBERP S) (IGREATERP S Game.OverScore))))))

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
    (printout R.Status "Room " R.Room " as " R.Name " on " R.Relay T)
    (printout R.Status "Offering: " R.Players T)
    (printout R.Status (OR R.State "") T)
    (printout R.Status "Games played here: " R.Games T)))

(R.Step
  (LAMBDA NIL
    (COND
       ((NOT (HNET.Connected?))
        (LET ((Name (HNET.Connect R.Room R.Name R.Relay)))
             (if (STRINGP Name)
                 then (R.Offer)
               else (SETQ R.State (CONCAT "can't reach the relay: " (CADR Name) "; trying again"))
                    (R.Show)
                    (DISMISS 30000))))
       ((AND HNET.MyPlayers (R.GameOver?))
        (add R.Games 1)
        (SETQ R.State "game over; new players in a moment")
        (R.Show)
        (DISMISS 3000)
        (R.Offer))
       ((AND HNET.MyPlayers HNET.LastFrom (NOT (MEMBER HNET.LastFrom (HNET.PeerNames))))
        (* ; "The house left.  Often it just finished: give the last scores a moment to arrive, and count the game if it ended.")
        (SETQ R.State (CONCAT HNET.LastFrom " left; new players"))
        (R.Show)
        (DISMISS 2000)
        (if (R.GameOver?) then (add R.Games 1))
        (R.Offer))
       ((AND HNET.MyPlayers (IGREATERP (R.Minutes HNET.LastCallAt) R.IdleMinutes))
        (R.Offer))
       ((AND (NULL HNET.MyPlayers) (NULL H.WaitingToPlay))
        (* ; "The house said goodbye before the game ended, or someone took the players from the Exec.")
        (R.Offer))
       (HNET.MyPlayers (SETQ R.State (CONCAT "playing seats " (for P in HNET.MyPlayers collect (fetch Number of P))
                                             " for " (OR HNET.LastFrom "?")))))
    (R.Show)))

(R.Loop
  (LAMBDA NIL
    (while T do (XCL:CONDITION-CASE (R.Step)
                       (CL:ERROR (C)
                              (SETQ R.State (CONCAT "error: " (CL:PRINC-TO-STRING C)))
                              (NLSETQ (R.Show))))
                (DISMISS 2000))))
)

(SETQ R.Room (R.Env "RESIDENTROOM" "athena"))
(SETQ R.Name (R.Env "RESIDENTNAME" "athena"))
(SETQ R.Relay (OR (HNET.EnvRelay) HNET.Relay))
(SETQ R.Players (R.Words (R.Env "RESIDENTPLAYERS" "EP NP CP")))
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
