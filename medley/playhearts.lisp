;; PLAYHEARTS -- a modern front door for the revived HEARTS (not part of the 1986 system).
;;
;;   (PlayHearts)                            ask for the players and options with menus
;;   (PlayHearts '(HP EP EP CP) Open? ManualDeal?)   ...or give them
;;
;; Opens the card table with a menu bar -- Start Game, Setup..., Exit -- and returns at once.
;; Nothing plays until Start Game.  Each game runs in its own process on the ORIGINAL 1986
;; game loop (H.PlayGame), so the Exec stays free.  Exit (or closing the table) stops any game
;; and closes every Hearts window this session opened.
;;
;; The 1986 entry point LHearts is untouched: it starts playing at once and plays game after
;; game until interrupted.  This file only adds functions (prefix PH.); it redefines nothing.

(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "PLAYHEARTS -- menu-driven front end for HEARTS (2026).  Loads HEARTS if needed.")

(OR (GETD (QUOTE H.PlayGame))
    (FILESLOAD ACTIVEREGIONS HEARTS))

(RPAQ? PH.CurrentTable NIL)

(RPAQQ PH.PlayerTypes (("Human (you)" (QUOTE HP)
                              "You play, clicking cards in your own window")
                       ("Expert" (QUOTE EP)
                              "The 1986 KEE expert system: models opponents, can shoot or eclipse")
                       ("Conservative" (QUOTE CP)
                              "A fixed minimizing strategy in Lisp")
                       ("Clown" (QUOTE CLOWN)
                              "Plays a random legal card")))

(RPAQQ PH.WindowTitles ("Hearts Card Table" "Thoughts of " "Hearts window for " "Hearts Window for "
                        "Dealing Window"))

(RPAQQ PH.Props (PH.Players PH.Config PH.Open? PH.ManualDeal? PH.Before PH.Process PH.Played?))

(DEFINEQ

(PlayHearts
  (LAMBDA (Config Open? ManualDeal? Region)
    (* ; "Set up a Hearts session and return its card table.  With no Config, ask for the players and options.  Seats left empty are filled with Conservatives.  Region (optional) places the table.")
    (PROG (Answers Before Players Table)
          (if (NULL Config)
              then (SETQ Answers (PH.AskConfig))
                   (if (NULL Answers)
                       then (RETURN NIL))
                   (SETQ Config (CAR Answers))
                   (SETQ Open? (CADR Answers))
                   (SETQ ManualDeal? (CADDR Answers)))
          (SETQ Config (APPEND Config))
          (while (LESSP (LENGTH Config) 4) do (SETQ Config (NCONC1 Config (QUOTE CP))))
          (if (AND (FMEMB (QUOTE EP) Config) (NOT (GETD (QUOTE EP.Create))))
              then (FILESLOAD EXPERT))
          (SETQ Before (OPENWINDOWS))
          (SETQ Players (for Type in Config collect (PH.MakePlayer Type Open?)))
          (for P in Players as I from 1 do (replace Number of P with I))
          (SETQ Table (PH.OpenTable Players Region))
          (WINDOWPROP Table (QUOTE PH.Players) Players)
          (WINDOWPROP Table (QUOTE PH.Config) Config)
          (WINDOWPROP Table (QUOTE PH.Open?) Open?)
          (WINDOWPROP Table (QUOTE PH.ManualDeal?) ManualDeal?)
          (WINDOWPROP Table (QUOTE PH.Before) Before)
          (PROMPTPRINT "Hearts: choose Start Game on the card table to play.")
          (RETURN Table))))

(PH.AskConfig
  (LAMBDA NIL
    (* ; "Ask for the four seats and the options with pop-up menus.  -> (Config Open? ManualDeal?), or NIL if a menu is dismissed.")
    (PROG ((I 1) Config Type Open? Manual Think)
      SEAT
          (if (GREATERP I 4) then (GO OPTIONS))
          (SETQ Type (MENU (create MENU
                                   ITEMS _ PH.PlayerTypes
                                   TITLE _ (CONCAT "Player " I " (clockwise)")
                                   MENUFONT _ (QUOTE (GACHA 10 BOLD)))))
          (if (NULL Type) then (RETURN NIL))
          (SETQ Config (NCONC1 Config Type))
          (SETQ I (ADD1 I))
          (GO SEAT)
      OPTIONS
          (SETQ Open? (PH.YesNo "Play with open hands?"))
          (if (NULL Open?) then (RETURN NIL))
          (SETQ Manual (PH.YesNo "Deal the cards by hand?"))
          (if (NULL Manual) then (RETURN NIL))
          (if (FMEMB (QUOTE CP) Config)
              then (SETQ Think (PH.YesNo "Show the Conservatives' thoughts?"))
                   (if (NULL Think) then (RETURN NIL))
                   (SETQ ThinkFlag? (EQ Think (QUOTE YES))))
          (RETURN (LIST Config (EQ Open? (QUOTE YES)) (EQ Manual (QUOTE YES)))))))

(PH.YesNo
  (LAMBDA (Question)
    (MENU (create MENU
                  ITEMS _ (QUOTE (("Yes" (QUOTE YES)) ("No" (QUOTE NO))))
                  TITLE _ Question
                  MENUCOLUMNS _ 2
                  MENUFONT _ (QUOTE (GACHA 10 BOLD))))))

(PH.MakePlayer
  (LAMBDA (Type Open?)
    (* ; "Like H.MakePlayer, but asks a human's name in the prompt window, which works from any process (HP.Create would read it from the Exec).")
    (if (EQ Type (QUOTE HP))
        then (HP.Create (OR (PROMPTFORWORD "Your name for this game:" NIL NIL PROMPTWINDOW)
                            "Player"))
      else (H.MakePlayer Type Open?))))

(PH.OpenTable
  (LAMBDA (Players Region)
    (* ; "The 1986 card table (CT.Open), plus our menu bar and close handler.")
    (LET ((Table (CT.Open Players Region))
          Menu)
         (SETQ Menu (create MENU
                            ITEMS _ (LIST (LIST "Start Game" (LIST (QUOTE PH.Start) Table)
                                                "Play a game with these players")
                                          (LIST "Setup..." (LIST (QUOTE PH.Setup) Table)
                                                "Choose new players and options")
                                          (LIST "Exit" (LIST (QUOTE PH.Exit) Table)
                                                "Stop, and close all the Hearts windows"))
                            WHENSELECTEDFN _ (FUNCTION PH.MenuSelected)
                            MENUROWS _ 1
                            MENUFONT _ (QUOTE (GACHA 10 BOLD))))
         (ATTACHWINDOW (MENUWINDOW Menu) Table (QUOTE TOP))
         (WINDOWPROP Table (QUOTE CLOSEFN) (FUNCTION PH.TableClosed))
         (SETQ PH.CurrentTable Table)
         Table)))

(PH.MenuSelected
  (LAMBDA (Item Menu Button)
    (* ; "Runs in the mouse process: do quick things here, and give anything interactive its own process.")
    (LET ((Fn (CAR (CADR Item)))
          (Table (CADR (CADR Item))))
         (if (EQ Fn (QUOTE PH.Setup))
             then (ADD.PROCESS (LIST (QUOTE PH.Setup) (KWOTE Table)) (QUOTE NAME) (QUOTE Hearts.Setup))
           else (APPLY* Fn Table)))))

(PH.Running?
  (LAMBDA (Table)
    (LET ((Proc (WINDOWPROP Table (QUOTE PH.Process))))
         (AND Proc (PROCESSP Proc) Proc))))

(PH.Start
  (LAMBDA (Table)
    (if (PH.Running? Table)
        then (PROMPTPRINT "A game is already being played.  Exit stops it.")
             NIL
      else (LET ((Proc (ADD.PROCESS (LIST (QUOTE PH.RunGame) (KWOTE Table))
                              (QUOTE NAME) (QUOTE Hearts))))
                (WINDOWPROP Table (QUOTE PH.Process) Proc)
                Proc))))

(PH.RunGame
  (LAMBDA (Table)
    (* ; "One game, in its own process, on the 1986 game loop.  Every game after the first gets a fresh table in the same place (CT.Open lays out and scores a new table).")
    (LET ((Players (WINDOWPROP Table (QUOTE PH.Players))))
         (if (WINDOWPROP Table (QUOTE PH.Played?))
             then (SETQ Table (PH.ReopenTable Table)))
         (WINDOWPROP Table (QUOTE PH.Played?) T)
         (WINDOWPROP Table (QUOTE PH.Process) (THIS.PROCESS))
         (SETQ CT.All (LIST Table))
         (PROMPTPRINT "Hearts: new game.")
         (H.PlayGame Players (WINDOWPROP Table (QUOTE PH.ManualDeal?)))
         (SETQ H.GameList (NCONC1 H.GameList H.LastGame))
         (WINDOWPROP Table (QUOTE PH.Process) NIL)
         (PROMPTPRINT (CONCAT "Game over -- " (PH.WinnerNames H.LastGame Players)
                             " won.  Start Game to play again, or Exit."))
         H.LastGame)))

(PH.ReopenTable
  (LAMBDA (Old)
    (LET ((New (PH.OpenTable (WINDOWPROP Old (QUOTE PH.Players)) (WINDOWPROP Old (QUOTE REGION)))))
         (for P in PH.Props do (WINDOWPROP New P (WINDOWPROP Old P)))
         (WINDOWPROP Old (QUOTE CLOSEFN) NIL)
         (CLOSEW Old)
         New)))

(PH.WinnerNames
  (LAMBDA (Game Players)
    (LET ((Names (for N in (fetch Winners of Game) collect (fetch Name of (CAR (NTH Players N))))))
         (if (CDR Names)
             then (CONCATLIST (CDR (for N in Names join (LIST " and " N))))
           else (MKSTRING (CAR Names))))))

(PH.Setup
  (LAMBDA (Table)
    (* ; "Ask again, and start a new session at the same place.")
    (LET ((Answers (PH.AskConfig))
          (Region (WINDOWPROP Table (QUOTE REGION))))
         (if Answers
             then (PH.Exit Table)
                  (PlayHearts (CAR Answers) (CADR Answers) (CADDR Answers) Region)))))

(PH.TableClosed
  (LAMBDA (Table)
    (* ; "The user closed the card table: end the session (the table itself is already closing).")
    (PH.Exit Table T)
    NIL))

(PH.Exit
  (LAMBDA (Table TableClosing?)
    (* ; "Stop any game in progress and close every Hearts window opened since this session began: the table, thought windows, hand windows, a dealing window.")
    (LET ((Proc (PH.Running? Table))
          (Before (WINDOWPROP Table (QUOTE PH.Before))))
         (if (AND Proc (NEQ Proc (THIS.PROCESS)))
             then (DEL.PROCESS Proc))
         (WINDOWPROP Table (QUOTE PH.Process) NIL)
         (if (NOT TableClosing?)
             then (WINDOWPROP Table (QUOTE CLOSEFN) NIL))
         (for W in (OPENWINDOWS) when (AND (NOT (MEMB W Before))
                                           (NOT (AND TableClosing? (EQ W Table)))
                                           (PH.HeartsWindow? W))
            do (WINDOWPROP W (QUOTE CLOSEFN) NIL)
               (CLOSEW W))
         (PH.ForgetPlayers (WINDOWPROP Table (QUOTE PH.Players)))
         (SETQ CT.All NIL)
         (if (EQ PH.CurrentTable Table) then (SETQ PH.CurrentTable NIL))
         (PROMPTPRINT "Hearts: closed.")
         T)))

(PH.HeartsWindow?
  (LAMBDA (W)
    (LET ((Title (WINDOWPROP W (QUOTE TITLE))))
         (AND (STRINGP Title)
              (for Prefix in PH.WindowTitles thereis (STRPOS Prefix Title 1 NIL T))))))

(PH.ForgetPlayers
  (LAMBDA (Players)
    (* ; "Delete this session's Expert units (player, history, opponent models).")
    (if (GETD (QUOTE UNITDELETE))
        then (for P in Players when (EQ (fetch Type of P) (QUOTE Kee))
                do (LET ((U (fetch Object of P)))
                        (for Slot in (QUOTE (history LeftPlayer RightPlayer AcrossPlayer))
                           do (UNITDELETE (GET.VALUE U Slot)))
                        (UNITDELETE U))))))
)
