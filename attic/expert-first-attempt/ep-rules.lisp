;; -*- Mode: Lisp; Package: Interlisp -*-
;; EP-RULES.LISP  —  HEARTS Expert Player: rules engine + all production rules
;;
;; This file replaces the IntelliCorp KEE rule system (RuleSystem2 backward chainer
;; with weighted rules and EMYCIN certainty factors).  It provides:
;;
;;   1. A minimal weighted-rule engine (EP.RuleSystem) that:
;;        - Each rule is stored as (rule-name weight test-fn action-fn)
;;        - Rules are sorted by descending weight and tried in order.
;;        - First rule whose test passes fires (backward-chain on the goal slot).
;;        - The engine mirrors KEE's "find the highest-weight applicable rule and
;;          execute its THEN clause, including DO side-effects".
;;
;;   2. All ~90 production rules from kee-expert-rules.txt, translated to
;;      Interlisp lambda pairs (test + action), grouped in the same rule classes
;;      as the original KEE file:
;;        evaluation.rules / trick.evaluation
;;        evaluation.rules / passin.evaluation
;;        opponent.trick.evaluation
;;        opponent.passin.evaluation
;;        initial.evaluation
;;        play.rules / minimizing.play / lead.play
;;        play.rules / minimizing.play / follow.play
;;        play.rules / minimizing.play / dump.play
;;        play.rules / eclipsing.play / eclipse.lead
;;        play.rules / eclipsing.play / eclipse.follow
;;        play.rules / eclipsing.play / eclipse.dump
;;        play.rules / shooting.play / shoot.lead
;;        play.rules / shooting.play / shoot.follow
;;        play.rules / shooting.play / shoot.dump
;;        passout.rules / minimizing.passout
;;        passout.rules / shooting.passout
;;
;;   3. Helper predicates and card-list functions used by the rules
;;      (Not.Null, Non.Null, CardList.EliminateSuits, CardList.PointCards,
;;       CardList.ShortestSuit, CardList.HighSpades?, CardList.BridgePoints,
;;       Card.PrintCard, Card.CardsBetween, EP.NumberWithPoints …).
;;
;; Design note:
;;   KEE's (QUERY '(THE Slot OF unit IS ?Var) 1 '(rule-class)) maps to
;;   (EP.RunRules self 'rule-class 'Slot) which returns the value found or NIL.
;;   KEE's :UPDATE certainty accumulation maps to EP.CF.Update (in ep-loops.lisp).
;;
;; Written for the HEARTS revival (github.com/athena-ceo/hearts).
;; Phase 2b — KEE Expert Player reimplementation.
;; Author: Claude Code (Anthropic), with Harley Davis, 2026.

;; ============================================================
;; Section 1: Helper predicates / card-list utilities
;; (Some already exist in hearts-core.lisp; these fill the gaps.)
;; ============================================================
(DEFINEQ

(Not.Null
  [LAMBDA (X)                                                   (* hed "2026 revival")
    (* Already defined in hearts-core.lisp; kept here for completeness.
       Returns X if non-NIL, NIL otherwise. *)
    X])

(Non.Null
  [LAMBDA (X)                                                   (* hed "2026 revival")
    (* Alias used in one original rule — "Non.Null" vs "Not.Null". *)
    X])

(CardList.EliminateSuits
  [LAMBDA (CardList Suits)                                      (* hed "2026 revival")
    (* Remove all cards whose suit is in Suits from CardList. *)
    (for Card in CardList collect Card
       unless (FMEMB (Card.Suit Card) Suits)])

(CardList.CardsOfSuits
  [LAMBDA (CardList Suits)                                      (* hed "2026 revival")
    (* Keep only cards whose suit is in Suits. *)
    (for Card in CardList collect Card
       when (FMEMB (Card.Suit Card) Suits)])

(CardList.PointCards
  [LAMBDA (CardList)                                            (* hed "2026 revival")
    (* A card is a "point card" if it is a Heart or the Queen of Spades. *)
    (for Card in CardList collect Card
       when (OR (EQUAL (Card.Suit Card) (QUOTE H))
                (Card.Equal? Card (CP.Maggie])

(CardList.ShortestSuit
  [LAMBDA (CardList)                                            (* hed "2026 revival")
    (* Return the suit (symbol) with the fewest cards in CardList. *)
    (LET ((best NIL)
          (bestLen 99))
      (for Suit in SuitValues
         do (LET ((n (LENGTH (CardList.CardsOfSuit CardList Suit))))
              (if (AND (GREATERP n 0)
                       (LESSP n bestLen))
                  then (SETQ best Suit)
                       (SETQ bestLen n))))
      best])

(CardList.HighSpades?
  [LAMBDA (SpadeList)                                           (* hed "2026 revival")
    (* Return the highest spade in SpadeList if it is J or higher, else NIL.
       Used as both a boolean predicate and a value return. *)
    (LET ((Top (Card.MaxCard SpadeList)))
      (if (AND Top (Card.Higher? Top (Card.Create (QUOTE J) (QUOTE S))))
          then Top
        else NIL])

(CardList.BridgePoints
  [LAMBDA (CardList)                                            (* hed "2026 revival")
    (* Standard Goren high-card point count: A=4 K=3 Q=2 J=1. *)
    (for Card in CardList
       sum (SELECTQ (Card.Value Card)
                    ((14)
                      4)
                    ((13)
                      3)
                    ((12)
                      2)
                    ((11)
                      1)
                    0)])

(Hand.FaceCards
  [LAMBDA (Hand)                                                (* hed "2026 revival")
    (* Return a flat list of all face cards (J/Q/K/A) in the hand. *)
    (for Card in (Hand.Cards Hand) collect Card
       when (GEQ (Card.Value Card) 11])

(Hand.MaxCard
  [LAMBDA (Hand Suit)                                           (* hed "2026 revival")
    (* Return the highest card in the given suit, or overall if Suit is NIL. *)
    (Card.MaxCard (if Suit
                      then (Hand.CardsInSuit Hand Suit)
                    else (Hand.Cards Hand])

(Hand.MinCard
  [LAMBDA (Hand Suit)                                           (* hed "2026 revival")
    (Card.MinCard (if Suit
                      then (Hand.CardsInSuit Hand Suit)
                    else (Hand.Cards Hand])

(Card.PrintCard
  [LAMBDA (Card)                                                (* hed "2026 revival")
    (* Print a card as "AS", "2C", "QH" etc. *)
    (CONCAT (SELECTQ (Card.Value Card)
                     ((14) "A")
                     ((13) "K")
                     ((12) "Q")
                     ((11) "J")
                     ((10) "T")
                     (Card.Value Card))
            (SELECTQ (Card.Suit Card)
                     ((QUOTE S) "S")
                     ((QUOTE H) "H")
                     ((QUOTE D) "D")
                     ((QUOTE C) "C")
                     "?"])

(Card.CardsBetween
  [LAMBDA (Card1 Card2)                                         (* hed "2026 revival")
    (* Return list of card values strictly between two cards of the same suit.
       Used by sfol.little.over to see how "little" we're going over. *)
    (if (NOT (EQUAL (Card.Suit Card1) (Card.Suit Card2)))
        then NIL
      else (LET ((lo (Card.Value (if (Card.Lower? Card1 Card2) then Card1 else Card2)))
                 (hi (Card.Value (if (Card.Lower? Card1 Card2) then Card2 else Card1)))
                 (suit (Card.Suit Card1)))
            (for v from (ADD1 lo) to (SUB1 hi) collect (Card.Create v suit])

(CardList.MaxCard
  [LAMBDA (CardList)                                            (* hed "2026 revival")
    (* Alias of Card.MaxCard for a flat list — used by a couple of rules. *)
    (Card.MaxCard CardList])

(CardList.LowerCards
  [LAMBDA (CardList Pivot Suit)                                 (* hed "2026 revival")
    (* Cards in CardList of the given Suit that are strictly lower than Pivot.
       If Suit is NIL, match all suits. *)
    (for Card in CardList collect Card
       when (AND (if Suit then (EQUAL (Card.Suit Card) Suit) else T)
                 (Card.Lower? Card Pivot])

(CardList.HigherCards
  [LAMBDA (CardList Pivot Suit)                                 (* hed "2026 revival")
    (* Cards strictly higher than Pivot (within Suit if given). *)
    (for Card in CardList collect Card
       when (AND (if Suit then (EQUAL (Card.Suit Card) Suit) else T)
                 (Card.Higher? Card Pivot])

(EP.NumberWithPoints
  [LAMBDA (Hist)                                                (* hed "2026 revival")
    (* How many of the four point-buckets have > 0 points so far this deal? *)
    (for Slot in (QUOTE (MyPoints LeftPoints RightPoints AcrossPoints))
       count (GREATERP (EP.GET.VALUE Hist Slot) 0)])

)

;; ============================================================
;; Section 2: Weighted-rule engine
;; ============================================================
(DEFINEQ

(* EP.RuleSystem — a minimal weighted backward-chainer that mirrors KEE RuleSystem2.
   Rules are stored in an alist indexed by rule-class name:
     EP.RuleTable = ((class-name . ((name weight test-fn action-fn) ...)) ...)
   EP.RunRules fires the highest-weight rule whose test succeeds, executes its
   action (which sets a result slot on Self), then returns the result value. *)

(EP.RuleTable
  [LAMBDA NIL                                                   (* hed "2026 revival")
    (* Return the global rule table. Initialized lazily. *)
    (if (NOT (BOUNDP (QUOTE EP.*RuleTable*)))
        then (SETQ EP.*RuleTable* NIL))
    EP.*RuleTable*])

(EP.DefRuleClass
  [LAMBDA (ClassName Rules)                                     (* hed "2026 revival")
    (* Register a named rule class.  Rules is a list of (name weight test action). *)
    (if (NOT (BOUNDP (QUOTE EP.*RuleTable*)))
        then (SETQ EP.*RuleTable* NIL))
    (SETQ EP.*RuleTable*
          (CONS (CONS ClassName (SORT Rules (FUNCTION (LAMBDA (a b) (GREATERP (CADR a) (CADR b))))))
                (REMOVE (FASSOC ClassName EP.*RuleTable*) EP.*RuleTable*)))
    ClassName])

(EP.RunRules
  [LAMBDA (Self ClassName ResultSlot)                           (* hed "2026 revival")
    (* Find the highest-weight rule in ClassName whose test succeeds.
       The test fn receives Self; the action fn receives Self and sets ResultSlot.
       Returns the value placed in ResultSlot, or NIL if no rule fires. *)
    (LET ((entry (FASSOC ClassName (EP.RuleTable)))
          fired)
      (if (NULL entry)
          then NIL
        else (for Rule in (CDR entry)
                do (LET ((test (CADDR Rule))
                         (action (CADDDR Rule)))
                     (if (APPLY test (LIST Self))
                         then (APPLY action (LIST Self))
                              (SETQ fired T)
                              (RETURN NIL))))
             (EP.GET.VALUE Self ResultSlot])

(EP.RunAllRules
  [LAMBDA (Self ClassName ResultSlot)                           (* hed "2026 revival")
    (* Like EP.RunRules but fires ALL rules whose tests pass (for CF accumulation). *)
    (LET ((entry (FASSOC ClassName (EP.RuleTable))))
      (if (NULL entry)
          then NIL
        else (for Rule in (CDR entry)
                do (LET ((test (CADDR Rule))
                         (action (CADDDR Rule)))
                     (if (APPLY test (LIST Self))
                         then (APPLY action (LIST Self)))))
             (EP.GET.VALUE Self ResultSlot])

)

;; ============================================================
;; Section 3: Production rules — translated from kee-expert-rules.txt
;;
;; Convention:
;;   Each rule is (name weight test-lambda action-lambda).
;;   In KEE: (THE Slot OF unit IS ?Var) = (EP.GET.VALUE Self 'Slot)
;;           (THE Slot OF unit IS val)  = (EQUAL val (EP.GET.VALUE Self 'Slot))
;;           DO clause = side-effects after THEN
;; ============================================================

;; ---- trick.evaluation ----
(EP.DefRuleClass (QUOTE trick.evaluation)
  (LIST

   (LIST (QUOTE trick.eval.cant.shoot) 100
     (FUNCTION [LAMBDA (Self)
       (LET ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
             (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick))))
         (AND (EQUAL Strat (QUOTE Shooting))
              Trick
              (GREATERP (Trick.Points Trick) 0)
              (NEQ (Trick.Winner Trick) (EP.GET.VALUE Self (QUOTE PlayerNumber])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Minimizing))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "I can't make it. Damn!")))]))

   (LIST (QUOTE te.right.shooting) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
              (RightOp (EP.GET.VALUE Self (QUOTE RightPlayer)))
              (Cert (EP.CF.Get RightOp (QUOTE Shooting)))
              (Thresh (EP.GET.VALUE (EP.GET.VALUE Self (QUOTE Personality))
                                    (QUOTE TriggerHappiness))))
         (AND (EQUAL Strat (QUOTE Minimizing))
              (GEQ Cert Thresh])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Eclipsing))
       (EP.PUT.VALUE Self (QUOTE Shooter) (EP.GET.VALUE Self (QUOTE RightPlayer)))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "I think the player to my right is shooting.")))]))

   (LIST (QUOTE te.left.shooting) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
              (LeftOp (EP.GET.VALUE Self (QUOTE LeftPlayer)))
              (Cert (EP.CF.Get LeftOp (QUOTE Shooting)))
              (Thresh (EP.GET.VALUE (EP.GET.VALUE Self (QUOTE Personality))
                                    (QUOTE TriggerHappiness))))
         (AND (EQUAL Strat (QUOTE Minimizing))
              (GEQ Cert Thresh])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Eclipsing))
       (EP.PUT.VALUE Self (QUOTE Shooter) (EP.GET.VALUE Self (QUOTE LeftPlayer)))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "I think the player to my left is shooting.")))]))

   (LIST (QUOTE te.across.shooting) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
              (AcrossOp (EP.GET.VALUE Self (QUOTE AcrossPlayer)))
              (Cert (EP.CF.Get AcrossOp (QUOTE Shooting)))
              (Thresh (EP.GET.VALUE (EP.GET.VALUE Self (QUOTE Personality))
                                    (QUOTE TriggerHappiness))))
         (AND (EQUAL Strat (QUOTE Minimizing))
              (GEQ Cert Thresh])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Eclipsing))
       (EP.PUT.VALUE Self (QUOTE Shooter) (EP.GET.VALUE Self (QUOTE AcrossPlayer)))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "I think the player across from me is shooting.")))]))

   (LIST (QUOTE te.go.for.it) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (NWP (EP.NumberWithPoints Hist))
              (MyPts (EP.GET.VALUE Hist (QUOTE MyPoints))))
         (AND (OR (EQUAL Strat (QUOTE Eclipsing)) (EQUAL Strat (QUOTE Minimizing)))
              (OR (AND (EQUAL NWP 1) (GREATERP MyPts 0))
                  (EQUAL NWP 0))
              (EQUAL (LENGTH (EP.SuitsWithCards Self))
                     (LENGTH (EP.WinnerSuits Hist])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Shooting))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "I can shoot!")))]))

   (LIST (QUOTE eclipse.success) 100
     (FUNCTION [LAMBDA (Self)
       (LET ((Strat (EP.GET.VALUE Self (QUOTE Strategy)))
             (Hist (EP.GET.VALUE Self (QUOTE history))))
         (AND (EQUAL Strat (QUOTE Eclipsing))
              (GREATERP (EP.NumberWithPoints Hist) 1])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Minimizing))
       (LET ((HWin (EP.GET.VALUE Self (QUOTE HandWindow))))
         (if HWin then (Open.Print HWin "The shooter has been stopped!")))]))

   (LIST (QUOTE trickeval.keep.strategy) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE Strategy)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy)
                    (EP.GET.VALUE Self (QUOTE Strategy)))]))))

;; ---- passin.evaluation ----
(EP.DefRuleClass (QUOTE passin.evaluation)
  (LIST

   (LIST (QUOTE pi.shoot.test) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Spades (Hand.CardsInSuit Hand (QUOTE S)))
              (Pers (EP.GET.VALUE Self (QUOTE Personality)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (NonWinnerHearts (EP.NonWinners Hist (QUOTE H) NIL)))
         (AND Hand Pers Hist
              (OR (CardList.HighSpades? Spades)
                  (LEQ (LENGTH Spades) (EP.GET.VALUE Pers (QUOTE PIMaxLowSpades))))
              (OR (NULL NonWinnerHearts)
                  (AND (LEQ (LENGTH NonWinnerHearts)
                            (EP.GET.VALUE Pers (QUOTE PIMaxLoserHearts)))
                       (Card.Higher? (Card.MinCard NonWinnerHearts)
                                     (Card.Create (EP.GET.VALUE Pers (QUOTE PILowestHeart))
                                                  (QUOTE H)))))
              (GEQ (CardList.BridgePoints (Hand.FaceCards Hand))
                   (EP.GET.VALUE Pers (QUOTE PIMinShootPoints])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Shooting))]))

   (LIST (QUOTE pi.default.strategy) 0
     (FUNCTION [LAMBDA (Self) T])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE NewStrategy) (QUOTE Minimizing))]))))

;; ---- initial.evaluation ----
(EP.DefRuleClass (QUOTE initial.evaluation)
  (LIST

   (LIST (QUOTE shoot.test) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Spades (Hand.CardsInSuit Hand (QUOTE S)))
              (Pers (EP.GET.VALUE Self (QUOTE Personality)))
              (Hist (EP.GET.VALUE Self (QUOTE history))))
         (AND Hand Pers Hist
              (OR (CardList.HighSpades? Spades)
                  (LEQ (LENGTH Spades) (EP.GET.VALUE Pers (QUOTE POMaxLowSpades))))
              (LEQ (LENGTH (EP.NonWinners Hist (QUOTE H) NIL))
                   (EP.GET.VALUE Pers (QUOTE POMaxLoserHearts)))
              (GEQ (CardList.BridgePoints (Hand.FaceCards Hand))
                   (EP.GET.VALUE Pers (QUOTE POMinShootPoints])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE Strategy) (QUOTE Shooting))]))

   (LIST (QUOTE default.strategy) 0
     (FUNCTION [LAMBDA (Self) T])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE Strategy) (QUOTE Minimizing))]))))

;; ---- opponent.trick.evaluation  (run on each OpponentModel, not on Self directly) ----
(EP.DefRuleClass (QUOTE opponent.trick.evaluation)
  (LIST

   (LIST (QUOTE ote.only.point.taker) 100
     (FUNCTION [LAMBDA (OpSelf)
       (* OpSelf = the opponent model; its MainPlayer is the expert player. *)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (Hist (EP.GET.VALUE Main (QUOTE history)))
              (Trick (EP.GET.VALUE Main (QUOTE CurrentTrick))))
         (AND Main Hist Trick
              (EQUAL (Trick.Winner Trick) (EP.GET.VALUE OpSelf (QUOTE PlayerNum)))
              (GEQ (Trick.Points Trick) 1)
              (EQUAL 1 (EP.NumberWithPoints Hist])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.2)]))

   (LIST (QUOTE ote.no.shooting) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (Hist (EP.GET.VALUE Main (QUOTE history))))
         (AND Main Hist
              (GREATERP (EP.NumberWithPoints Hist) 1])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) -0.99)]))

   (LIST (QUOTE ote.low.on.trick.1) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (CardPlayed (EP.LastCardPlayed OpSelf)))
         (AND Main
              (EQUAL (EP.GET.VALUE Main (QUOTE TrickNumber)) 1)
              CardPlayed
              (Card.NotEqual? CardPlayed (Card.Create 2 (QUOTE C)))
              (Card.Lower? CardPlayed (Card.Create 10 (Card.Suit CardPlayed])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.12)]))

   (LIST (QUOTE ote.dump.non.point) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (Hist (EP.GET.VALUE Main (QUOTE history)))
              (Trick (EP.GET.VALUE Main (QUOTE CurrentTrick)))
              (LastPlayed (EP.LastCardPlayed OpSelf))
              PlayedSuit)
         (AND Main Hist Trick LastPlayed
              (SETQ PlayedSuit (Card.Suit LastPlayed))
              (NEQ (Trick.LeadSuit Trick) PlayedSuit)  (* card was dumped *)
              (NEQ PlayedSuit (QUOTE H))               (* not a point card *)
              (Card.NotEqual? (Card.Create (QUOTE Q) (QUOTE S)) LastPlayed) (* not Maggie *)
              (FMEMB LastPlayed (EP.NonWinners Hist PlayedSuit
                                               (EP.GET.VALUES Hist (QUOTE CardsLeft])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.11)]))))

;; ---- opponent.passin.evaluation ----
(EP.DefRuleClass (QUOTE opponent.passin.evaluation)
  (LIST

   (LIST (QUOTE ope.two.h.pass) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (PassIn (EP.GET.VALUE Main (QUOTE PassInCards)))
              (Hearts (CardList.CardsOfSuit PassIn (QUOTE H))))
         (AND Main PassIn
              (EQUAL (LENGTH Hearts) 2)
              (LESSP (CardList.BridgePoints Hearts) 4])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.2)]))

   (LIST (QUOTE ope.min.is.normal) 100
     (FUNCTION [LAMBDA (OpSelf) T])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Minimizing) 0.3)]))

   (LIST (QUOTE ope.low.pass) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (PassIn (EP.GET.VALUE Main (QUOTE PassInCards)))
              (Pers (EP.GET.VALUE Main (QUOTE Personality))))
         (AND Main PassIn Pers
              (LEQ (CardList.BridgePoints PassIn)
                   (EP.GET.VALUE Pers (QUOTE LowPassPoints])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.3)]))

   (LIST (QUOTE ope.high.pass) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (PassIn (EP.GET.VALUE Main (QUOTE PassInCards)))
              (Pers (EP.GET.VALUE Main (QUOTE Personality))))
         (AND Main PassIn Pers
              (GEQ (CardList.BridgePoints PassIn)
                   (EP.GET.VALUE Pers (QUOTE HiPassPoints])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Minimizing) 0.5)]))

   (LIST (QUOTE ope.all.h.pass) 100
     (FUNCTION [LAMBDA (OpSelf)
       (LET* ((Main (EP.GET.VALUE OpSelf (QUOTE MainPlayer)))
              (PassIn (EP.GET.VALUE Main (QUOTE PassInCards)))
              (Hearts (CardList.CardsOfSuit PassIn (QUOTE H))))
         (AND Main PassIn
              (EQUAL (LENGTH Hearts) 3)
              (LESSP (CardList.BridgePoints Hearts) 4])
     (FUNCTION [LAMBDA (OpSelf)
       (EP.CF.Update OpSelf (QUOTE Shooting) 0.4)]))))

;; ---- lead.play (minimizing) ----
(EP.DefRuleClass (QUOTE lead.play)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE lead.lowest.non.winner) 50
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (EP.NonWinners Hist NIL Legals)))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (EP.NonWinners Hist NIL Legals)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard NW) NIL))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading lowest non-winner."))]))

   (LIST (QUOTE lead.lowest.non.s) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NonSpades (CardList.EliminateSuit Legals (QUOTE S)))
              (NWNS (INTERSECTION NonSpades (EP.NonWinners Hist NIL Legals))))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieLocation)) (QUOTE InHand))
              (Not.Null NWNS)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NonSpades (CardList.EliminateSuit Legals (QUOTE S)))
              (NWNS (INTERSECTION NonSpades (EP.NonWinners Hist NIL Legals))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard NWNS) NWNS))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading lowest non-spade."))]))

   (LIST (QUOTE lead.heart) 60
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Hearts (CardList.CardsOfSuit Legals (QUOTE H)))
              (HLosers (EP.Losers Hist (QUOTE H) NIL)))
         (AND (GEQ (LENGTH Hearts) 1)
              (Not.Null HLosers)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (HLosers (EP.Losers Hist (QUOTE H) NIL)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard HLosers))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading a heart. What the hey."))]))

   (LIST (QUOTE lead.single.diamond) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (TrickN (EP.GET.VALUE Self (QUOTE TrickNumber)))
              (Diamonds (CardList.CardsOfSuit Legals (QUOTE D))))
         (AND (LESSP TrickN 6)
              (EQUAL (LENGTH Diamonds) 1)
              (EP.Equivalent? Hist (CAR Diamonds)
                              (EP.GET.VALUE Hist (QUOTE DiamondWinner)) T)])
     (FUNCTION [LAMBDA (Self)
       (LET ((Diamonds (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE D))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR Diamonds))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading my singleton diamond."))]))

   (LIST (QUOTE lead.single.club) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Pers (EP.GET.VALUE Self (QUOTE Personality)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (TrickN (EP.GET.VALUE Self (QUOTE TrickNumber)))
              (Clubs (CardList.CardsOfSuit Legals (QUOTE C))))
         (AND (LESSP TrickN (EP.GET.VALUE Pers (QUOTE LastSingletonTrick)))
              (EQUAL (LENGTH Clubs) 1)
              (EP.Equivalent? Hist (CAR Clubs)
                              (EP.GET.VALUE Hist (QUOTE ClubWinner)) T)])
     (FUNCTION [LAMBDA (Self)
       (LET ((Clubs (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE C))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR Clubs))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading my singleton club."))]))

   (LIST (QUOTE lead.queen.hunt) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Spades (CardList.CardsOfSuit Legals (QUOTE S)))
              (Mag (CP.Maggie)))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE NotPlayed))
              (Not.Null Spades)
              (Card.Lower? (Card.MaxCard Spades) Mag)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Spades (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE S))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard Spades) NIL))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Looking for the maggie."))]))

   (LIST (QUOTE lead.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading lowest card.")]))))

;; ---- follow.play (minimizing) ----
(EP.DefRuleClass (QUOTE follow.play)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE safe.play.QS) 110
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (LowerCards (CardList.LowerCards Legals
                                              (Card.MaxCard (Trick.Cards Trick) LeadSuit)
                                              LeadSuit))
              (Mag (CP.Maggie)))
         (AND (Not.Null LowerCards)
              (CardList.Member Mag LowerCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CP.Maggie))
       (EP.PUT.VALUE Self (QUOTE LatestReason)
                    "Min - looks like someone's munching the maggie.")]))

   (LIST (QUOTE follow.last.must.win) 110
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (NiceCards (CardList.RemoveCard Legals (CP.Maggie))))
         (AND (EQP (LENGTH (Trick.Cards Trick)) 3)
              (NULL (CardList.LowerCards Legals
                                        (Card.MaxCard (Trick.Cards Trick) LeadSuit)
                                        LeadSuit))
              (Not.Null NiceCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NiceCards (CardList.RemoveCard Legals (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard NiceCards) NiceCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Playing last; must win trick; will play high."))]))

   (LIST (QUOTE follow.last.above.QS) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (Mag (CP.Maggie)))
         (AND (CardList.Member Mag Legals)
              (EQP (LENGTH (Trick.Cards Trick)) 3)
              (Card.Higher? (CardList.MaxCard Legals) Mag)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CardList.MaxCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Playing last; avoiding QS.")]))

   (LIST (QUOTE follow.last.high.safe) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (NiceCards (CardList.RemoveCard Legals (CP.Maggie))))
         (AND (EQP (LENGTH (Trick.Cards Trick)) 3)
              (EQP (Trick.Points Trick) 0)
              (Not.Null NiceCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NiceCards (CardList.RemoveCard Legals (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard NiceCards) NiceCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Playing last; trick is safe; going high."))]))

   (LIST (QUOTE follow.highest.below.QS) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (Mag (CP.Maggie))
              (HLS (CardList.MaxCard (CardList.LowerCards Legals Mag NIL))))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE NotPlayed))
              (EQP (Trick.Points Trick) 0)
              (Not.Null HLS)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (HLS (CardList.MaxCard (CardList.LowerCards Legals (CP.Maggie) NIL))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) HLS)
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Playing below QS on a safe trick."))]))

   (LIST (QUOTE follow.not.QS) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Mag (CP.Maggie)))
         (EQUAL (Card.MinCard Legals) Mag)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Mag (CP.Maggie)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard Legals)
                                            (CardList.RemoveCard Legals Mag)))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Playing something other than the QS."))]))

   (LIST (QUOTE follow.t1.hi.c) 90
     (FUNCTION [LAMBDA (Self)
       (EQUAL (EP.GET.VALUE Self (QUOTE TrickNumber)) 1)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Min - playing high on first trick."))]))

   (LIST (QUOTE third.plays.hi.c.or.d) 65
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick)))
         (AND (EQP (LENGTH (Trick.Cards Trick)) 2)
              (EQUAL 0 (Trick.Points Trick))
              (OR (EQUAL LeadSuit (QUOTE C))
                  (EQUAL LeadSuit (QUOTE D))
                  (AND (EQUAL LeadSuit (QUOTE S))
                       (OR (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE Played))
                           (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE NotPlayed))
                                (Card.Lower? (Card.MaxCard Legals) (CP.Maggie)))))))])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "No harm to play high in third position."))]))

   (LIST (QUOTE follow.lowest.non.s) 60
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NonSpades (CardList.EliminateSuit Legals (QUOTE S)))
              (NWNS (INTERSECTION NonSpades (EP.NonWinners Hist NIL Legals))))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieLocation)) (QUOTE InHand))
              (Not.Null NWNS)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NonSpades (CardList.EliminateSuit Legals (QUOTE S)))
              (NWNS (INTERSECTION NonSpades (EP.NonWinners Hist NIL Legals))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard NWNS) NWNS))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Playing lowest non spade. A silly rule."))]))

   (LIST (QUOTE safe.play) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (LowerCards (CardList.LowerCards Legals
                                              (Card.MaxCard (Trick.Cards Trick) LeadSuit)
                                              LeadSuit)))
         (Not.Null LowerCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (LowerCards (CardList.LowerCards Legals
                                              (Card.MaxCard (Trick.Cards Trick) LeadSuit)
                                              LeadSuit)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (Card.MaxCard LowerCards) LowerCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Normal play - highest under highest played."))]))

   (LIST (QUOTE follow.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Following with lowest card."))]))))

;; ---- dump.play (minimizing) ----
(EP.DefRuleClass (QUOTE dump.play)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE dump.queen) 100
     (FUNCTION [LAMBDA (Self)
       (CardList.Member (CP.Maggie) (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CP.Maggie))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Min - dumping the maggie. Heh, heh.")]))

   (LIST (QUOTE dump.h) 80
     (FUNCTION [LAMBDA (Self)
       (Not.Null (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE H)])
     (FUNCTION [LAMBDA (Self)
       (LET ((Hearts (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE H))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard Hearts))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Min - dumping a heart. Sorry."))]))

   (LIST (QUOTE dump.hi.s) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (HS (CardList.HighSpades? Legals)))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE NotPlayed))
              (Not.Null HS)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (HS (CardList.HighSpades? Legals)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) HS)
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Dumping my highest spade."))]))

   (LIST (QUOTE dump.hi.non.s) 75
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NonSpades (CardList.EliminateSuit Legals (QUOTE S))))
         (AND (EQUAL (EP.GET.VALUE Self (QUOTE MaggieLocation)) (QUOTE InHand))
              (Non.Null NonSpades)])
     (FUNCTION [LAMBDA (Self)
       (LET ((NonSpades (CardList.EliminateSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE S))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard NonSpades))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Min - dumping my highest non-spade."))]))

   (LIST (QUOTE dump.hi.card) 70
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Min - dumping my highest card.")]))))

;; ---- eclipse.lead ----
(EP.DefRuleClass (QUOTE eclipse.lead)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE elead.lead.h) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Hearts (CardList.CardsOfSuit Legals (QUOTE H))))
         (AND Shooter
              (FMEMB (QUOTE H) (EP.GET.VALUES Shooter (QUOTE Voids)))
              (Not.Null Hearts)])
     (FUNCTION [LAMBDA (Self)
       (LET ((Hearts (CardList.CardsOfSuit (EP.GET.VALUE Self (QUOTE LegalCards)) (QUOTE H))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard Hearts))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - leading a low heart; the shooter is void in them."))]))

   (LIST (QUOTE elead.non.shooter.void) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Suits (EP.HeartyNonShooterVoidSuits Self))
              (LeadCards (CardList.CardsOfSuits Legals Suits)))
         (Not.Null LeadCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Suits (EP.HeartyNonShooterVoidSuits Self))
              (LeadCards (CardList.CardsOfSuits Legals Suits)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard LeadCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - leading a card in a non-shooter's void suit."))]))

   (LIST (QUOTE elead.shooter.void) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (SVCards (if Shooter
                           then (CardList.CardsOfSuits Legals
                                                       (EP.GET.VALUES Shooter (QUOTE Voids)))
                         else NIL)))
         (Not.Null SVCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (SVCards (CardList.CardsOfSuits Legals (EP.GET.VALUES Shooter (QUOTE Voids)))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard SVCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - leading a card in the shooter's void suit."))]))

   (LIST (QUOTE elead.lowest.shortest.suit) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Short (CardList.ShortestSuit Legals)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (Card.MinCard (CardList.CardsOfSuit Legals Short)))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - leading a card in my shortest suit."))]))))

;; ---- eclipse.follow ----
(EP.DefRuleClass (QUOTE eclipse.follow)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE efol.dump.queen) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (Mag (CP.Maggie)))
         (AND Shooter
              (Not.Null (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (EQUAL (Trick.LeadSuit Trick) (QUOTE S))
              (CardList.Member Mag Legals)
              (Card.Higher? Mag (Card.MaxCard (Trick.Cards Trick) (QUOTE S))])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CP.Maggie))
       (EP.PUT.VALUE Self (QUOTE LatestReason)
                    "Eclipsing - sacrificing the queen for the glory of mankind.")]))

   (LIST (QUOTE efol.womp.1) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              ShooterPlay HigherCards)
         (AND Shooter
              (GREATERP (Trick.Points Trick) 0)
              (SETQ ShooterPlay (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (Not.Null ShooterPlay)
              (EQUAL (EP.GET.VALUE Shooter (QUOTE PlayerNum)) (Trick.WinnerSoFar Trick))
              (SETQ HigherCards (CardList.HigherCards Legals ShooterPlay LeadSuit))
              (Not.Null HigherCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (ShooterPlay (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (HigherCards (CardList.HigherCards Legals ShooterPlay LeadSuit)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard HigherCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - going to go over the shooter on this trick with points."))]))

   (LIST (QUOTE efol.womp.2) 60
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick)))
         (AND Shooter
              (GREATERP (Trick.Points Trick) 0)
              (NULL (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (FMEMB (Card.MaxCard (CardList.CardsOfSuit (Trick.Cards Trick) LeadSuit))
                     (EP.NonWinners Hist LeadSuit (EP.GET.VALUES Hist (QUOTE CardsLeft))))
              (EP.Equivalent? Hist (EP.GetWinner Hist LeadSuit)
                              (Card.MaxCard Legals LeadSuit))])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard Legals LeadSuit))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - going to take this trick with points."))]))

   (LIST (QUOTE efol.womp.3) 50
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              HighestCard HighestPlayed)
         (AND Shooter
              (GREATERP (Trick.Points Trick) 0)
              (NULL (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (SETQ HighestCard (Card.MaxCard Legals LeadSuit))
              (SETQ HighestPlayed (Card.MaxCard (CardList.CardsOfSuit (Trick.Cards Trick) LeadSuit)))
              (Card.Higher? HighestCard HighestPlayed)
              (EP.Equivalent? Hist HighestCard HighestPlayed T)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard Legals LeadSuit))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - hoping to take this trick with points."))]))

   (LIST (QUOTE efol.low.play) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Eclipsing - playing my lowest card.")]))))

;; ---- eclipse.dump ----
(EP.DefRuleClass (QUOTE eclipse.dump)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE edump.screw.shooter) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (PointCards (CardList.PointCards Legals))
              (Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick))))
         (AND (Not.Null PointCards)
              Shooter
              (Not.Null (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (NEQ (EP.GET.VALUE Shooter (QUOTE PlayerNum)) (Trick.WinnerSoFar Trick))])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (PickCard (if (CardList.Member (CP.Maggie) Legals)
                            then (CP.Maggie)
                          else (Card.MaxCard Legals))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) PickCard)
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - dumping a point card on a non-shooter!"))]))

   (LIST (QUOTE edump.no.points) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (NPNW (LDIFFERENCE (EP.NonWinners Hist NIL Legals)
                                 (CardList.PointCards Legals))))
         (AND Shooter
              (EQUAL (EP.GET.VALUE Shooter (QUOTE PlayerNum)) (Trick.WinnerSoFar Trick))
              (Not.Null NPNW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NPNW (LDIFFERENCE (EP.NonWinners Hist NIL Legals)
                                 (CardList.PointCards Legals))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard NPNW))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - dumping a non-winner on the shooter."))]))

   (LIST (QUOTE edump.hope.to.screw.shooter) 95
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (PointCards (CardList.PointCards Legals))
              (Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick))))
         (AND (Not.Null PointCards)
              Shooter
              (Not.Null (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick))
              (EP.Equivalent? Hist (Trick.PlayOf (EP.GET.VALUE Shooter (QUOTE PlayerNum)) Trick)
                              (EP.GetWinner Hist (Trick.LeadSuit Trick)) T)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (PickCard (if (CardList.Member (CP.Maggie) Legals)
                            then (CP.Maggie)
                          else (Card.MinCard Legals))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) PickCard)
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - hoping a non-shooter wins this one; dumping low point card."))]))

   (LIST (QUOTE edump.shooter.void) 93
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (SVoids (if Shooter
                          then (CardList.CardsOfSuits Legals (EP.GET.VALUES Shooter (QUOTE Voids)))
                        else NIL)))
         (Not.Null SVoids)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Shooter (EP.GET.VALUE Self (QUOTE Shooter)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (SVoids (CardList.CardsOfSuits Legals (EP.GET.VALUES Shooter (QUOTE Voids)))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard SVoids))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - dumping a shooter void card."))]))

   (LIST (QUOTE edump.useless) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (AllCardSuits (EP.AllCardSuits Hist))
              (ACSCards (CardList.CardsOfSuits Legals AllCardSuits)))
         (Not.Null ACSCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (AllCardSuits (EP.AllCardSuits Hist))
              (ACSCards (CardList.CardsOfSuits Legals AllCardSuits)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard ACSCards))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Eclipsing - dumping a useless suit."))]))

   (LIST (QUOTE edump.short.suit.nonwinners) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (EP.NonWinners Hist NIL Legals)))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (EP.NonWinners Hist NIL Legals)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (Card.MinCard (CardList.CardsOfSuit NW (CardList.ShortestSuit NW))))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Eclipsing - dumping a short suit non-winner."))]))

   (LIST (QUOTE edump.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Eclipsing - dumping my lowest card.")]))))

;; ---- shoot.lead ----
(EP.DefRuleClass (QUOTE shoot.lead)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE slead.hearts) 130
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Hearts (CardList.CardsOfSuit Legals (QUOTE H))))
         (AND (EP.WinnerSuit? Hist (QUOTE H))
              (EQUAL (EP.GET.VALUE Self (QUOTE MaggieStatus)) (QUOTE Played))
              (Not.Null Hearts)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.LowestEquivalent Hist (EP.GET.VALUE Hist (QUOTE HeartWinner)) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - leading hearts to clean up this game."))]))

   (LIST (QUOTE slead.non.op.void.loser) 125
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (HVS (EP.HeartyOpponentVoidSuits Self))
              (NW (CardList.EliminateSuits
                    (CardList.RemoveCard
                      (CardList.EliminateSuits (EP.NonWinners Hist NIL Legals) WS)
                      (CP.Maggie))
                    HVS)))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (HVS (EP.HeartyOpponentVoidSuits Self))
              (NW (CardList.EliminateSuits
                    (CardList.RemoveCard
                      (CardList.EliminateSuits (EP.NonWinners Hist NIL Legals) WS)
                      (CP.Maggie))
                    HVS)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard NW))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - leading non-QS non-winner non-opponent void card."))]))

   (LIST (QUOTE slead.lowest.winner.except.QS) 120
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (WSCards (CardList.CardsOfSuits Legals WS))
              (Winners (CardList.RemoveCard (EP.Winners Hist NIL WSCards) (CP.Maggie))))
         (AND (Not.Null WSCards)
              (Not.Null Winners)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (WSCards (CardList.CardsOfSuits Legals WS))
              (Winners (CardList.RemoveCard (EP.Winners Hist NIL WSCards) (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard Winners))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - leading a non-QS winner."))]))

   (LIST (QUOTE slead.loser.except.QS) 110
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (NW (CardList.RemoveCard
                    (CardList.EliminateSuits (EP.NonWinners Hist NIL Legals) WS)
                    (CP.Maggie))))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WS (EP.WinnerSuits Hist))
              (NW (CardList.RemoveCard
                    (CardList.EliminateSuits (EP.NonWinners Hist NIL Legals) WS)
                    (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard NW))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Shooting - leading a non-QS non-winner."))]))

   (LIST (QUOTE lead.lowest.except.QS) 10
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Pick (Card.MinCard (CardList.RemoveCard Legals (CP.Maggie)))))
         (Not.Null Pick)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Pick (Card.MinCard (CardList.RemoveCard Legals (CP.Maggie)))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) Pick)
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading lowest non-QS card."))]))

   (LIST (QUOTE lead.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Leading lowest card.")]))))

;; ---- shoot.follow ----
(EP.DefRuleClass (QUOTE shoot.follow)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE sfol.trick.1.low) 100
     (FUNCTION [LAMBDA (Self)
       (EQUAL (EP.GET.VALUE Self (QUOTE TrickNumber)) 1)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - playing low on first trick."))]))

   (LIST (QUOTE sfol.must.take) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (HCard (EP.HighestEquivalent Hist (Card.MaxCard Legals) Legals)))
         (AND (GREATERP (Trick.Points Trick) 0)
              (Not.Null HCard)
              (Card.Higher? HCard (Card.MaxCard (Trick.Cards Trick)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MaxCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Shooting - must take this one."))]))

   (LIST (QUOTE sfol.little.over) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (WinnerCard (Card.MaxCard (Trick.Cards Trick) LeadSuit))
              (HigherCards (CardList.HigherCards Legals WinnerCard LeadSuit))
              LowestHigh)
         (AND (Not.Null HigherCards)
              (SETQ LowestHigh (Card.MinCard HigherCards))
              (LEQ (LENGTH (Card.CardsBetween LowestHigh WinnerCard)) 4)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Trick (EP.GET.VALUE Self (QUOTE CurrentTrick)))
              (LeadSuit (Trick.LeadSuit Trick))
              (WinnerCard (Card.MaxCard (Trick.Cards Trick) LeadSuit))
              (HigherCards (CardList.HigherCards Legals WinnerCard LeadSuit))
              (LowestHigh (Card.MinCard HigherCards)))
         (EP.PUT.VALUE Self (QUOTE PlayCard) LowestHigh)
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - going a little bit over."))]))

   (LIST (QUOTE sfol.last.dump.loser) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Trick (EP.GET.VALUE Self (QUOTE CurrentTrick))))
         (AND (EQP (LENGTH (Trick.Cards Trick)) 3)
              (EQP (Trick.Points Trick) 0)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - following with loser on last play."))]))

   (LIST (QUOTE follow.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard Legals) Legals))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Following with lowest card."))]))))

;; ---- shoot.dump ----
(EP.DefRuleClass (QUOTE shoot.dump)
  (LIST

   (LIST (QUOTE one.choice) 1000
     (FUNCTION [LAMBDA (Self)
       (EQP (LENGTH (EP.GET.VALUE Self (QUOTE LegalCards))) 1)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (CAR (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "One choice.")]))

   (LIST (QUOTE compute.weak.suit) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (WS (EP.SuitWithFewestWinners Hist (QUOTE (H)))))
         (Not.Null WS)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (WS (EP.SuitWithFewestWinners Hist (QUOTE (H)))))
         (EP.PUT.VALUE Self (QUOTE WeakestSuit) WS))]))

   (LIST (QUOTE dump.weak.suit.loser) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WeakSuit (EP.GET.VALUE Self (QUOTE WeakestSuit)))
              (NW (if WeakSuit then (EP.NonWinners Hist WeakSuit Legals) else NIL)))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (WeakSuit (EP.GET.VALUE Self (QUOTE WeakestSuit)))
              (NW (EP.NonWinners Hist WeakSuit Legals)))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard NW) NW))
         (EP.PUT.VALUE Self (QUOTE LatestReason)
                       "Shooting - dumping a weak suit non-winner."))]))

   (LIST (QUOTE dump.loser) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Losers (CardList.RemoveCard
                        (CardList.EliminateSuit (EP.Losers Hist NIL Legals) (QUOTE H))
                        (CP.Maggie))))
         (Not.Null Losers)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (Losers (CardList.RemoveCard
                        (CardList.EliminateSuit (EP.Losers Hist NIL Legals) (QUOTE H))
                        (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MaxCard Losers))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Shoot - dumping a loser."))]))

   (LIST (QUOTE dump.non.winner) 80
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (CardList.RemoveCard
                    (CardList.EliminateSuit (EP.NonWinners Hist NIL Legals) (QUOTE H))
                    (CP.Maggie))))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (Legals (EP.GET.VALUE Self (QUOTE LegalCards)))
              (NW (CardList.RemoveCard
                    (CardList.EliminateSuit (EP.NonWinners Hist NIL Legals) (QUOTE H))
                    (CP.Maggie))))
         (EP.PUT.VALUE Self (QUOTE PlayCard)
                       (EP.HighestEquivalent Hist (Card.MinCard NW) NW))
         (EP.PUT.VALUE Self (QUOTE LatestReason) "Shooting - dumping a non-winner."))]))

   (LIST (QUOTE sdump.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (EP.GET.VALUE Self (QUOTE LegalCards)])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PlayCard) (Card.MinCard (EP.GET.VALUE Self (QUOTE LegalCards))))
       (EP.PUT.VALUE Self (QUOTE LatestReason) "Shooting - dumping lowest card.")]))))

;; ---- minimizing.passout ----
(EP.DefRuleClass (QUOTE minimizing.passout)
  (LIST

   (LIST (QUOTE pass.hi.s) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (HighestSpade (Hand.MaxCard Hand (QUOTE S))))
         (AND HighestSpade
              (Card.Higher? HighestSpade (Card.Create (QUOTE J) (QUOTE S)))
              (EP.PoorSpadesProtection Self)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (HS (Hand.MaxCard Hand (QUOTE S))))
         (EP.DoPass Self (LIST HS)))]))

   (LIST (QUOTE pass.hi.h) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (HH (Hand.MaxCard Hand (QUOTE H))))
         (AND HH (Card.Higher? HH (Card.Create (QUOTE J) (QUOTE H])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (HH (Hand.MaxCard Hand (QUOTE H))))
         (EP.DoPass Self (LIST HH)))]))

   (LIST (QUOTE two.d) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Diamonds (Hand.CardsInSuit Hand (QUOTE D))))
         (EQUAL (LENGTH Diamonds) 2)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Diamonds (Hand.CardsInSuit Hand (QUOTE D))))
         (EP.DoPass Self (LIST (Card.MaxCard Diamonds))))]))

   (LIST (QUOTE one.d) 70
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Diamonds (Hand.CardsInSuit Hand (QUOTE D))))
         (EQUAL (LENGTH Diamonds) 1)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Diamonds (Hand.CardsInSuit Hand (QUOTE D))))
         (EP.DoPass Self (LIST (CAR Diamonds))))]))

   (LIST (QUOTE short.c) 60
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Clubs (Hand.CardsInSuit Hand (QUOTE C))))
         (AND (Not.Null Clubs)
              (LESSP (LENGTH Clubs) 3)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Clubs (Hand.CardsInSuit Hand (QUOTE C))))
         (EP.DoPass Self Clubs))]))

   (LIST (QUOTE highest.non.s.pick) 50
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MaxCard (CardList.EliminateSuit (Hand.Cards Hand) (QUOTE S)))))
         (Not.Null Pick)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MaxCard (CardList.EliminateSuit (Hand.Cards Hand) (QUOTE S)))))
         (EP.DoPass Self (LIST Pick)))]))

   (LIST (QUOTE s.prot?.1) 10
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pers (EP.GET.VALUE Self (QUOTE Personality))))
         (LESSP (LENGTH (Hand.CardsInSuit Hand (QUOTE S)))
                (EP.GET.VALUE Pers (QUOTE SpadeProtLen])
     (FUNCTION [LAMBDA (Self)
       (EP.PUT.VALUE Self (QUOTE PoorSpadesProtection) T)]))

   (LIST (QUOTE highest.pick) 5
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MaxCard (Hand.Cards Hand))))
         (Not.Null Pick)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MaxCard (Hand.Cards Hand))))
         (EP.DoPass Self (LIST Pick)))]))))

;; ---- shooting.passout ----
(EP.DefRuleClass (QUOTE shooting.passout)
  (LIST

   (LIST (QUOTE pass.all.loser.h) 100
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (NWH (EP.NonWinners Hist (QUOTE H) NIL)))
         (Not.Null NWH)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (NWH (EP.NonWinners Hist (QUOTE H) NIL)))
         (EP.DoPass Self NWH))]))

   (LIST (QUOTE pass.loser.h) 90
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Hist (EP.GET.VALUE Self (QUOTE history)))
              (LoHeart (Hand.MinCard Hand (QUOTE H))))
         (AND LoHeart
              (FMEMB LoHeart (EP.NonWinners Hist (QUOTE H) NIL])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (LoHeart (Hand.MinCard Hand (QUOTE H))))
         (EP.DoPass Self (LIST LoHeart)))]))

   (LIST (QUOTE pass.lowest.non.s) 20
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MinCard (CardList.EliminateSuit (Hand.Cards Hand) (QUOTE S)))))
         (Not.Null Pick)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MinCard (CardList.EliminateSuit (Hand.Cards Hand) (QUOTE S)))))
         (EP.DoPass Self (LIST Pick)))]))

   (LIST (QUOTE pass.any.non.winner) 10
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (NW (APPEND (EP.NonWinners Hist (QUOTE D) NIL)
                          (EP.NonWinners Hist (QUOTE C) NIL))))
         (Not.Null NW)])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hist (EP.GET.VALUE Self (QUOTE history)))
              (NW (APPEND (EP.NonWinners Hist (QUOTE D) NIL)
                          (EP.NonWinners Hist (QUOTE C) NIL))))
         (EP.DoPass Self (LIST (Card.MinCard NW))))]))

   (LIST (QUOTE pass.lowest) 0
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand))))
         (Not.Null (Hand.Cards Hand])
     (FUNCTION [LAMBDA (Self)
       (LET* ((Hand (EP.GET.VALUE Self (QUOTE Hand)))
              (Pick (Card.MinCard (Hand.Cards Hand))))
         (EP.DoPass Self (LIST Pick)))]))))

;; helper used by s.prot?.1 action
(DEFINEQ
(EP.PoorSpadesProtection
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (EP.GET.VALUE Self (QUOTE PoorSpadesProtection])
)
