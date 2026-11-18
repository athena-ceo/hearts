(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "The resident HEARTS Medley (docs/medley-server.md).  Started by docker/resident-run.

    It offers players to the house, over Courier (HCOURIER): anyone opening a table there, from a
    browser or from a Medley, can take them as opponents, and they play here, on this Medley, at up
    to R.Tables tables at once, a fresh set of players for each.  Its screen is on the web: watch
    it, or control it.  One game is on show.  The row of tabs under the status window has one tab
    for each game: choosing one puts that game's card table and its players' Thoughts windows on
    the screen.")

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
    (for W in (READ (OPENSTRINGSTREAM (CONCAT "(" Text ")")))
       collect (MKATOM (U-CASE W)))))

(R.Kind
  (LAMBDA (Type)
    (SELECTQ Type
        (EP "Expert")
        (NP "Neural network")
        (CP "Conservative")
        (CLOWN "Clown")
        (MKSTRING Type))))

(R.Label
  (LAMBDA (Type)
    (* ; "What the house calls a player of this type in its list of opponents.")
    (CONCAT (R.Kind Type) " on Medley")))

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
    (* ; "Close every window of a game: card tables, hands, players' thoughts.")
    (HC.Switch NIL)
    (for W in (OPENWINDOWS) when (R.Ours? W) do (CLOSEW W))
    (SETQ R.NextSlot 0)))

(R.Make
  (LAMBDA (Type)
    (* ; "A player, with its Thoughts window.  The Conservative and the network make their own; a closed-hand Expert narrates only into its hand window, so give it one as PlayHearts does.  HCOURIER calls this for each table, through the forms given to HC.Offer.")
    (LET ((Player (H.MakePlayer Type NIL)))
         (if (EQ Type (QUOTE EP))
             then (PH.GiveThoughtsWindow Player))
         Player)))

(R.NewGame
  (LAMBDA NIL
    (* ; "Before a table's players are made: their Thoughts windows take the same places as every other table's.")
    (SETQ R.NextSlot 0)))

(R.Offer
  (LAMBDA NIL
    (* ; "Offer the players to the house, for R.Tables tables at once.  If the house can't be reached three times running, stop Medley: the emulator joins the NetHub only as it starts, and resident-run starts it again.")
    (R.Tidy)
    (LET ((Result (HC.Offer (for X in R.Players collect (LIST (QUOTE R.Make) (KWOTE X)))
                         R.Key
                         (for X in R.Players collect (R.Label X))
                         R.Tables)))
         (if (EQ (CAR (LISTP Result)) (QUOTE ERROR))
             then (R.Lost (CADDR Result))
           else (SETQ R.Misses 0)
                (SETQ R.CheckedAt (CLOCK 0))))))

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
        then (SETQ R.Status (CREATEW (CREATEREGION 475 804 450 76) "The resident HEARTS Medley"))
             (SETQ R.TabsShown (QUOTE None)))
    (CLEARW R.Status)
    (printout R.Status "At the house " HC.House T)
    (* ; "Four lines fit above the tabs, so the players go on one.")
    (printout R.Status "Offering:")
    (for X in R.Players as N from 1 do (printout R.Status (if (EQ N 1) then " " else ", ") (R.Kind X)))
    (TERPRI R.Status)
    (printout R.Status (OR R.State "") T)
    (printout R.Status "Games played here: " HC.Ended)
    (R.Tabs)))

(R.People
  (LAMBDA (Game)
    (* ; "Who this Medley's players are playing in GAME: the names in the seats that are not its own.")
    (for Name in (fetch (HCGAME Names) of Game) as Seat from 1
       unless (ELT (fetch (HCGAME Seats) of Game) Seat) collect Name)))

(R.TabLabel
  (LAMBDA (Game N)
    (* ; "A tab: the game's number here, the first of the people in it, and a mark on the game on show.")
    (LET ((Who (MKSTRING (OR (CAR (R.People Game)) "table"))))
         (CONCAT (if (EQ Game HC.Shown) then "*" else " ")
                N " " (if (IGREATERP (NCHARS Who) 5) then (SUBSTRING Who 1 5) else Who)))))

(R.Tabs
  (LAMBDA NIL
    (* ; "The row of tabs under the status window, one for each game, oldest first.  It is made again only when the games or the game on show have changed.")
    (LET* ((Games (REVERSE HC.Games))
           (Now (CONS HC.Shown Games)))
          (if (NOT (EQUAL Now R.TabsShown))
              then (if (AND R.TabsWindow (OPENWP R.TabsWindow))
                       then (DETACHWINDOW R.TabsWindow)
                            (CLOSEW R.TabsWindow))
                   (SETQ R.TabsWindow NIL)
                   (if Games
                       then (SETQ R.TabsWindow
                             (MENUWINDOW (create MENU
                                                ITEMS _ (for Game in Games as N from 1
                                                           collect (LIST (R.TabLabel Game N) Game
                                                                         (CONCAT "Show the game with "
                                                                                (PH.Names (R.People Game)))))
                                                WHENSELECTEDFN _ (FUNCTION R.TabSelected)
                                                MENUROWS _ 1
                                                MENUFONT _ (QUOTE (GACHA 10 BOLD)))))
                            (ATTACHWINDOW R.TabsWindow R.Status (QUOTE BOTTOM)))
                   (SETQ R.TabsShown Now)))))

(R.TabSelected
  (LAMBDA (Item Menu Button)
    (* ; "Runs in the mouse process: the game is put on show in a process of its own, which may wait for a trick to finish.")
    (ADD.PROCESS (LIST (QUOTE R.Pick) (KWOTE (CADR Item))) (QUOTE NAME) (QUOTE Hearts.Tab))))

(R.Pick
  (LAMBDA (Game)
    (if (MEMB Game HC.Games) then (HC.Pick Game))
    (R.Show)))

(R.Step
  (LAMBDA NIL
    (for Game in (COPY HC.Games) when (IGREATERP (R.Minutes (fetch (HCGAME HeardAt) of Game)) R.IdleMinutes)
       do (* ; "A game the house has said nothing about for a long time: give its place to another.")
          (HC.Leave Game))
    (COND
       ((NULL HC.Forward)
        (R.Offer))
       ((AND HC.Shown (NOT (MEMB HC.Shown HC.Games))
             (IGREATERP (IDIFFERENCE (CLOCK 0) (fetch (HCGAME EndedAt) of HC.Shown))
                    (if HC.Games then 5000 else 60000)))
        (* ; "The game on show is over: after a moment the newest game takes the screen, or after a minute with no game the screen is cleared.")
        (HC.Switch (CAR HC.Games)))
       ((IGEQ (R.Minutes R.CheckedAt) 1)
        (* ; "Is the house still there?")
        (LET ((Answer (HC.Tables)))
             (if (EQ (CAR (LISTP Answer)) (QUOTE ERROR))
                 then (R.Lost (CADDR Answer))
               else (SETQ R.Misses 0)
                    (SETQ R.CheckedAt (CLOCK 0))))))
    (SETQ R.State (if HC.Games
                      then (CONCAT "playing at " (LENGTH HC.Games) " of " R.Tables " tables")
                    else "waiting for someone to choose these players"))
    (R.Show)))

(R.Loop
  (LAMBDA NIL
    (* ; "An error in a step is shown in the status window, and its message (ERRORMESS) in the Exec; the next step comes two seconds later.")
    (while T do (if (NOT (NLSETQ (R.Step)))
                    then (ERRORMESS NIL)
                         (SETQ R.State "error: see the Exec")
                         (NLSETQ (R.Show)))
                (DISMISS 2000))))
)

(SETQ R.Players (R.Words (R.Env "RESIDENTPLAYERS" "EP NP CP")))
(SETQ R.Key (R.Env "RESIDENTKEY" ""))
(* "How many tables the players are at at once.")
(SETQ R.Tables (OR (FIXP (MKATOM (R.Env "RESIDENTTABLES" "8"))) 8))
(SETQ R.Misses 0)
(SETQ R.CheckedAt NIL)
(SETQ R.IdleMinutes 20)
(* "A finished trick stays on the card table for a second (the 1986 table held it for two): long enough to watch, and half the time of a deal.")
(SETQ HC.TrickPause 1000)
(SETQ R.Status NIL)
(SETQ R.TabsWindow NIL)
(SETQ R.TabsShown (QUOTE None))
(SETQ HC.NewGameFn (QUOTE R.NewGame))
(* "The card table sits under the status window and its row of tabs.")
(SETQ HNET.CTReg (QUOTE (475 370 450 400)))
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
     (if Exec then (SHAPEW Exec (CREATEREGION 475 10 450 334))))
(R.Show)
(ADD.PROCESS (QUOTE (R.Loop)) (QUOTE NAME) (QUOTE Resident))
STOP
