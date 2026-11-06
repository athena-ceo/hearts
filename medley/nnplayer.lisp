;; NNPLAYER -- a HEARTS player that is a neural network, running entirely in Interlisp (not part of
;; the 1986 system).
;;
;;   (FILESLOAD NNPLAYER)
;;   (PlayHearts '(HP NP EP CP))                or (LHearts '(HP NP EP CP))
;;
;; An ordinary Lisp-transport player: the six-message protocol, no change to the game, and no outside
;; help while it plays.  The network was trained by self-play outside Medley (selfplay/train.py).
;; NP.Features is the Lisp twin of selfplay/features.py, and NP.Scores runs the same two hidden layers
;; of rectified units over weights read from the file HEARTSNET (selfplay/export_lisp.py).

(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "NNPLAYER -- a HEARTS player that is a neural network, in pure Interlisp (2026).  Loads HEARTS if needed.")

(OR (GETD (QUOTE H.PlayGame))
    (FILESLOAD ACTIVEREGIONS HEARTS))

(FILESLOAD UNIXCOMM)

(* "Settings.  NP.ModelFile is found beside the other files if NIL.")
(RPAQ? NP.ModelFile NIL)
(RPAQ? NP.Thoughts? T)

(* "The network, once read: NP.Net is (layer1 bias1 layer2 bias2 policy policyBias), each layer an array of raw float rows.")
(RPAQ? NP.Net NIL)
(RPAQ? NP.Moves 0)
(RPAQ? NP.Milliseconds 0)

(RECORD NP (NP.Name NP.Hand NP.Seat NP.ThoughtWindow NP.PassDir NP.Passed NP.Received NP.History))

(RPAQQ NPMapping ((GiveHand . NP.GiveHand)
                  (PassOut . NP.PassOut)
                  (PassIn . NP.PassIn)
                  (Play . NP.Play)
                  (Trick . NP.Trick)
                  (Results . NP.Results)))

(DEFINEQ

(NP.Create
  (LAMBDA (Open?)
    (NP.Load)
    (LET* ((Name (GENSYM (QUOTE Neural)))
           (Win (if NP.Thoughts?
                    then (CREATEW (GETBOXREGION 400 200 NIL NIL NIL
                                         (CONCAT "Please find a place for the thinking window for " Name))
                                (CONCAT "Thoughts of " Name)))))
          (if Win
              then (WINDOWPROP Win (QUOTE SCROLLFN) (FUNCTION SCROLLBYREPAINTFN))
                   (DSPSCROLL T (WINDOWPROP Win (QUOTE DSP))))
          (create Player
                 Name _ Name
                 Type _ (QUOTE Lisp)
                 Object _ (create NP NP.Name _ Name NP.ThoughtWindow _ Win)
                 Mapping _ NPMapping))))

(NP.GiveHand
  (LAMBDA (self Hand Seat)
    (replace NP.Hand of self with Hand)
    (replace NP.Seat of self with Seat)
    (replace NP.PassDir of self with NIL)
    (replace NP.Passed of self with NIL)
    (replace NP.Received of self with NIL)
    (replace NP.History of self with NIL)))

(NP.PassOut
  (LAMBDA (self PassDir)
    (replace NP.PassDir of self with PassDir)
    (if PassDir
        then (LET* ((Hand (fetch NP.Hand of self))
                    (All (Hand.Cards Hand))
                    Selected)
                   (for I from 1 to 3
                      do (SETQ Selected
                           (NCONC1 Selected
                                   (NP.Best self (QUOTE pass)
                                          (for C in All collect C unless (MEMB C Selected))
                                          All Selected NIL NIL NIL))))
                   (for C in Selected do (Hand.RemoveCard Hand C))
                   (replace NP.Passed of self with Selected)
                   Selected))))

(NP.PassIn
  (LAMBDA (self PassIn)
    (for C in PassIn do (Hand.AddCard (fetch NP.Hand of self) C))
    (replace NP.Received of self with PassIn)))

(NP.Play
  (LAMBDA (self Trick HeartsBroken? FirstTrick?)
    (LET* ((Hand (fetch NP.Hand of self))
           (Legal (H.GetLegals Hand Trick HeartsBroken? FirstTrick?))
           (Card (if (CDR Legal)
                     then (NP.Best self (QUOTE play) Legal (Hand.Cards Hand) NIL
                                 Trick HeartsBroken? FirstTrick?)
                   else (CAR Legal))))
          (Hand.RemoveCard Hand Card)
          Card)))

(NP.Trick
  (LAMBDA (self Trick)
    (replace NP.History of self
       with (NCONC1 (fetch NP.History of self)
                   (LIST (fetch LeadPlayerNum of Trick)
                         (APPEND (fetch Cards of Trick))
                         (fetch Winner of Trick))))))

(NP.Results
  (LAMBDA (self Scores)
    (NP.Think self (CONCAT "Scores by seat: " Scores))))

(NP.Think
  (LAMBDA (self Text)
    (if (fetch NP.ThoughtWindow of self)
        then (printout (fetch NP.ThoughtWindow of self) Text T))))

(NP.Best
  (LAMBDA (self Decision Candidates Hand Selected Trick HeartsBroken? FirstTrick?)
    (* ; "The candidate the network scores highest.  Thinks aloud with the scores of the top few.")
    (LET* ((Start (CLOCK 0))
           (Active (NP.Features self Decision Candidates Hand Selected Trick HeartsBroken? FirstTrick?))
           (Scores (NP.Scores Active (for C in Candidates collect (NP.CardIndex C))))
           (Best NIL)
           (BestScore NIL))
          (for C in Candidates as S in Scores
             do (if (OR (NULL BestScore) (GREATERP S BestScore))
                    then (SETQ Best C)
                         (SETQ BestScore S)))
          (SETQ NP.Moves (ADD1 NP.Moves))
          (SETQ NP.Milliseconds (IPLUS NP.Milliseconds (IDIFFERENCE (CLOCK 0) Start)))
          (if (fetch NP.ThoughtWindow of self)
              then (NP.Think self (NP.Summary Decision Candidates Scores)))
          Best)))

(NP.Summary
  (LAMBDA (Decision Candidates Scores)
    (* ; "The choices with their shares of the network's preference, best first.")
    (LET* ((Top (APPLY (FUNCTION MAX) Scores))
           (Weights (for S in Scores collect (ANTILOG (DIFFERENCE S Top))))
           (Total (APPLY (FUNCTION PLUS) Weights))
           (Pairs (SORT (for C in Candidates as W in Weights collect (CONS (QUOTIENT W Total) C))
                        (FUNCTION (LAMBDA (A B) (GREATERP (CAR A) (CAR B))))))
           (Text (CONCAT Decision ":")))
          (for P in Pairs as I from 1 to 4
             do (SETQ Text (CONCAT Text " " (NP.CardName (CDR P)) " "
                                  (FIX (TIMES 100.0 (CAR P))) "%%")))
          Text)))

(NP.CardName
  (LAMBDA (Card)
    (CONCAT (fetch Suit of Card) (fetch Value of Card))))

(NP.CardIndex
  (LAMBDA (Card)
    (* ; "0-51: suits C D H S, then ranks 2 to A.  The order of DECK in selfplay/hearts_sim.py.")
    (IPLUS (ITIMES 13 (NP.SuitIndex (fetch Suit of Card)))
           (LET ((V (fetch Value of Card)))
                (SELECTQ V
                    (J 9)
                    (Q 10)
                    (K 11)
                    (A 12)
                    (IDIFFERENCE V 2))))))

(NP.SuitIndex
  (LAMBDA (Suit)
    (SELECTQ Suit
        (C 0)
        (D 1)
        (H 2)
        3)))

(NP.Points
  (LAMBDA (Card)
    (if (EQ (fetch Suit of Card) (QUOTE H))
        then 1
      elseif (AND (EQ (fetch Suit of Card) (QUOTE S)) (EQ (fetch Value of Card) (QUOTE Q)))
        then 13
      else 0)))

(NP.Relative
  (LAMBDA (Leader Position Seat)
    (* ; "Seat of the player at Position in a trick, counted from my own seat: 0 is me.")
    (IMOD (IPLUS (SUB1 Leader) Position (IMINUS (SUB1 Seat)) 8) 4)))

(NP.Features
  (LAMBDA (self Decision Candidates Hand Selected Trick HeartsBroken? FirstTrick?)
    (* ; "selfplay/features.py, as a list of (index . value) with no duplicates.  Each feature is set once in a table, so a repeated setting cannot count twice.")
    (LET ((X (ARRAY 512 (QUOTE POINTER) 0 0))
          (Seat (fetch NP.Seat of self)))
         (for C in Hand do (SETA X (IPLUS 0 (NP.CardIndex C)) 1))
         (SETA X (IPLUS 396 (SELECTQ (fetch NP.PassDir of self)
                                (Left 0)
                                (Across 1)
                                (Right 2)
                                3))
               1)
         (for C in Candidates do (SETA X (IPLUS 460 (NP.CardIndex C)) 1))
         (if (EQ Decision (QUOTE pass))
             then (SETA X (IPLUS 400 (LENGTH Selected)) 1)
                  (for C in Selected do (SETA X (IPLUS 404 (NP.CardIndex C)) 1))
           else (SETA X 403 1)
                (LET ((Taken (ARRAY 4 (QUOTE POINTER) 0 0))
                      Seen)
                     (for Done in (fetch NP.History of self)
                        do (LET* ((Leader (CAR Done))
                                  (Cards (CADR Done))
                                  (LeadSuit (fetch Suit of (CAR Cards))))
                                 (for C in Cards as I from 0
                                    do (push Seen C)
                                       (if (NEQ (fetch Suit of C) LeadSuit)
                                           then (SETA X (IPLUS 372 (ITIMES 4 (NP.Relative Leader I Seat))
                                                               (NP.SuitIndex LeadSuit))
                                                      1))
                                       (SETA Taken (SUB1 (CADDR Done))
                                             (IPLUS (ELT Taken (SUB1 (CADDR Done))) (NP.Points C))))))
                     (LET* ((Cards (fetch Cards of Trick))
                            (Leader (fetch LeadPlayerNum of Trick))
                            (LeadSuit (AND Cards (fetch Suit of (CAR Cards))))
                            (BestAt 0)
                            (BestIndex (AND Cards (NP.CardIndex (CAR Cards)))))
                           (SETA X (IPLUS 364 (LENGTH Cards)) 1)
                           (for C in Cards as I from 0
                              do (push Seen C)
                                 (SETA X (IPLUS 208 (ITIMES 52 I) (NP.CardIndex C)) 1)
                                 (if (NEQ (fetch Suit of C) LeadSuit)
                                     then (SETA X (IPLUS 372 (ITIMES 4 (NP.Relative Leader I Seat))
                                                         (NP.SuitIndex LeadSuit))
                                                1)
                                   elseif (IGREATERP (NP.CardIndex C) BestIndex)
                                     then (SETQ BestAt I)
                                          (SETQ BestIndex (NP.CardIndex C))))
                           (if Cards
                               then (SETA X (IPLUS 368 (NP.Relative Leader BestAt Seat)) 1)))
                     (for C in Seen do (SETA X (IPLUS 52 (NP.CardIndex C)) 1))
                     (for C in (fetch NP.Passed of self)
                        do (if (NOT (for S in Seen thereis (AND (EQ (fetch Suit of S) (fetch Suit of C))
                                                                 (EQUAL (fetch Value of S) (fetch Value of C)))))
                               then (SETA X (IPLUS 104 (NP.CardIndex C)) 1)))
                     (for C in (fetch NP.Received of self) do (SETA X (IPLUS 156 (NP.CardIndex C)) 1))
                     (for I from 0 to 3
                        do (LET ((Relative (IMOD (IPLUS I (IMINUS (SUB1 Seat)) 8) 4))
                                 (Points (ELT Taken I)))
                                (if (NEQ Points 0)
                                    then (SETA X (IPLUS 388 Relative) (QUOTIENT (FLOAT Points) 26.0))
                                         (SETA X (IPLUS 456 Relative) 1))))
                     (if HeartsBroken? then (SETA X 392 1))
                     (if FirstTrick? then (SETA X 393 1))
                     (if (for S in Seen thereis (AND (EQ (fetch Suit of S) (QUOTE S))
                                                     (EQ (fetch Value of S) (QUOTE Q))))
                         then (SETA X 394 1))
                     (SETA X 395 (QUOTIENT (FLOAT (ADD1 (LENGTH (fetch NP.History of self)))) 13.0))))
         (for I from 0 to 511 collect (CONS I (FLOAT (ELT X I))) when (NEQ (ELT X I) 0)))))

(NP.Layer
  (LAMBDA (Rows Bias Count Active)
    (* ; "One hidden layer: Active is a list of (column . value) inputs.  Returns the outputs that are above zero, as the same kind of list.")
    (for R from 0 to (SUB1 Count)
       join (LET ((Sum (\GETBASEFLOATP Bias (LLSH R 1)))
                  (Row (ELT Rows R)))
                 (for A in Active
                    do (SETQ Sum (FPLUS Sum (FTIMES (\GETBASEFLOATP Row (LLSH (CAR A) 1)) (CDR A)))))
                 (if (FGREATERP Sum 0.0)
                     then (LIST (CONS R Sum)))))))

(NP.Scores
  (LAMBDA (Active Cards)
    (* ; "The network's score for each card index in Cards.")
    (LET* ((H1 (NP.Layer (CAR NP.Net) (CADR NP.Net) 256 Active))
           (H2 (NP.Layer (CADDR NP.Net) (CADDDR NP.Net) 256 H1))
           (Rest (CDDDDR NP.Net))
           (Policy (CAR Rest))
           (Bias (CADR Rest)))
          (for J in Cards
             collect (LET ((Sum (\GETBASEFLOATP Bias (LLSH J 1)))
                           (Row (ELT Policy J)))
                          (for A in H2
                             do (SETQ Sum (FPLUS Sum (FTIMES (\GETBASEFLOATP Row (LLSH (CAR A) 1)) (CDR A)))))
                          Sum)))))

(NP.FindModel
  (LAMBDA NIL
    (OR NP.ModelFile
        (for Dir in (LIST (UNIX-GETENV "HEARTSDIR")
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/il"))
                          "/hearts/dist"
                          (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/Development/hearts/dist")))
           when Dir
           do (LET ((Path (CONCAT Dir "/HEARTSNET")))
                   (if (INFILEP (CONCAT "{UNIX}" Path))
                       then (RETURN (SETQ NP.ModelFile Path))))))))

(NP.ReadRows
  (LAMBDA (S Rows Columns)
    (* ; "An array of Rows blocks of Columns raw floats, read straight off the file.")
    (LET ((Result (ARRAY Rows (QUOTE POINTER) NIL 0)))
         (for R from 0 to (SUB1 Rows)
            do (SETA Result R (NP.ReadBlock S Columns)))
         Result)))

(NP.ReadBlock
  (LAMBDA (S Count)
    (LET ((Block (\ALLOCBLOCK Count)))
         (\BINS S Block 0 (ITIMES 4 Count))
         Block)))

(NP.Load
  (LAMBDA (Force?)
    (* ; "Read the weights once.  Layer sizes are fixed; see selfplay/export_lisp.py.")
    (if (OR Force? (NULL NP.Net))
        then (LET ((Path (NP.FindModel)))
                  (if (NULL Path)
                      then (ERROR "NNPLAYER: can't find the network file HEARTSNET; set NP.ModelFile"))
                  (LET ((S (OPENSTREAM (CONCAT "{UNIX}" Path) (QUOTE INPUT) (QUOTE OLD))))
                       (CL:UNWIND-PROTECT
                           (LET* ((W1 (NP.ReadRows S 256 512))
                                  (B1 (NP.ReadBlock S 256))
                                  (W2 (NP.ReadRows S 256 256))
                                  (B2 (NP.ReadBlock S 256))
                                  (WP (NP.ReadRows S 52 256))
                                  (BP (NP.ReadBlock S 52)))
                                 (SETQ NP.Net (LIST W1 B1 W2 B2 WP BP)))
                           (CLOSEF S)))))
    T))

(NP.Stats
  (LAMBDA NIL
    (LIST (QUOTE moves) NP.Moves (QUOTE milliseconds) NP.Milliseconds)))

)

(* "Compile the arithmetic: interpreted, a move takes far too long.")
(NLSETQ (CL:COMPILE (QUOTE NP.Layer)))
(NLSETQ (CL:COMPILE (QUOTE NP.Scores)))

(RPAQQ NP.MakePlayerAdvice (if (EQ Type (QUOTE NP)) then (RETURN (NP.Create Open?))))
(ADVISE (QUOTE H.MakePlayer) (QUOTE BEFORE) NP.MakePlayerAdvice)

STOP
