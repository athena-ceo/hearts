;; -*- Mode: Lisp; Package: Interlisp -*-
;; EP-GLUE.LISP  —  HEARTS Expert Player, message-handler glue layer
;;
;; This file provides:
;;   1. The full EP.* function set from kee-expert-player.txt, re-expressed to use
;;      the LOOPS object layer (ep-loops.lisp) and the rule engine (ep-rules.lisp)
;;      instead of KEE UNITMSG / QUERY / GET.VALUE / PUT.VALUE.
;;
;;   2. History helper methods: EP.Init, EP.ComputeStats, EP.ComputeWinnersAndLosers,
;;      EP.NonWinners, EP.Winners, EP.Losers, EP.HighestEquivalent, EP.LowestEquivalent,
;;      EP.Equivalent?, EP.EquivalentCards, EP.WinnerSuit?, EP.WinnerSuits,
;;      EP.FewestWinners, EP.SuitsWithCards, EP.SuitWithFewestWinners, EP.AllCardSuits,
;;      EP.GetWinner, EP.GetLoser, EP.LastCardPlayed, EP.NumberWithPoints,
;;      EP.HeartyNonShooterVoidSuits, EP.HeartyOpponentVoidSuits.
;;
;;   3. The six top-level H.Apply message handlers that the core dispatches to:
;;        GiveHand → EP.GiveHand
;;        PassOut  → EP.PassOut   (calls rule engine for pass card selection)
;;        PassIn   → EP.PassIn
;;        Play     → EP.Play      (calls rule engine for card selection)
;;        Trick    → EP.Trick     (updates history + opponent models + re-evaluates strategy)
;;        Results  → EP.Results
;;
;;   4. EP.Create  — creates a complete Player record for use by H.MakePlayer.
;;      EP.DoPass  — the pass accumulator called by pass-out rules.
;;      EP.OpInit  — resets an opponent model for a new hand.
;;      EP.UpdateModel — updates one opponent model after a trick.
;;
;;   5. KillExperts — tear-down utility.
;;
;;   6. EPMapping  — the Lisp-type dispatch table so the Expert runs via the Lisp path
;;      in H.Apply (Type=Lisp) — *NOT* via the Kee path — since KEE is unavailable.
;;      This is the key architectural change vs. the original: the original used
;;      Type=Kee and UNITMSG*; we use Type=Lisp and a function alist identical in
;;      shape to CP/CLOWN/HP mapping tables.
;;
;; Written for the HEARTS revival (github.com/athena-ceo/hearts).
;; Phase 2b — KEE Expert Player reimplementation.
;; Author: Claude Code (Anthropic), with Harley Davis, 2026.

;; ============================================================
;; Section 1: History helpers
;; (These were the message handlers on the KEE history unit.)
;; ============================================================
(DEFINEQ

(EP.Init
  [LAMBDA (self)                                                (* hed "2026 revival")
    (* Initialize the history unit for a new hand.
       self = EP.HistoryClass instance. *)
    (for Slot in (QUOTE (CardsLeft CardsPlayed SpadesLeft HeartsLeft DiamondsLeft ClubsLeft
                                SpadesPlayed HeartsPlayed DiamondsPlayed ClubsPlayed Reasons))
       do (EP.REMOVE.ALL.LOCAL.VALUES self Slot))
    (LET [(Cards (for v in CardValues join (for s in SuitValues collect (Card.Create v s))))]
      (EP.PUT.VALUE self (QUOTE CardsLeft) Cards)
      (EP.PUT.VALUE self (QUOTE SpadesLeft)   (CardList.CardsOfSuit Cards (QUOTE S)))
      (EP.PUT.VALUE self (QUOTE HeartsLeft)   (CardList.CardsOfSuit Cards (QUOTE H)))
      (EP.PUT.VALUE self (QUOTE DiamondsLeft) (CardList.CardsOfSuit Cards (QUOTE D)))
      (EP.PUT.VALUE self (QUOTE ClubsLeft)    (CardList.CardsOfSuit Cards (QUOTE C)))
      (EP.PUT.VALUE self (QUOTE MyTotalPoints)
                   (PLUS (EP.GET.VALUE self (QUOTE MyTotalPoints))
                         (EP.GET.VALUE self (QUOTE MyPoints))))
      (EP.PUT.VALUE self (QUOTE LeftTotalPoints)
                   (PLUS (EP.GET.VALUE self (QUOTE LeftTotalPoints))
                         (EP.GET.VALUE self (QUOTE LeftPoints))))
      (EP.PUT.VALUE self (QUOTE RightTotalPoints)
                   (PLUS (EP.GET.VALUE self (QUOTE RightTotalPoints))
                         (EP.GET.VALUE self (QUOTE RightPoints))))
      (EP.PUT.VALUE self (QUOTE AcrossTotalPoints)
                   (PLUS (EP.GET.VALUE self (QUOTE AcrossTotalPoints))
                         (EP.GET.VALUE self (QUOTE AcrossPoints))))
      (EP.ComputeWinnersAndLosers self)])

(EP.ComputeWinnersAndLosers
  [LAMBDA (self)                                                (* hed "2026 revival")
    (* Recompute the current highest (winner) and lowest (loser) card
       remaining in each suit.  self = EP.HistoryClass instance. *)
    (for LeftSlot in (QUOTE (SpadesLeft HeartsLeft DiamondsLeft ClubsLeft))
       as WinnerSlot in (QUOTE (SpadeWinner HeartWinner DiamondWinner ClubWinner))
       as LoserSlot in (QUOTE (SpadeLoser HeartLoser DiamondLoser ClubLoser))
       do (LET ((CardsLeft (EP.GET.VALUES self LeftSlot)))
            (EP.PUT.VALUE self WinnerSlot (Card.MaxCard CardsLeft))
            (EP.PUT.VALUE self LoserSlot  (Card.MinCard CardsLeft)])

(EP.ComputeStats
  [LAMBDA (self Trick)                                          (* hed "2026 revival")
    (* After a trick is resolved: remove played cards from history,
       update per-position point tallies.  self = EP.HistoryClass instance. *)
    (LET ((Player (EP.GET.VALUE self (QUOTE Player)))
          (WinnerNum (fetch Winner of Trick))
          PlayerNum WinnerSlot)
      (SETQ PlayerNum (EP.GET.VALUE Player (QUOTE MyNumber)))
      (for Card in (Trick.Cards Trick)
         do (EP.REMOVE.VALUE self (QUOTE CardsLeft) Card)
            (EP.REMOVE.VALUE self (SELECTQ (Card.Suit Card)
                                            ((QUOTE S) (QUOTE SpadesLeft))
                                            ((QUOTE H) (QUOTE HeartsLeft))
                                            ((QUOTE D) (QUOTE DiamondsLeft))
                                            ((QUOTE C) (QUOTE ClubsLeft))
                                            NIL)
                             Card)
            (EP.ADD.VALUE self (QUOTE CardsPlayed) Card)
            (EP.ADD.VALUE self (SELECTQ (Card.Suit Card)
                                         ((QUOTE S) (QUOTE SpadesPlayed))
                                         ((QUOTE H) (QUOTE HeartsPlayed))
                                         ((QUOTE D) (QUOTE DiamondsPlayed))
                                         ((QUOTE C) (QUOTE ClubsPlayed))
                                         NIL)
                           Card))
      (EP.ComputeWinnersAndLosers self)
      (SETQ WinnerSlot (SELECTQ (PlayerLoc PlayerNum WinnerNum)
                                 ((QUOTE Left)   (QUOTE LeftPoints))
                                 ((QUOTE Right)  (QUOTE RightPoints))
                                 ((QUOTE Across) (QUOTE AcrossPoints))
                                 (QUOTE MyPoints)))
      (EP.PUT.VALUE self WinnerSlot
                   (PLUS (Trick.Points Trick) (EP.GET.VALUE self WinnerSlot)))
      (if (NEQ WinnerNum PlayerNum)
          then (LET ((OpUnit (EP.GetOpponent Player WinnerNum)))
                 (if OpUnit
                     then (EP.PUT.VALUE OpUnit (QUOTE Points)
                                        (EP.GET.VALUE self WinnerSlot)])

(EP.Equivalent?
  [LAMBDA (self Card1 Card2 Not?)                               (* hed "2026 revival")
    (* True if Card1 and Card2 are "equivalent" — all cards between them have
       been played or are in the owner's hand.  Not? inverts.
       self = EP.HistoryClass instance. *)
    (if (NOT (EQUAL (Card.Suit Card1) (Card.Suit Card2)))
        then NIL
      else (LET* ((suit (Card.Suit Card1))
                  (PlayedCards (CardList.CardsOfSuit (EP.GET.VALUES self (QUOTE CardsPlayed)) suit))
                  (HandCards (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player))
                                                              (QUOTE Hand))
                                               suit)))
             (if (Card.Higher? Card1 Card2)
                 then (LET ((tmp Card1)) (SETQ Card1 Card2) (SETQ Card2 tmp)))
             (if Not?
                 then (for val in (Card.ValueSublist (Card.Value Card1) (Card.Value Card2))
                          thereis (LET ((tc (Card.Create val suit)))
                                    (NOT (OR (FMEMB tc PlayedCards) (FMEMB tc HandCards)))))
               else (for val in (Card.ValueSublist (Card.Value Card1) (Card.Value Card2))
                        always (LET ((tc (Card.Create val suit)))
                                 (OR (FMEMB tc PlayedCards) (FMEMB tc HandCards)])

(EP.EquivalentCards
  [LAMBDA (Self Card LimitingCards)                             (* hed "2026 revival")
    (* Return all cards from LimitingCards (or from the player's hand in Card's suit)
       that are equivalent to Card.  self = EP.HistoryClass instance. *)
    (for c in (OR LimitingCards
                  (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE Self (QUOTE Player)) (QUOTE Hand))
                                    (Card.Suit Card)))
       collect c when (EP.Equivalent? Self Card c)])

(EP.HighestEquivalent
  [LAMBDA (Self Card LimitingCards)                             (* hed "2026 revival")
    (Card.MaxCard (EP.EquivalentCards Self Card LimitingCards)])

(EP.LowestEquivalent
  [LAMBDA (Self Card LimitingCards)                             (* hed "2026 revival")
    (Card.MinCard (EP.EquivalentCards Self Card LimitingCards])

(EP.NonWinners
  [LAMBDA (self suit cardlist)                                  (* hed "2026 revival")
    (* Cards in cardlist (or hand) that are NOT equivalent to the current winner
       of the given suit.  self = EP.HistoryClass. *)
    (if suit
        then (for card in (if cardlist
                              then (CardList.CardsOfSuit cardlist suit)
                            else (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player))
                                                                  (QUOTE Hand))
                                                   suit))
                 collect card unless (EP.Equivalent? self card (EP.GetWinner self suit)))
      else (for card in (OR cardlist
                            (Hand.Cards (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player)) (QUOTE Hand))))
               collect card unless (EP.Equivalent? self card
                                                   (EP.GetWinner self (Card.Suit card])

(EP.Winners
  [LAMBDA (self suit cardlist)                                  (* hed "2026 revival")
    (* Cards equivalent to the current suit winner. *)
    (if suit
        then (for card in (if cardlist
                              then (CardList.CardsOfSuit cardlist suit)
                            else (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player))
                                                                  (QUOTE Hand))
                                                   suit))
                 collect card when (EP.Equivalent? self card (EP.GetWinner self suit)))
      else (for card in (OR cardlist
                            (Hand.Cards (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player)) (QUOTE Hand))))
               collect card when (EP.Equivalent? self card
                                                  (EP.GetWinner self (Card.Suit card])

(EP.Losers
  [LAMBDA (self suit cardlist)                                  (* hed "2026 revival")
    (* Cards equivalent to the current suit loser. *)
    (if suit
        then (for card in (if cardlist
                              then (CardList.CardsOfSuit cardlist suit)
                            else (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player))
                                                                  (QUOTE Hand))
                                                   suit))
                 collect card when (EP.Equivalent? self card (EP.GetLoser self suit)))
      else (for card in (OR cardlist
                            (Hand.Cards (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player)) (QUOTE Hand))))
               collect card when (EP.Equivalent? self card
                                                   (EP.GetLoser self (Card.Suit card])

(EP.GetWinner
  [LAMBDA (self suit)                                           (* hed "2026 revival")
    (EP.GET.VALUE self (SELECTQ suit
                                 ((QUOTE S) (QUOTE SpadeWinner))
                                 ((QUOTE H) (QUOTE HeartWinner))
                                 ((QUOTE D) (QUOTE DiamondWinner))
                                 ((QUOTE C) (QUOTE ClubWinner))
                                 NIL])

(EP.GetLoser
  [LAMBDA (self suit)                                           (* hed "2026 revival")
    (EP.GET.VALUE self (SELECTQ suit
                                 ((QUOTE S) (QUOTE SpadeLoser))
                                 ((QUOTE H) (QUOTE HeartLoser))
                                 ((QUOTE D) (QUOTE DiamondLoser))
                                 ((QUOTE C) (QUOTE ClubLoser))
                                 NIL])

(EP.WinnerSuit?
  [LAMBDA (self suit)                                           (* hed "2026 revival")
    (* Is the given suit a "winner suit" — one where we hold the highest
       remaining card or more winners than non-hand losers? *)
    (LET ((Winners (EP.Winners self suit NIL))
          (CardsLeft (CardList.CardsOfSuit (EP.GET.VALUES self (QUOTE CardsLeft)) suit))
          (HandCards (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player)) (QUOTE Hand))
                                       suit)))
      (OR (EQP 0 (LENGTH (EP.NonWinners self suit NIL)))
          (GREATERP (LENGTH Winners)
                    (LENGTH (LDIFFERENCE CardsLeft HandCards])

(EP.WinnerSuits
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (* All suits where we hold the current winner equivalent. *)
    (for suit in SuitValues collect suit when (EP.WinnerSuit? Self suit)])

(EP.FewestWinners
  [LAMBDA (Self ExcludedSuits)                                  (* hed "2026 revival")
    (* Suit (not in ExcludedSuits) with the fewest winner-equivalent cards in hand. *)
    (LET ((best NIL) (bestN 999))
      (for suit in SuitValues
         unless (FMEMB suit ExcludedSuits)
         do (LET ((n (LENGTH (EP.EquivalentCards Self (EP.GetWinner Self suit) NIL))))
              (if (LESSP n bestN)
                  then (SETQ best suit) (SETQ bestN n))))
      best])

(EP.SuitWithFewestWinners
  [LAMBDA (Self ExcludedSuits)                                  (* hed "2026 revival")
    (* Return the suit (not in ExcludedSuits) with the fewest winner-class cards
       in the player's hand. Used by compute.weak.suit in shoot.dump. *)
    (EP.FewestWinners (EP.GET.VALUE Self (QUOTE history)) ExcludedSuits])

(EP.SuitsWithCards
  [LAMBDA (self)                                                (* hed "2026 revival")
    (* Suits in which the player's hand has at least one card.
       self = EP.PlayerClass instance. *)
    (LET [(Hand (EP.GET.VALUE self (QUOTE Hand)))]
      (for suit in SuitValues collect suit when (Not.Null (Hand.CardsInSuit Hand suit])

(EP.AllCardSuits
  [LAMBDA (Hist)                                                (* hed "2026 revival")
    (* Suits where all remaining cards are in someone's hand (no unseen cards).
       Used by edump.useless.  Hist = EP.HistoryClass instance. *)
    (for suit in SuitValues collect suit
       when (NULL (LDIFFERENCE (CardList.CardsOfSuit (EP.GET.VALUES Hist (QUOTE CardsLeft)) suit)
                               (Hand.CardsInSuit (EP.GET.VALUE (EP.GET.VALUE Hist (QUOTE Player))
                                                                (QUOTE Hand))
                                                 suit])

(EP.LastCardPlayed
  [LAMBDA (self)                                                (* hed "2026 revival")
    (* self = EP.OpponentModelClass: last card this opponent played. *)
    (CAR (EP.GET.VALUES self (QUOTE PlayedCards])

(EP.NumberWithPoints
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (* How many of the four positions have taken > 0 points this deal.
       Self = EP.HistoryClass instance. *)
    (for Slot in (QUOTE (MyPoints LeftPoints RightPoints AcrossPoints))
       count (GREATERP (EP.GET.VALUE Self Slot) 0])

(EP.HeartyNonShooterVoidSuits
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (* Suits that non-shooters with hearts are void in.  Self = EP.PlayerClass. *)
    (LET ((Voids NIL))
      (for op in (LIST (EP.GET.VALUE Self (QUOTE LeftPlayer))
                       (EP.GET.VALUE Self (QUOTE RightPlayer))
                       (EP.GET.VALUE Self (QUOTE AcrossPlayer)))
         do (SETQ Voids (UNION Voids (EP.GET.VALUES op (QUOTE Voids))))
            unless (OR (EQUAL op (EP.GET.VALUE Self (QUOTE Shooter)))
                       (FMEMB (QUOTE H) (EP.GET.VALUES op (QUOTE Voids)))))
      Voids])

(EP.HeartyOpponentVoidSuits
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (* All suits that opponents who still have hearts are void in.
       Self = EP.PlayerClass. *)
    (LET ((Voids NIL))
      (for op in (LIST (EP.GET.VALUE Self (QUOTE LeftPlayer))
                       (EP.GET.VALUE Self (QUOTE RightPlayer))
                       (EP.GET.VALUE Self (QUOTE AcrossPlayer)))
         do (SETQ Voids (UNION Voids (EP.GET.VALUES op (QUOTE Voids))))
            unless (FMEMB (QUOTE H) (EP.GET.VALUES op (QUOTE Voids))))
      Voids])

)

;; ============================================================
;; Section 2: Opponent model helpers
;; ============================================================
(DEFINEQ

(EP.OpInit
  [LAMBDA (Self)                                                (* hed "2026 revival")
    (* Reset an opponent model for a new hand.  Self = EP.OpponentModelClass. *)
    (for Slot in (QUOTE (HandCards PlayedCards Strategy TricksWon Voids))
       do (EP.REMOVE.ALL.LOCAL.VALUES Self Slot))
    (EP.PUT.VALUE Self (QUOTE Points) 0)
    (EP.CF.Reset Self)])

(EP.GetOpponent
  [LAMBDA (Self NumOrLoc)                                       (* hed "2026 revival")
    (* Self = EP.PlayerClass.  NumOrLoc = player-number integer or location symbol. *)
    (if (NUMBERP NumOrLoc)
        then (SETQ NumOrLoc (PlayerLoc (EP.GET.VALUE Self (QUOTE PlayerNumber)) NumOrLoc)))
    (if NumOrLoc
        then (EP.GET.VALUE Self (SELECTQ NumOrLoc
                                          ((QUOTE Left)   (QUOTE LeftPlayer))
                                          ((QUOTE Right)  (QUOTE RightPlayer))
                                          ((QUOTE Across) (QUOTE AcrossPlayer))
                                          NIL])

(EP.UpdateModel
  [LAMBDA (Self Trick)                                          (* hed "2026 revival")
    (* Update one opponent model after a trick.  Self = EP.OpponentModelClass.
       Called for each of Left/Right/Across by EP.Trick. *)
    (LET* ((MyNumber (EP.GET.VALUE Self (QUOTE PlayerNum)))
           (OwnerNumber (EP.GET.VALUE (EP.GET.VALUE Self (QUOTE MainPlayer)) (QUOTE PlayerNumber)))
           (Winner (Trick.Winner Trick))
           (LeadSuit (Card.Suit (CAR (Trick.Cards Trick))))
           MyCard)
      (if (EQP MyNumber Winner)
          then (EP.ADD.VALUE Self (QUOTE TricksWon) Trick))
      (EP.ADD.VALUE Self (QUOTE PlayedCards)
                   (SETQ MyCard (Trick.PlayOf MyNumber Trick)))
      (if (AND MyCard (NOT (EQUAL LeadSuit (Card.Suit MyCard))))
          then (EP.REPLACE.VALUE Self (QUOTE Voids) LeadSuit LeadSuit))
      (* Run the opponent strategy CF rules *)
      (EP.RunAllRules Self (QUOTE opponent.trick.evaluation) (QUOTE CF.alist)])

)

;; ============================================================
;; Section 3: Pass accumulator (called from pass-out rules)
;; ============================================================
(DEFINEQ

(EP.DoPass
  [LAMBDA (Self PCards)                                         (* hed "2026 revival")
    (* Add PCards to the pass-card list, respecting the 3-card limit.
       Returns new NumberOfPassCards if successful, NIL if limit exceeded.
       Self = EP.PlayerClass. *)
    (LET* ((CurrentPassCards (EP.GET.VALUES Self (QUOTE PassCards)))
           (NewNPC (PLUS (FLENGTH PCards) (EP.GET.VALUE Self (QUOTE NumberOfPassCards))))
           (PCards (for PC in PCards collect PC unless (FMEMB PC CurrentPassCards))))
      (if (OR (NULL PCards) (GREATERP NewNPC 3))
          then NIL
        else (EP.ADD.VALUES Self (QUOTE PassCards) PCards)
             (Hand.RemoveCards (EP.GET.VALUE Self (QUOTE Hand)) PCards)
             (EP.PUT.VALUE Self (QUOTE NumberOfPassCards) NewNPC)
             NewNPC])

)

;; ============================================================
;; Section 4: The six H.Apply message handlers
;; ============================================================
(DEFINEQ

(EP.GiveHand
  [LAMBDA (self Hand MyNumber)                                  (* hed "2026 revival")
    (* GiveHand message: store 13-card hand, initialize history + opponent models,
       note Maggie location.  self = EP.PlayerClass instance. *)
    (LET [(HWin (EP.GET.VALUE self (QUOTE HandWindow)))]
      (EP.PUT.VALUE self (QUOTE Hand) Hand)
      (EP.PUT.VALUE self (QUOTE MaggieStatus) (QUOTE NotPlayed))
      (EP.PUT.VALUE self (QUOTE TrickNumber) 0)
      (EP.PUT.VALUE self (QUOTE MyNumber) MyNumber)
      (EP.PUT.VALUE self (QUOTE PlayerNumber) MyNumber)
      (EP.Init (EP.GET.VALUE self (QUOTE history)))
      (if (CardList.Member (CP.Maggie) (Hand.CardsInSuit Hand (QUOTE S)))
          then (EP.PUT.VALUE self (QUOTE MaggieLocation) (QUOTE InHand))
        else (EP.PUT.VALUE self (QUOTE MaggieLocation) (QUOTE Elsewhere)))
      (if HWin
          then (Open.RemakeWindow HWin Hand)
               (CLEARW (GETPROMPTWINDOW HWin)))
      (for dir in (QUOTE (Left Right Across))
         as OpSlot in (QUOTE (LeftPlayer RightPlayer AcrossPlayer))
         do (LET ((Op (EP.GET.VALUE self OpSlot)))
              (EP.OpInit Op)
              (EP.PUT.VALUE Op (QUOTE PlayerNum)
                            (PlayerNum MyNumber dir])

(EP.PassOut
  [LAMBDA (self PassDir)                                        (* hed "2026 revival")
    (* PassOut message: choose 3 cards to pass in direction PassDir.
       Uses the rule engine — strategy determines which passout rule class to run. *)
    (LET ((Hand (EP.GET.VALUE self (QUOTE Hand)))
          (HWin (EP.GET.VALUE self (QUOTE HandWindow)))
          PassCards)
      (* Set up context for rules *)
      (EP.PUT.VALUE self (QUOTE NumberOfPassCards) 0)
      (EP.PUT.VALUE self (QUOTE PassDir) PassDir)
      (EP.REMOVE.ALL.LOCAL.VALUES self (QUOTE PassCards))
      (EP.PUT.VALUE self (QUOTE PoorSpadesProtection) NIL)

      (* Pre-pass strategy determination *)
      (EP.REMOVE.ALL.LOCAL.VALUES self (QUOTE Strategy))
      (EP.RunRules self (QUOTE initial.evaluation) (QUOTE Strategy))
      (if HWin
          then (Open.Print HWin (CONCAT "My strategy is "
                                        (EP.GET.VALUE self (QUOTE Strategy)))))

      (* Choose pass cards according to strategy *)
      (if PassDir
          then (LET* ((StratSym (EP.GET.VALUE self (QUOTE Strategy)))
                      (RuleClass (if (EQUAL StratSym (QUOTE Shooting))
                                     then (QUOTE shooting.passout)
                                   else (QUOTE minimizing.passout))))
                 (EP.PUT.VALUE self (QUOTE PassOutRuleClass) RuleClass)
                 (* Run the passout rules until we have 3 cards *)
                 (EP.RunPassOutLoop self RuleClass)
                 (SETQ PassCards (EP.GET.VALUES self (QUOTE PassCards)))
                 (* Inform opponent model of outgoing cards *)
                 (LET ((DestOp (EP.GetOpponent self PassDir)))
                   (if DestOp
                       then (EP.ADD.VALUES DestOp (QUOTE HandCards) PassCards)))
                 (if HWin
                     then (Open.Print HWin "Passing: " T)
                          (for card in PassCards do (Open.Print HWin (CONCAT (Card.PrintCard card) " ") T))
                          (Open.Print HWin " ")
                          (Open.RemakeWindow HWin Hand))))
      PassCards])

(EP.RunPassOutLoop
  [LAMBDA (Self RuleClass)                                      (* hed "2026 revival")
    (* Run pass-out rules in a loop until 3 cards have been selected.
       Mirrors the KEE (do (QUERY ...) repeatuntil 3) loop. *)
    (LET ((MaxIter 10)
          (Iter 0))
      (WHILE (AND (LESSP (EP.GET.VALUE Self (QUOTE NumberOfPassCards)) 3)
                  (LESSP (SETQ Iter (ADD1 Iter)) MaxIter))
        do (EP.RunRules Self RuleClass (QUOTE PassCards)))])

(EP.PassIn
  [LAMBDA (self PassIn)                                         (* hed "2026 revival")
    (* PassIn message: receive 3 cards from the passer; update hand and
       model the passer's strategy. *)
    (LET [(Hand (EP.GET.VALUE self (QUOTE Hand)))
          (HWin (EP.GET.VALUE self (QUOTE HandWindow)))]
      (* Book-keeping *)
      (EP.PUT.VALUE self (QUOTE PassInCards) PassIn)
      (EP.PUT.VALUE self (QUOTE PassInFrom)
                   (EP.GetOpponent self
                                   (SELECTQ (EP.GET.VALUE self (QUOTE PassDir))
                                             ((QUOTE Left)   (QUOTE Right))
                                             ((QUOTE Across) (QUOTE Across))
                                             ((QUOTE Right)  (QUOTE Left))
                                             NIL)))
      (* Add cards to hand *)
      (for Card in PassIn do (Hand.AddCard Hand Card))
      (* Track Maggie location *)
      (if (CardList.Member (CP.Maggie) (Hand.CardsInSuit Hand (QUOTE S)))
          then (EP.PUT.VALUE self (QUOTE MaggieLocation) (QUOTE InHand))
        else (EP.PUT.VALUE self (QUOTE MaggieLocation) (QUOTE Elsewhere)))
      (if HWin
          then (Open.RemakeWindow HWin Hand)
               (Open.Print HWin (CONCAT "Receiving: "
                                        (for pi in PassIn collect (Card.PrintCard pi)))))
      (* Model the passer's strategy based on what they passed *)
      (LET ((PassFromOp (EP.GET.VALUE self (QUOTE PassInFrom))))
        (if PassFromOp
            then (EP.RunAllRules PassFromOp (QUOTE opponent.passin.evaluation) (QUOTE CF.alist))))
      (* Re-evaluate own strategy after receiving pass *)
      (EP.REMOVE.ALL.LOCAL.VALUES self (QUOTE NewStrategy))
      (EP.RunRules self (QUOTE passin.evaluation) (QUOTE NewStrategy))
      (EP.PUT.VALUE self (QUOTE Strategy) (EP.GET.VALUE self (QUOTE NewStrategy)))
      (if HWin
          then (Open.Print HWin (CONCAT "New strategy is: " (EP.GET.VALUE self (QUOTE NewStrategy)))))
      ])

(EP.Play
  [LAMBDA (self Trick HeartsBroken? FirstTrick?)                (* hed "2026 revival")
    (* Play message: choose and return one legal card.
       Sets up context slots, dispatches to strategy-specific rule class,
       removes the card from hand, logs the reason, returns the card. *)
    (LET ((Hand (EP.GET.VALUE self (QUOTE Hand)))
          (LeadCard (CAR (Trick.Cards Trick)))
          (HWin (EP.GET.VALUE self (QUOTE HandWindow)))
          Legals PlayCard PlayMode LatestReason)
      (* Set current-player context for rules *)
      (EP.REMOVE.ALL.LOCAL.VALUES self (QUOTE PlayCard))
      (SETQ Legals (H.GetLegals Hand Trick HeartsBroken? FirstTrick?))
      (EP.PUT.VALUE self (QUOTE LegalCards) Legals)
      (EP.PUT.VALUE self (QUOTE PlayMode)
                   (SETQ PlayMode (if LeadCard
                                      then (if (EQUAL (Card.Suit LeadCard)
                                                      (Card.Suit (CAR Legals)))
                                               then (QUOTE FollowSuit)
                                             else (QUOTE Dump))
                                    else (QUOTE Lead))))
      (EP.PUT.VALUE self (QUOTE CurrentTrick) Trick)
      (EP.PUT.VALUE self (QUOTE TrickNumber) (ADD1 (EP.GET.VALUE self (QUOTE TrickNumber))))
      (* Dispatch to correct strategy + mode rule class *)
      (LET* ((StratSym (EP.GET.VALUE self (QUOTE Strategy)))
             (RuleClass (EP.PlayRuleClass StratSym PlayMode)))
        (if StratSym
            then (EP.RunRules self RuleClass (QUOTE PlayCard))
          else (EP.RunRules self (QUOTE lead.play) (QUOTE PlayCard))))
      (* Retrieve result *)
      (SETQ PlayCard (EP.GET.VALUE self (QUOTE PlayCard)))
      (SETQ LatestReason (EP.GET.VALUE self (QUOTE LatestReason)))
      (* Remove from hand *)
      (Hand.RemoveCard Hand PlayCard)
      (* Display *)
      (if HWin
          then (if FirstTrick? then (Open.Print HWin "Playing : " T))
               (Open.Print HWin (CONCAT (SELECTQ PlayMode
                                             ((QUOTE FollowSuit) "f")
                                             ((QUOTE Dump) "d")
                                             ((QUOTE Lead) "l")
                                             NIL)
                                        (Card.PrintCard PlayCard)
                                        " " LatestReason)
                            T)
               (Open.RemakeWindow HWin Hand))
      (* Log reason *)
      (EP.ADD.VALUE (EP.GET.VALUE self (QUOTE history)) (QUOTE Reasons)
                   (LIST (Card.PrintCard PlayCard) LatestReason))
      PlayCard])

(EP.PlayRuleClass
  [LAMBDA (Strategy PlayMode)                                   (* hed "2026 revival")
    (* Map (strategy, play-mode) pair to the rule class name.
       Mirrors the SELECTQ structure in EP.MinPlay / EP.ShootPlay / EP.EclipsePlay. *)
    (SELECTQ Strategy
      ((QUOTE Minimizing)
        (SELECTQ PlayMode
          ((QUOTE FollowSuit) (QUOTE follow.play))
          ((QUOTE Dump)       (QUOTE dump.play))
          ((QUOTE Lead)       (QUOTE lead.play))
          (QUOTE lead.play)))
      ((QUOTE Shooting)
        (SELECTQ PlayMode
          ((QUOTE FollowSuit) (QUOTE shoot.follow))
          ((QUOTE Dump)       (QUOTE shoot.dump))
          ((QUOTE Lead)       (QUOTE shoot.lead))
          (QUOTE shoot.lead)))
      ((QUOTE Eclipsing)
        (SELECTQ PlayMode
          ((QUOTE FollowSuit) (QUOTE eclipse.follow))
          ((QUOTE Dump)       (QUOTE eclipse.dump))
          ((QUOTE Lead)       (QUOTE eclipse.lead))
          (QUOTE eclipse.lead)))
      (QUOTE lead.play)])

(EP.Trick
  [LAMBDA (self Trick)                                          (* hed "2026 revival")
    (* Trick message (optional): update Maggie tracking, history, opponent models,
       and re-evaluate strategy. *)
    (* Track Maggie *)
    (if (CardList.Member (CP.Maggie) (Trick.Cards Trick))
        then (EP.PUT.VALUE self (QUOTE MaggieStatus) (QUOTE Played))
             (EP.PUT.VALUE self (QUOTE MaggieLocation) (QUOTE Elsewhere)))
    (* Update history *)
    (EP.ComputeStats (EP.GET.VALUE self (QUOTE history)) Trick)
    (* Update opponent models *)
    (for OpSlot in (QUOTE (LeftPlayer RightPlayer AcrossPlayer))
       bind CurOp
       do (SETQ CurOp (EP.GET.VALUE self OpSlot))
          (EP.PUT.VALUE self (QUOTE CurrentOpponent) CurOp)
          (EP.UpdateModel CurOp Trick))
    (* Re-evaluate strategy *)
    (EP.REMOVE.ALL.LOCAL.VALUES self (QUOTE NewStrategy))
    (EP.RunRules self (QUOTE trick.evaluation) (QUOTE NewStrategy))
    (EP.PUT.VALUE self (QUOTE Strategy) (EP.GET.VALUE self (QUOTE NewStrategy))])

(EP.Results
  [LAMBDA NIL                                                   (* hed "2026 revival")
    (* Results message (optional): no action needed for the Expert player. *)
    NIL])

)

;; ============================================================
;; Section 5: Player construction (H.Apply seam)
;; ============================================================
(DEFINEQ

(EP.Create
  [LAMBDA (Open?)                                               (* hed "2026 revival")
    (* Create a complete Expert Player: an EP.PlayerClass composite wrapped in
       the Player record that H.Apply / H.MakePlayer expects.
       Returns a Player record with Type=Lisp and an EPMapping dispatch table. *)
    (LET* ((PUnit (EP.MakePlayer Open?))
           (PName (EP.GET.VALUE PUnit (QUOTE Name))))
      (create Player
              Name   ← PName
              Number ← NIL          (* filled in by H.Deal when seating *)
              Type   ← (QUOTE Lisp)
              Object ← PUnit
              Mapping ← EPMapping])

(RPAQQ EPMapping
  ((GiveHand . EP.GiveHand)
   (PassOut  . EP.PassOut)
   (PassIn   . EP.PassIn)
   (Play     . EP.Play)
   (Trick    . EP.Trick)
   (Results  . EP.Results)))

)

;; ============================================================
;; Section 6: Teardown
;; ============================================================
(DEFINEQ

(KillExperts
  [LAMBDA NIL                                                   (* hed "2026 revival")
    (* Remove all Expert player instances.  In the original KEE version this
       deleted KEE units; here we just GC them by clearing any global references.
       H.GameList and Player arrays are reset by the normal game teardown. *)
    NIL])

)

;; ============================================================
;; Section 7: Printing / debugging utilities
;; ============================================================
(DEFINEQ

(EP.PrintLastGameReasons
  [LAMBDA (self)                                                (* hed "2026 revival")
    (* Print reason log for every Expert player in the last game.
       self = an EP.PlayerClass instance (or NIL for all). *)
    (if self
        then (EP.PrintReasons (EP.GET.VALUE self (QUOTE history)) NIL)
      else (if H.LastGame
               then (for Player in (fetch Players of H.LastGame)
                       do (if (EQUAL (fetch Type of Player) (QUOTE Lisp))
                              then (LET ((Obj (fetch Object of Player)))
                                     (if (TYPEP Obj (QUOTE EP.PlayerClass))
                                         then (EP.PrintReasons
                                                (EP.GET.VALUE Obj (QUOTE history))
                                                NIL])

(EP.PrintReasons
  [LAMBDA (self filename)                                       (* hed "2026 revival")
    (* Print the reason log for one history unit.
       self = EP.HistoryClass.  filename = stream, filename string, or NIL for stdout. *)
    (LET [(Stream (if (NULL filename)
                      then T
                    elseif (STREAMP filename)
                      then filename
                    else (OPENSTREAM filename (QUOTE OUTPUT))))]
      (printout Stream .FONT (QUOTE (TIMESROMAN 12 BOLD))
                .CENTER 0 "Reasoning for game of player "
                (EP.GET.VALUE (EP.GET.VALUE self (QUOTE Player)) (QUOTE Name))
                T T)
      (printout Stream .FONT BOLDFONT "Play" .TAB 10 "Reason" .FONT DEFAULTFONT T)
      (for reason in (EP.GET.VALUES self (QUOTE Reasons))
         do (printout Stream (CAR reason) .TAB 10 (CADR reason) T])

)
