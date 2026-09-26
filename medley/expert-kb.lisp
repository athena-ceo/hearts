;; EXPERT-KB -- the reconstructed KEE knowledge base "expert", as LOOPS classes and units.
;;
;; What survives from 1986 is the Interlisp EP.* code (transcription/kee-expert-player.txt)
;; and the rule listing (transcription/kee-expert-rules.txt).  The KEE knowledge-base file
;; itself -- the unit hierarchy, slot declarations, message-handler wiring and personality
;; values -- is lost.  This file reconstructs it from how the code and rules use it and
;; from the 1986 overview (transcription/docs/overview.md section 4.1).  Everything here
;; is a reconstruction; each guess is marked.  build_expert.py inserts this file into
;; EXPERT after KEELOOPS and before the transcribed EP.* code and rules.

(* "Reconstructed KEE knowledge base: unit classes (LOOPS classes)")

(* ; "expert.players: the class unit.  Own slot CurrentPlayer (set by each player before it queries, so the rules can find it); message Create makes a player.")
(DEFCLASS EP.ExpertPlayers
   (MetaClass Class) (Supers KEE.ClassUnit)
   (InstanceVariables (CurrentPlayer NIL)))

(* ; "A member of expert.players: one Expert Player.  Slots are every slot the EP code and rules read or write.")
(DEFCLASS EP.ExpertPlayer
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (Hand NIL) (HandWindow NIL) (MyNumber NIL) (PlayerNumber NIL)
          (history NIL) (LeftPlayer NIL) (RightPlayer NIL) (AcrossPlayer NIL)
          (Strategy NIL) (NewStrategy NIL) (Shooter NIL) (WeakestSuit NIL)
          (MaggieStatus NotPlayed) (MaggieLocation Elsewhere)
          (TrickNumber 0) (LegalCards NIL) (CurrentTrick NIL) (PlayMode NIL)
          (PlayCard NIL) (LatestReason NIL)
          (PassDir NIL) (PassCards NIL Cardinality Multiple) (NumberOfPassCards 0)
          (PassInCards NIL) (PassInFrom NIL) (CurrentOpponent NIL)
          (Personality standard.personality)))

(* ; "histories: the class unit for History units.")
(DEFCLASS EP.Histories
   (MetaClass Class) (Supers KEE.ClassUnit))

(* ; "A History: the cards seen this deal, winners/losers per suit, and points.")
(DEFCLASS EP.History
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (Player NIL)
          (CardsLeft NIL Cardinality Multiple) (CardsPlayed NIL Cardinality Multiple)
          (SpadesLeft NIL Cardinality Multiple) (HeartsLeft NIL Cardinality Multiple)
          (DiamondsLeft NIL Cardinality Multiple) (ClubsLeft NIL Cardinality Multiple)
          (SpadesPlayed NIL Cardinality Multiple) (HeartsPlayed NIL Cardinality Multiple)
          (DiamondsPlayed NIL Cardinality Multiple) (ClubsPlayed NIL Cardinality Multiple)
          (SpadeWinner NIL) (HeartWinner NIL) (DiamondWinner NIL) (ClubWinner NIL)
          (SpadeLoser NIL) (HeartLoser NIL) (DiamondLoser NIL) (ClubLoser NIL)
          (MyPoints 0) (LeftPoints 0) (RightPoints 0) (AcrossPoints 0)
          (MyTotalPoints 0) (LeftTotalPoints 0) (RightTotalPoints 0) (AcrossTotalPoints 0)
          (Reasons NIL Cardinality Multiple)))

(* ; "opponent.models: the class unit for Opponent Models.")
(DEFCLASS EP.OpponentModels
   (MetaClass Class) (Supers KEE.ClassUnit))

(* ; "An Opponent Model.  Strategy is only ever used through its certainty factors (UNCERTAIN.VALUES facet).")
(DEFCLASS EP.OpponentModel
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (MainPlayer NIL) (PlayerNum NIL) (Points 0)
          (HandCards NIL Cardinality Multiple) (PlayedCards NIL Cardinality Multiple)
          (TricksWon NIL Cardinality Multiple) (Voids NIL Cardinality Multiple)
          (Strategy NIL Cardinality Multiple)))

(* ; "strategies: Minimizing, Shooting, Eclipsing.  Each has PassOut / Play handlers that run its rule classes.")
(DEFCLASS EP.Strategies
   (MetaClass Class) (Supers KEE.ClassUnit))

(DEFCLASS EP.Strategy
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (PassOutRuleClass NIL)))

(DEFCLASS EP.MinimizingStrategy
   (MetaClass Class) (Supers EP.Strategy))

(DEFCLASS EP.ShootingStrategy
   (MetaClass Class) (Supers EP.Strategy))

(DEFCLASS EP.EclipsingStrategy
   (MetaClass Class) (Supers EP.Strategy))

(* ; "personalities: the thresholds the rules consult.  The 1986 values are lost.  RECONSTRUCTED: POMaxLowSpades 2, POMaxLoserHearts 3, POMinShootPoints 15 and LowPassPoints 0 are the values the overview (4.2.1) reports for Dostoevsky.  TriggerHappiness 0.5 is inferred from Example 2: Kant suspected Marcel after the pass (CF .44 from ope.two.h.pass + ope.low.pass) and switched to Eclipsing after trick 1 (+ ote.low.on.trick.1 -> .51), so the threshold lies in (.44, .51].  LastSingletonTrick 6 follows the lead.single.* comments.  The rest are judgement calls.")
(DEFCLASS EP.Personalities
   (MetaClass Class) (Supers KEE.ClassUnit))

(DEFCLASS EP.Personality
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (TriggerHappiness 0.5)
          (POMaxLowSpades 2) (POMaxLoserHearts 3) (POMinShootPoints 15)
          (PIMaxLowSpades 2) (PIMaxLoserHearts 2) (PILowestHeart 10) (PIMinShootPoints 15)
          (LowPassPoints 0) (HiPassPoints 6)
          (SpadeProtLen 4) (LastSingletonTrick 6)))

(* "Message handlers.  The EP.* function names come from the listing; which unit each one is a handler on, and under what message name, is reconstructed from how the code and rules send them.  SuitWithFewestWinners (sent by rule compute.weak.suit) is EP.FewestWinners; AllCardSuits (sent by edump.useless) had no surviving function and is reconstructed below.")
(RPAQQ EP.Handlers
       ((EP.ExpertPlayers Create EP.Create)
        (EP.ExpertPlayer GiveHand EP.GiveHand)
        (EP.ExpertPlayer PassOut EP.PassOut)
        (EP.ExpertPlayer PassIn EP.PassIn)
        (EP.ExpertPlayer Play EP.Play)
        (EP.ExpertPlayer Trick EP.Trick)
        (EP.ExpertPlayer Results EP.Results)
        (EP.ExpertPlayer GetOpponent EP.GetOpponent)
        (EP.ExpertPlayer DoPass EP.DoPass)
        (EP.ExpertPlayer HeartyNonShooterVoidSuits EP.HeartyNonShooterVoidSuits)
        (EP.ExpertPlayer HeartyOpponentVoidSuits EP.HeartyOpponentVoidSuits)
        (EP.Histories PrintLastGameReasons EP.PrintLastGameReasons)
        (EP.History Init EP.Init)
        (EP.History ComputeStats EP.ComputeStats)
        (EP.History ComputeWinnersAndLosers EP.ComputeWinnersAndLosers)
        (EP.History Equivalent? EP.Equivalent?)
        (EP.History EquivalentCards EP.EquivalentCards)
        (EP.History HighestEquivalent EP.HighestEquivalent)
        (EP.History LowestEquivalent EP.LowestEquivalent)
        (EP.History NonWinners EP.NonWinners)
        (EP.History Winners EP.Winners)
        (EP.History Losers EP.Losers)
        (EP.History GetWinner EP.GetWinner)
        (EP.History GetLoser EP.GetLoser)
        (EP.History WinnerSuit? EP.WinnerSuit?)
        (EP.History WinnerSuits EP.WinnerSuits)
        (EP.History FewestWinners EP.FewestWinners)
        (EP.History SuitWithFewestWinners EP.FewestWinners)
        (EP.History NumberWithPoints EP.NumberWithPoints)
        (EP.History SuitsWithCards EP.SuitsWithCards)
        (EP.History AllCardSuits EP.AllCardSuits)
        (EP.History PrintReasons EP.PrintReasons)
        (EP.OpponentModel Init EP.OpInit)
        (EP.OpponentModel UpdateModel EP.UpdateModel)
        (EP.OpponentModel LastCardPlayed EP.LastCardPlayed)
        (EP.MinimizingStrategy PassOut EP.MinPass)
        (EP.MinimizingStrategy Play EP.MinPlay)
        (EP.ShootingStrategy PassOut EP.ShootPass)
        (EP.ShootingStrategy Play EP.ShootPlay)
        (EP.EclipsingStrategy Play EP.EclipsePlay)))

(DEFINEQ

(EP.BuildKB
  (LAMBDA NIL
    (* ; "Create the permanent units of the expert KB and wire the message handlers.  Run once when EXPERT loads (after the EP.* functions exist).")
    (for H in EP.Handlers do (KEE.DefHandler (CAR H) (CADR H) (CADDR H)))
    (for CU in (QUOTE ((EP.ExpertPlayers expert.players EP.ExpertPlayer)
                       (EP.Histories histories EP.History)
                       (EP.OpponentModels opponent.models EP.OpponentModel)
                       (EP.Strategies strategies EP.Strategy)
                       (EP.Personalities personalities EP.Personality)))
       do (PutValue (KEE.MakeUnit (CAR CU) (CADR CU)) (QUOTE KEE.MemberClass) (CADDR CU)))
    (for S in (QUOTE ((EP.MinimizingStrategy Minimizing minimizing.passout)
                      (EP.ShootingStrategy Shooting shooting.passout)
                      (EP.EclipsingStrategy Eclipsing NIL)))
       do (PutValue (KEE.MakeUnit (CAR S) (CADR S)) (QUOTE PassOutRuleClass) (CADDR S)))
    (UNITCREATE (QUOTE standard.personality) NIL (QUOTE personalities))
    (QUOTE expert)))

)

(* ;;; "Lost image definitions: called by the rules, defined nowhere in the listings.")
(DEFINEQ

(EP.AllCardSuits
  (LAMBDA (self)
    (* ; "RECONSTRUCTED (sent by rule edump.useless, 'dumping a useless suit'): the suits in which every card still unplayed is in my own hand -- I can neither be forced nor help anyone in them.")
    (LET ((Hand (GET.VALUE (GET.VALUE self (QUOTE Player)) (QUOTE Hand))))
         (for Suit in SuitValues
            collect Suit
            when (AND (Hand.CardsInSuit Hand Suit)
                      (for C in (CardList.CardsOfSuit (GET.VALUES self (QUOTE CardsLeft)) Suit)
                         always (CardList.Member C (Hand.CardsInSuit Hand Suit))))))))

(CardList.EliminateSuits
  (LAMBDA (CardList Suits)
    (* ; "RECONSTRUCTED.  The overview (4.2.1, footnote 6) notes this was undefined at the time of the example game, so slead.non.op.void.loser never fired.  Plural of CardList.EliminateSuit.")
    (for C in CardList collect C unless (FMEMB (Card.Suit C) Suits))))

(CardList.MaxCard
  (LAMBDA (CardList InSuit)
    (* ; "RECONSTRUCTED (rules follow.last.above.QS, follow.highest.below.QS): same as Card.MaxCard.")
    (Card.MaxCard CardList InSuit)))

(Card.CardsBetween
  (LAMBDA (Card1 Card2)
    (* ; "RECONSTRUCTED (rule sfol.little.over): the cards of the suit strictly between two cards.")
    (LET ((Lo (if (Card.Lower? Card1 Card2) then Card1 else Card2))
          (Hi (if (Card.Lower? Card1 Card2) then Card2 else Card1)))
         (for C in (for V in (Card.ValueSublist (Card.Value Lo) (Card.Value Hi))
                      collect (Card.Create V (Card.Suit Lo)))
            collect C unless (OR (Card.Equal? C Lo) (Card.Equal? C Hi))))))
)

(MOVD? (QUOTE Not.Null) (QUOTE Non.Null))
(* ; "RECONSTRUCTED: rule dump.hi.non.s is printed with Non.Null, a slip for Not.Null.")
