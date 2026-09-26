;; -*- Mode: Lisp; Package: Interlisp -*-
;; EP-LOOPS.LISP  —  HEARTS Expert Player, LOOPS object layer
;;
;; Replaces IntelliCorp KEE (unavailable in Medley) with plain InterLisp-D LOOPS.
;; This file defines the class hierarchy and instance accessors that mirror the
;; KEE unit structure described in ARCHITECTURE.md §8 and kee-expert-player.txt.
;;
;; The KEE "slot" model (GET.VALUE / PUT.VALUE / ADD.VALUE / REMOVE.VALUE /
;; GET.VALUES / REMOVE.ALL.LOCAL.VALUES / REMOVE.FACET) is approximated by
;; LOOPS instance variables accessed through a thin property-list shim when
;; LOOPS instance variables are inconvenient (multi-valued "facets").
;;
;; Class hierarchy:
;;
;;   Object
;;     EP.PlayerClass          — one expert player unit (was KEE unit expert.players.XXX)
;;     EP.HistoryClass         — history bookkeeping unit (was XXXHistory)
;;     EP.OpponentModelClass   — one opponent model (was XXXLeftPlayer etc.)
;;     EP.StrategyClass        — abstract strategy (was Minimizing / Shooting / Eclipsing KEE units)
;;       EP.MinimizingStrategy
;;       EP.ShootingStrategy
;;       EP.EclipsingStrategy
;;
;; Certainty Factors:
;;   Opponent strategy is tracked with EMYCIN-style certainty factors stored in
;;   the OpponentModel's CF.alist: ((Minimizing . <cf>) (Shooting . <cf>) ...).
;;   EP.CF.Update and EP.CF.Get implement the :UPDATE accumulation rule from KEE.
;;
;; Written for the HEARTS revival (github.com/athena-ceo/hearts).
;; Phase 2b — KEE Expert Player reimplementation.
;; Author: Claude Code (Anthropic), with Harley Davis, 2026.

(DEFINEQ

;; ============================================================
;; Low-level multi-valued slot helpers
;; (KEE allowed multiple values per slot; LOOPS instance vars are single-valued.
;;  We simulate multi-valued slots with a separate association list stored as
;;  a LOOPS instance variable named <SlotName>.MULTI or on a local plist.)
;; ============================================================

(EP.GET.VALUES
  [LAMBDA (Unit Slot)                                           (* hed "2026 revival")
    (LET ((iv (SEND Unit (MKATOM (CONCAT "get." Slot)))))
      (if (LISTP iv)
          then iv
        else (if iv then (LIST iv) else NIL])

(EP.PUT.VALUE
  [LAMBDA (Unit Slot Val)                                       (* hed "2026 revival")
    (SEND Unit (MKATOM (CONCAT "set." Slot)) Val)
    Val])

(EP.GET.VALUE
  [LAMBDA (Unit Slot)                                          (* hed "2026 revival")
    (CAR (EP.GET.VALUES Unit Slot])

(EP.ADD.VALUE
  [LAMBDA (Unit Slot Val)                                       (* hed "2026 revival")
    (LET ((cur (EP.GET.VALUES Unit Slot)))
      (EP.PUT.VALUE Unit Slot (CONS Val cur))
      Val])

(EP.ADD.VALUES
  [LAMBDA (Unit Slot Vals)                                      (* hed "2026 revival")
    (for V in Vals do (EP.ADD.VALUE Unit Slot V))
    Vals])

(EP.REMOVE.VALUE
  [LAMBDA (Unit Slot Val)                                       (* hed "2026 revival")
    (EP.PUT.VALUE Unit Slot (REMOVE Val (EP.GET.VALUES Unit Slot)))
    Val])

(EP.REMOVE.ALL.LOCAL.VALUES
  [LAMBDA (Unit Slot)                                           (* hed "2026 revival")
    (EP.PUT.VALUE Unit Slot NIL)])

(EP.REPLACE.VALUE
  [LAMBDA (Unit Slot Old New)                                   (* hed "2026 revival")
    (EP.PUT.VALUE Unit Slot (SUBST New Old (EP.GET.VALUES Unit Slot)))
    New])

)

;; ============================================================
;; Certainty-Factor helpers (EMYCIN-style, as used in KEE)
;; ============================================================
(DEFINEQ

(EP.CF.Update
  [LAMBDA (Unit Hypothesis Delta)                               (* hed "2026 revival")
    (* Accumulate a certainty-factor update for an opponent's strategy hypothesis.
       Uses the standard EMYCIN combine rule:
         if same sign:  cf' = cf + delta * (1 - |cf|)
         if diff sign:  cf' = (cf + delta) / (1 - min(|cf|,|delta|))
       Stored in Unit's CF.alist slot.)
    (LET* ((al (EP.GET.VALUE Unit (QUOTE CF.alist)))
           (old (OR (CDR (FASSOC Hypothesis al)) 0))
           (new (if (GREATERP (TIMES old Delta) 0)
                    then (PLUS old (TIMES Delta (DIFFERENCE 1 (ABS old))))
                  else (QUOTIENT (PLUS old Delta)
                                 (DIFFERENCE 1 (MIN (ABS old) (ABS Delta))))))
           (newclamped (MAX -1 (MIN 1 new)))
           (newalist (CONS (CONS Hypothesis newclamped)
                           (for pair in al collect pair unless (EQ (CAR pair)
                                                                   Hypothesis)))))
      (EP.PUT.VALUE Unit (QUOTE CF.alist)
                   newalist)
      newclamped])

(EP.CF.Get
  [LAMBDA (Unit Hypothesis)                                     (* hed "2026 revival")
    (OR (CDR (FASSOC Hypothesis (EP.GET.VALUE Unit (QUOTE CF.alist)))) 0])

(EP.CF.Reset
  [LAMBDA (Unit)                                                (* hed "2026 revival")
    (EP.PUT.VALUE Unit (QUOTE CF.alist)
                 NIL)])

)

;; ============================================================
;; LOOPS class definitions
;; ============================================================

(DEFINECLASS EP.HistoryClass ()
  (CardsLeft      :initform NIL)     (* all 52 cards not yet played *)
  (CardsPlayed    :initform NIL)
  (SpadesLeft     :initform NIL)
  (HeartsLeft     :initform NIL)
  (DiamondsLeft   :initform NIL)
  (ClubsLeft      :initform NIL)
  (SpadesPlayed   :initform NIL)
  (HeartsPlayed   :initform NIL)
  (DiamondsPlayed :initform NIL)
  (ClubsPlayed    :initform NIL)
  (SpadeWinner    :initform NIL)
  (HeartWinner    :initform NIL)
  (DiamondWinner  :initform NIL)
  (ClubWinner     :initform NIL)
  (SpadeLoser     :initform NIL)
  (HeartLoser     :initform NIL)
  (DiamondLoser   :initform NIL)
  (ClubLoser      :initform NIL)
  (MyPoints       :initform 0)
  (LeftPoints     :initform 0)
  (RightPoints    :initform 0)
  (AcrossPoints   :initform 0)
  (MyTotalPoints  :initform 0)
  (LeftTotalPoints  :initform 0)
  (RightTotalPoints :initform 0)
  (AcrossTotalPoints :initform 0)
  (Reasons        :initform NIL)
  (Player         :initform NIL)    (* back-pointer to EP.PlayerClass instance *)
)

(DEFINECLASS EP.OpponentModelClass ()
  (PlayerNum    :initform NIL)
  (Points       :initform 0)
  (PlayedCards  :initform NIL)
  (HandCards    :initform NIL)
  (TricksWon    :initform NIL)
  (Voids        :initform NIL)
  (CF.alist     :initform NIL)      (* certainty-factor alist for strategy *)
  (MainPlayer   :initform NIL)      (* back-pointer to EP.PlayerClass *)
)

(DEFINECLASS EP.PlayerClass ()
  (Name           :initform NIL)
  (Hand           :initform NIL)
  (HandWindow     :initform NIL)
  (MyNumber       :initform NIL)
  (PlayerNumber   :initform NIL)
  (history        :initform NIL)    (* EP.HistoryClass instance *)
  (LeftPlayer     :initform NIL)    (* EP.OpponentModelClass instance *)
  (RightPlayer    :initform NIL)
  (AcrossPlayer   :initform NIL)
  (Strategy       :initform NIL)    (* symbol: Minimizing Shooting Eclipsing *)
  (NewStrategy    :initform NIL)
  (Shooter        :initform NIL)    (* OpponentModel of suspected shooter *)
  (MaggieStatus   :initform (QUOTE NotPlayed))  (* NotPlayed / Played *)
  (MaggieLocation :initform (QUOTE Elsewhere))  (* InHand / Elsewhere *)
  (TrickNumber    :initform 0)
  (LegalCards     :initform NIL)
  (CurrentTrick   :initform NIL)
  (PlayMode       :initform NIL)    (* Lead / FollowSuit / Dump *)
  (PlayCard       :initform NIL)
  (LatestReason   :initform NIL)
  (PassDir        :initform NIL)
  (PassCards      :initform NIL)
  (NumberOfPassCards :initform 0)
  (PassInCards    :initform NIL)
  (PassInFrom     :initform NIL)
  (PassOutRuleClass :initform NIL)
  (CurrentOpponent  :initform NIL)
  (Personality    :initform NIL)    (* EP.PersonalityClass instance *)
  (WeakestSuit    :initform NIL)
  (PlayedCards    :initform NIL)    (* history shortcut: list of cards played last trick *)
)

(DEFINECLASS EP.PersonalityClass ()
  (* Personality parameters — analogous to KEE personality unit slots.
     These control strategy thresholds; values below are reasonable defaults
     derived from reading the original rules. *)
  (TriggerHappiness     :initform 0.35)   (* CF threshold to switch to Eclipsing *)
  (PIMaxLowSpades       :initform 3)      (* pass-in: max low spades to still consider shooting *)
  (PIMaxLoserHearts     :initform 3)      (* pass-in: max loser hearts *)
  (PILowestHeart        :initform 10)     (* pass-in: minimum heart value (face-card-ish) *)
  (PIMinShootPoints     :initform 10)     (* pass-in: min bridge pts to consider shooting *)
  (POMaxLowSpades       :initform 2)      (* pre-pass: max low spades *)
  (POMaxLoserHearts     :initform 2)      (* pre-pass: max loser hearts *)
  (POMinShootPoints     :initform 12)     (* pre-pass: min bridge pts *)
  (LowPassPoints        :initform 3)      (* opponent pass: "low" bridge point threshold *)
  (HiPassPoints         :initform 10)     (* opponent pass: "high" bridge point threshold *)
  (SpadeProtLen         :initform 3)      (* min # spades for decent protection *)
  (LastSingletonTrick   :initform 6)      (* only play singleton before this trick *)
)

;; ============================================================
;; Accessor shim: SEND-compatible GET/SET for each named slot.
;; In Medley LOOPS, (SEND obj 'get.Slot) and (SEND obj 'set.Slot val)
;; map directly to the generated accessor methods.  We expose the same
;; names that the EP.* helpers expect via (EP.GET.VALUE unit 'Slot) etc.
;; The class definitions above generate these accessors automatically via
;; DEFINECLASS; this section just documents the convention.
;; ============================================================

;; ============================================================
;; Name generation for expert players (mirrors ExpertNames from kee-expert-player.txt)
;; ============================================================
(RPAQQ ExpertNames
  (Einstein Spinoza Aristotle Plato Nietzsche Tolstoy Dostoevsky Hoyle Schopenhauer
   Kant Leibniz Heidegger Hegel Thoreau HenryJames WilliamJames Melville
   EdgarPoe Democritus Darwin Goedel Fichte Flaubert Hemingway Maupassant
   MarcelProust Voltaire BlaisePascal Moliere ChuckBabbage SinclairLewis
   Fitzgerald JohnRawls BertRussell ALWhitehead MarvinMinsky JoeConrad
   JamesJoyce Descartes))

;; ============================================================
;; EP.PersonalityClass — create with defaults
;; ============================================================
(DEFINEQ

(EP.MakePersonality
  [LAMBDA NIL                                                   (* hed "2026 revival")
    (MAKE-INSTANCE (QUOTE EP.PersonalityClass)])

)

;; ============================================================
;; Expert player unit constructor
;; (Replaces KEE UNITCREATE and wires up sub-units.)
;; ============================================================
(DEFINEQ

(EP.MakePlayer
  [LAMBDA (Open?)                                               (* hed "2026 revival")
    (* Create a complete expert player composite:
       one EP.PlayerClass + one EP.HistoryClass + three EP.OpponentModelClass.
       Returns an EP.PlayerClass instance. *)
    (LET* ((PName (GENSYM (CAR (FNTH ExpertNames (RAND 1 (FLENGTH ExpertNames))))))
           (PUnit (MAKE-INSTANCE (QUOTE EP.PlayerClass)))
           (HUnit (MAKE-INSTANCE (QUOTE EP.HistoryClass)))
           (LUnit (MAKE-INSTANCE (QUOTE EP.OpponentModelClass)))
           (RUnit (MAKE-INSTANCE (QUOTE EP.OpponentModelClass)))
           (AUnit (MAKE-INSTANCE (QUOTE EP.OpponentModelClass))))
      (EP.PUT.VALUE PUnit (QUOTE Name) PName)
      (EP.PUT.VALUE PUnit (QUOTE history) HUnit)
      (EP.PUT.VALUE PUnit (QUOTE LeftPlayer) LUnit)
      (EP.PUT.VALUE PUnit (QUOTE RightPlayer) RUnit)
      (EP.PUT.VALUE PUnit (QUOTE AcrossPlayer) AUnit)
      (EP.PUT.VALUE PUnit (QUOTE Personality) (EP.MakePersonality))
      (EP.PUT.VALUE HUnit (QUOTE Player) PUnit)
      (EP.PUT.VALUE LUnit (QUOTE MainPlayer) PUnit)
      (EP.PUT.VALUE RUnit (QUOTE MainPlayer) PUnit)
      (EP.PUT.VALUE AUnit (QUOTE MainPlayer) PUnit)
      (if Open?
          then (EP.PUT.VALUE PUnit (QUOTE HandWindow)
                             (Open.CreateWindow PName "%\"expert%\"")))
      PUnit])

)
