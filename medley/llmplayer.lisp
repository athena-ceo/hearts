;; LLMPLAYER -- a HEARTS player whose moves come from an LLM (not part of the 1986 system).
;;
;;   (FILESLOAD LLMPLAYER)
;;   (LP.Check)                                 is the helper reachable?  is there an API key?
;;   (PlayHearts '(HP LP EP CP))                or (LHearts '(HP LP EP CP))
;;
;; An ordinary Lisp-transport player, like the Conservative: the six-message protocol, no change
;; to the game.  The seat's state is built only from its own messages, so it knows only what a
;; person in that seat would.  For each decision it writes that state to a JSON file and runs
;; medley/llm_player.py, which asks the model and prints one S-expression line.
;;
;; A request goes through a file because long writes to a process stream's stdin lose bytes; see
;; MEDLEY-ISSUES.  The game loop does not check the card a player returns, so this player does:
;; on any failure or unusable answer it plays a safe card and says so in its Thoughts window.

(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "LLMPLAYER -- a HEARTS player that asks an LLM for its moves (2026).  Loads HEARTS if needed.")

(OR (GETD (QUOTE H.PlayGame))
    (FILESLOAD ACTIVEREGIONS HEARTS))

(FILESLOAD UNIXCOMM)

(* "Settings.  The model and effort are the cost controls: see USER-MANUAL.")
(RPAQ? LP.Provider "anthropic")
(RPAQ? LP.Model "claude-opus-5-5")
(RPAQ? LP.Effort "medium")
(RPAQ? LP.TimeoutSeconds 300)
(RPAQ? LP.GraceSeconds 15)
(RPAQ? LP.Python "python3")
(RPAQ? LP.Helper NIL)
(RPAQ? LP.HelperOptions "")
(RPAQ? LP.LogFile NIL)
(RPAQ? LP.TempDir "/tmp")
(RPAQ? LP.Thoughts? T)

(* "Running totals across all LLM seats; (LP.Stats) reports them, (LP.ResetStats) clears them.")
(RPAQ? LP.Decisions 0)
(RPAQ? LP.Fallbacks 0)
(RPAQ? LP.InputTokens 0)
(RPAQ? LP.OutputTokens 0)

(RECORD LP (LP.Name LP.Hand LP.Seat LP.ThoughtWindow LP.OpenHand? LP.HandWindow LP.Plan LP.History
                    LP.PassDir LP.Passed LP.Received LP.Scores LP.Deal))

(RPAQQ LPMapping ((GiveHand . LP.GiveHand)
                  (PassOut . LP.PassOut)
                  (PassIn . LP.PassIn)
                  (Play . LP.Play)
                  (Trick . LP.Trick)
                  (Results . LP.Results)))

(DEFINEQ

(LP.Create
  (LAMBDA (Open?)
    (* ; "A new LLM player.  Unlike the Conservative it always gets a Thoughts window (unless LP.Thoughts? is NIL), because its reasoning is the point; an open hand gets a hand window as well.")
    (LET* ((Name (GENSYM (if (EQUAL LP.Provider "anthropic")
                               then (QUOTE Claude)
                             else (QUOTE LLM))))
           (Win (if LP.Thoughts?
                    then (CREATEW (GETBOXREGION 500 250 NIL NIL NIL
                                         (CONCAT "Please find a place for the thinking window for " Name))
                                (CONCAT "Thoughts of " Name)))))
          (if Win
              then (WINDOWPROP Win (QUOTE SCROLLFN) (FUNCTION SCROLLBYREPAINTFN))
                   (DSPSCROLL T (WINDOWPROP Win (QUOTE DSP))))
          (create Player
                 Name _ Name
                 Type _ (QUOTE Lisp)
                 Object _ (create LP
                                 LP.Name _ Name
                                 LP.ThoughtWindow _ Win
                                 LP.OpenHand? _ Open?
                                 LP.HandWindow _ (if Open?
                                                     then (Open.CreateWindow Name (QUOTE LP)))
                                 LP.Deal _ 0)
                 Mapping _ LPMapping))))

(LP.Think
  (LAMBDA (self Text)
    (* ; "A window wraps long lines itself, but mid-word; the model's remarks are long enough to matter.")
    (LET ((Win (fetch LP.ThoughtWindow of self)))
         (if Win
             then (for Line in (LP.Wrap Text (SUB1 (IQUOTIENT (WINDOWPROP Win (QUOTE WIDTH))
                                                          (CHARWIDTH (CHARCODE M) (DSPFONT NIL Win)))))
                     do (printout Win Line T))))))

(LP.Wrap
  (LAMBDA (Text Columns)
    (* ; "Text as a list of lines at most Columns long, broken at spaces where it can be.")
    (PROG ((Rest (MKSTRING Text))
           Lines Break)
      LOOP
          (if (ILEQ (NCHARS Rest) Columns)
              then (RETURN (NCONC1 Lines Rest)))
          (SETQ Break (OR (for I from Columns to 2 by -1 thereis (EQ (NTHCHARCODE Rest I) 32))
                          Columns))
          (SETQ Lines (NCONC1 Lines (SUBSTRING Rest 1 Break)))
          (SETQ Rest (SUBSTRING Rest (ADD1 Break)))
          (GO LOOP))))

(LP.Redraw
  (LAMBDA (self)
    (if (fetch LP.OpenHand? of self)
        then (Open.RemakeWindow (fetch LP.HandWindow of self)
                    (fetch LP.Hand of self)))))

(LP.GiveHand
  (LAMBDA (self Hand Seat)
    (* ; "A new deal.  A finished game's scores are dropped here, as players can outlive a game.")
    (if (for S in (fetch LP.Scores of self) thereis (IGREATERP S Game.OverScore))
        then (replace LP.Scores of self with NIL)
             (replace LP.Deal of self with 0))
    (replace LP.Hand of self with Hand)
    (replace LP.Seat of self with Seat)
    (replace LP.Plan of self with NIL)
    (replace LP.History of self with NIL)
    (replace LP.PassDir of self with NIL)
    (replace LP.Passed of self with NIL)
    (replace LP.Received of self with NIL)
    (replace LP.Deal of self with (ADD1 (fetch LP.Deal of self)))
    (LP.Think self (CONCAT "--- Deal " (fetch LP.Deal of self) " ---"))
    (LP.Redraw self)))

(LP.PassOut
  (LAMBDA (self PassDir)
    (replace LP.PassDir of self with PassDir)
    (if PassDir
        then (LET* ((Hand (fetch LP.Hand of self))
                    (Cards (LP.Decide self (QUOTE pass)
                                  (Hand.Cards Hand)
                                  3 NIL NIL NIL)))
                   (for C in Cards do (Hand.RemoveCard Hand C))
                   (replace LP.Passed of self with Cards)
                   (LP.Redraw self)
                   Cards))))

(LP.PassIn
  (LAMBDA (self PassIn)
    (for C in PassIn do (Hand.AddCard (fetch LP.Hand of self)
                               C))
    (replace LP.Received of self with PassIn)
    (LP.Redraw self)))

(LP.Play
  (LAMBDA (self Trick HeartsBroken? FirstTrick?)
    (* ; "With only one legal card there is nothing to decide, so no API call.")
    (LET* ((Hand (fetch LP.Hand of self))
           (Legal (H.GetLegals Hand Trick HeartsBroken? FirstTrick?))
           (Card (if (CDR Legal)
                     then (CAR (LP.Decide self (QUOTE play)
                                      Legal 1 Trick HeartsBroken? FirstTrick?))
                   else (LP.Think self (CONCAT "Only one legal card: " (LP.CardName (CAR Legal))))
                        (CAR Legal))))
          (Hand.RemoveCard Hand Card)
          (LP.Redraw self)
          Card)))

(LP.Trick
  (LAMBDA (self Trick)
    (replace LP.History of self
       with (NCONC1 (fetch LP.History of self)
                   (LIST (fetch LeadPlayerNum of Trick)
                         (APPEND (fetch Cards of Trick))
                         (fetch Winner of Trick))))))

(LP.Results
  (LAMBDA (self Scores)
    (replace LP.Scores of self with (APPEND Scores))
    (LP.Think self (CONCAT "Scores by seat: " Scores))))

(LP.Decide
  (LAMBDA (self Decision Candidates Count Trick HeartsBroken? FirstTrick?)
    (* ; "Ask the helper for Count cards from Candidates; returns the cards themselves.  Any failure, or an answer that is not Count different Candidates, gets a safe choice instead.")
    (LET* ((Reply (LP.Ask self Decision Candidates Trick HeartsBroken? FirstTrick?))
           (Cards (AND (EQ (CAR (LISTP Reply)) (QUOTE OK))
                       (LP.MatchCards (CADR Reply) Candidates Count))))
          (SETQ LP.Decisions (ADD1 LP.Decisions))
          (if Cards
              then (LP.NoteAnswer self Reply)
                   Cards
            else (LP.NoteTrouble self Reply)
                 (LP.SafeCards Candidates Count)))))

(LP.NoteAnswer
  (LAMBDA (self Reply)
    (LET ((Usage (CAR (LAST Reply))))
         (replace LP.Plan of self with (CADDR Reply))
         (SETQ LP.InputTokens (IPLUS LP.InputTokens (OR (FIXP (CAR Usage)) 0)))
         (SETQ LP.OutputTokens (IPLUS LP.OutputTokens (OR (FIXP (CADR Usage)) 0)))
         (LP.Think self (CADDDR Reply))
         (LP.Think self (CONCAT "  Plan: " (CADDR Reply))))))

(LP.NoteTrouble
  (LAMBDA (self Reply)
    (LET ((Why (if (AND (EQ (CAR (LISTP Reply)) (QUOTE ERROR)) (STRINGP (CADR Reply)))
                   then (CADR Reply)
                 elseif (EQ (CAR (LISTP Reply)) (QUOTE OK))
                   then "the answer was not a legal choice"
                 else "no usable reply from the helper")))
         (SETQ LP.Fallbacks (ADD1 LP.Fallbacks))
         (LP.Think self (CONCAT "(No answer from the model: " Why ".  Playing safe.)"))
         (PROMPTPRINT (CONCAT (fetch LP.Name of self) " is playing safe: " Why)))))

(LP.MatchCards
  (LAMBDA (Answer Candidates Count)
    (* ; "The Candidates named in Answer, or NIL unless it names exactly Count different ones.  Returns the game's own card objects, not the copies just read.")
    (LET ((Cards (AND (LISTP Answer)
                      (for A in Answer
                         collect (AND (LISTP A)
                                      (for C in Candidates thereis (Card.Equal? C A)))))))
         (if (AND (EQP (LENGTH Cards) Count)
                  (NOT (MEMB NIL Cards))
                  (for Tail on Cards never (MEMB (CAR Tail) (CDR Tail))))
             then Cards))))

(LP.SafeCards
  (LAMBDA (Candidates Count)
    (* ; "The fallback: pass the highest cards, play the lowest.  Legal, not clever.")
    (LET ((Sorted (SORT (APPEND Candidates)
                        (FUNCTION Card.Higher?))))
         (if (EQP Count 1)
             then (LAST Sorted)
           else (for I from 1 to Count as C in Sorted collect C)))))

(LP.Ask
  (LAMBDA (self Decision Candidates Trick HeartsBroken? FirstTrick?)
    (* ; "Returns the helper's reply as a list, or NIL if there is no readable one.")
    (LET* ((Path (CONCAT LP.TempDir "/llmplayer-" (L-CASE (fetch LP.Name of self)) ".json"))
           (File (CONCAT "{UNIX}" Path))
           (Line (AND (NLSETQ (LP.WriteRequest self File Decision Candidates Trick HeartsBroken?
                                     FirstTrick?))
                      (CAR (NLSETQ (LP.RunHelper Path))))))
          (NLSETQ (DELFILE File))
          (AND Line (LP.ParseReply Line)))))

(LP.ParseReply
  (LAMBDA (Line)
    (LET ((CL:*PACKAGE* (CL:FIND-PACKAGE "INTERLISP")))
         (CAR (NLSETQ (READ (OPENSTRINGSTREAM Line (QUOTE INPUT))
                            FILERDTBL))))))

(LP.RunHelper
  (LAMBDA (Path)
    (* ; "Run the helper on a request file; returns its one line of output, or NIL if it gave none in time.  The shell's || answers for a helper that could not run, so a missing python costs no wait.")
    (LET ((Helper (LP.FindHelper)))
         (if (NULL Helper)
             then "(ERROR %"cannot find llm_player.py: set LP.Helper or HEARTSDIR%")"
           else (LP.ReadProcessLine (CONCAT (LP.HelperCommand Helper)
                                            " " Path
                                            " 2>/dev/null || echo '(ERROR %"the helper did not run: is python3 on the path?%")'"))))))

(LP.HelperCommand
  (LAMBDA (Helper)
    (CONCAT LP.Python " " Helper " --provider " LP.Provider " --model " LP.Model " --effort " LP.Effort
           " --timeout " LP.TimeoutSeconds
           (if LP.LogFile
               then (CONCAT " --log " LP.LogFile)
             else "")
           " " LP.HelperOptions)))

(LP.ReadProcessLine
  (LAMBDA (Command)
    (LET ((S (CREATE-PROCESS-STREAM (LP.Sys Command))))
         (* ; "LP.Sys: a _ in LP.Python, LP.Helper and the like, read from a file, would reach the shell as an arrow on a Mac.")
         (if S
             then (CL:UNWIND-PROTECT
                      (LP.ReadLine S (ITIMES 1000 (IPLUS LP.TimeoutSeconds LP.GraceSeconds)))
                      (NLSETQ (CLOSEF S)))
           else "(ERROR %"cannot start a process: Medley needs the X11 path (MEDLEY-ISSUES M2)%")"))))

(LP.ReadLine
  (LAMBDA (S LimitMS)
    (* ; "One line, or NIL at the time limit.  Polled rather than READ directly, because READ would wait forever on a stuck helper.  BLOCK lets the rest of Medley run meanwhile.  EOFP is true whenever nothing is waiting, so it can't tell a slow helper from a dead one; the limit covers both.")
    (PROG ((Start (CLOCK 0))
           Codes B)
      LOOP
          (if (IGREATERP (IDIFFERENCE (CLOCK 0) Start) LimitMS)
              then (RETURN NIL))
          (if (EOFP S)
              then (BLOCK 200)
                   (GO LOOP))
          (SETQ B (BIN S))
          (if (EQ B 10)
              then (RETURN (CONCATCODES (REVERSE Codes))))
          (push Codes B)
          (GO LOOP))))

(LP.FindHelper
  (LAMBDA NIL
    (* ; "LP.Helper if set, else the first llm_player.py found beside the files or in the repo.")
    (OR LP.Helper
        (for Dir in (LIST (UNIX-GETENV "HEARTSDIR")
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/il"))
                          "/hearts/dist"
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/Development/hearts/dist")))
           when Dir
           do (LET ((Path (CONCAT Dir (LP.Sys "/llm_player.py"))))
                   (if (INFILEP (CONCAT "{UNIX}" Path))
                       then (RETURN (SETQ LP.Helper Path))))))))

(LP.Check
  (LAMBDA NIL
    (* ; "Spends nothing.  Returns (CHECK pythonVersion sdkVersion keySet? model), or says what is missing.")
    (LET ((Helper (LP.FindHelper)))
         (if Helper
             then (LET ((Line (LP.ReadProcessLine (CONCAT (LP.HelperCommand Helper)
                                                          " --check 2>/dev/null || echo '(ERROR %"the helper did not run: is python3 on the path?%")'"))))
                       (AND Line (LP.ParseReply Line)))
           else (LIST (QUOTE ERROR) "cannot find llm_player.py: set LP.Helper or HEARTSDIR")))))

(LP.Stats
  (LAMBDA NIL
    (LIST (QUOTE decisions) LP.Decisions (QUOTE fallbacks) LP.Fallbacks
          (QUOTE inputTokens) LP.InputTokens (QUOTE outputTokens) LP.OutputTokens)))

(LP.ResetStats
  (LAMBDA NIL
    (SETQ LP.Decisions 0)
    (SETQ LP.Fallbacks 0)
    (SETQ LP.InputTokens 0)
    (SETQ LP.OutputTokens 0)
    (LP.Stats)))

(LP.WriteRequest
  (LAMBDA (self File Decision Candidates Trick HeartsBroken? FirstTrick?)
    (LET ((S (OPENSTREAM File (QUOTE OUTPUT) (QUOTE NEW))))
         (CL:UNWIND-PROTECT
             (PROGN (LP.JField S "decision" T)
                    (LP.JString S Decision)
                    (LP.JField S "seat")
                    (PRIN3 (fetch LP.Seat of self) S)
                    (LP.JField S "deal")
                    (PRIN3 (fetch LP.Deal of self) S)
                    (if (fetch LP.PassDir of self)
                        then (LP.JField S "direction")
                             (LP.JString S (fetch LP.PassDir of self)))
                    (LP.JField S "hand")
                    (LP.JCards S (Hand.Cards (fetch LP.Hand of self)))
                    (if (EQ Decision (QUOTE play))
                        then (LP.JField S "legal")
                             (LP.JCards S Candidates)
                             (LP.JField S "trick")
                             (LP.JTrick S (fetch LeadPlayerNum of Trick)
                                    (fetch Cards of Trick)
                                    NIL)
                             (LP.JField S "hearts_broken")
                             (PRIN3 (if HeartsBroken? then "true" else "false") S)
                             (LP.JField S "first_trick")
                             (PRIN3 (if FirstTrick? then "true" else "false") S)
                             (LP.JField S "passed")
                             (LP.JCards S (fetch LP.Passed of self))
                             (LP.JField S "received")
                             (LP.JCards S (fetch LP.Received of self))
                             (LP.JField S "history")
                             (LP.JHistory S (fetch LP.History of self)))
                    (LP.JField S "scores")
                    (LP.JList S (OR (fetch LP.Scores of self) (QUOTE (0 0 0 0))))
                    (LP.JField S "over_score")
                    (PRIN3 Game.OverScore S)
                    (if (fetch LP.Plan of self)
                        then (LP.JField S "plan")
                             (LP.JString S (fetch LP.Plan of self)))
                    (PRIN3 "}" S)
                    (TERPRI S))
             (CLOSEF S)))))

(LP.JField
  (LAMBDA (S Name First?)
    (PRIN3 (if First? then "{" else ",") S)
    (LP.JString S Name)
    (PRIN3 ":" S)))

(LP.Sys
  (LAMBDA (Text)
    (* ; "Text, with each _ in it made the underscore the operating system sees in a file name or command.  A _ read from a Lisp file is character 95, which Medley also shows as the left arrow; when the system's format is UTF-8 (a LANG or LC_CTYPE with UTF in it, as on a Mac), Medley turns character 95 in a file name or command into the arrow, U+2190, so the helper's name would be wrong.  The real underscore is whatever a 95 byte from the system reads as.  (What we write into a file goes out byte for byte, so the request's JSON keys need nothing.)")
    (LET ((U (if (GETD (QUOTE SYSTOMSTRING))
                 then (CADR (CHCON (SYSTOMSTRING "a_a")))
               else 95)))
         (if (OR (EQ U 95) (NOT (STRPOS (CHARACTER 95) Text)))
             then Text
           else (CONCATCODES (for C in (CHCON Text) collect (if (EQ C 95) then U else C)))))))

(LP.JString
  (LAMBDA (S Text)
    (PRIN3 "%"" S)
    (for C in (CHCON Text)
       do (* ; "Escape double quote and backslash, by code: 34 and 92.")
          (if (OR (EQ C 34) (EQ C 92))
              then (PRIN3 (CHARACTER 92) S))
          (PRIN3 (CHARACTER C) S))
    (PRIN3 "%"" S)))

(LP.JList
  (LAMBDA (S Numbers)
    (PRIN3 "[" S)
    (for N in Numbers as I from 1
       do (if (IGREATERP I 1) then (PRIN3 "," S))
          (PRIN3 N S))
    (PRIN3 "]" S)))

(LP.JCards
  (LAMBDA (S Cards)
    (PRIN3 "[" S)
    (for C in Cards as I from 1
       do (if (IGREATERP I 1) then (PRIN3 "," S))
          (LP.JString S (LP.CardName C)))
    (PRIN3 "]" S)))

(LP.JTrick
  (LAMBDA (S Leader Cards Winner)
    (PRIN3 "{%"leader%":" S)
    (PRIN3 Leader S)
    (PRIN3 ",%"cards%":" S)
    (LP.JCards S Cards)
    (if Winner
        then (PRIN3 ",%"winner%":" S)
             (PRIN3 Winner S))
    (PRIN3 "}" S)))

(LP.JHistory
  (LAMBDA (S History)
    (PRIN3 "[" S)
    (for H in History as I from 1
       do (if (IGREATERP I 1) then (PRIN3 "," S))
          (LP.JTrick S (CAR H) (CADR H) (CADDR H)))
    (PRIN3 "]" S)))

(LP.CardName
  (LAMBDA (Card)
    (CONCAT (fetch Suit of Card) (fetch Value of Card))))
)

(* "So that (LHearts '(HP LP CP CP)) and PlayHearts both know this player.  Advice, not a
    redefinition: the 1986 H.MakePlayer is untouched, and (UNADVISE 'H.MakePlayer) removes it.")
(RPAQQ LP.MakePlayerAdvice (if (EQ Type (QUOTE LP)) then (RETURN (LP.Create Open?))))
(ADVISE (QUOTE H.MakePlayer) (QUOTE BEFORE) LP.MakePlayerAdvice)

STOP
