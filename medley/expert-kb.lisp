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

(* "Message handlers: (class message function documentation).  The EP.* function names come from the listing; which unit each one is a handler on, and under what message name, is reconstructed from how the code and rules send them.  SuitWithFewestWinners (sent by rule compute.weak.suit) is EP.FewestWinners; AllCardSuits (sent by edump.useless) had no surviving function and is reconstructed below.")
(RPAQQ EP.Handlers
       ((EP.ExpertPlayers Create EP.Create
          "Create an Expert Player: its player unit plus a History unit and three Opponent Model units.  Returns the Administrator's Player record (Type Kee).")
        (EP.ExpertPlayer GiveHand EP.GiveHand
          "Administrator message: take a new 13-card hand; reset the History and the three Opponent Models for the deal.")
        (EP.ExpertPlayer PassOut EP.PassOut
          "Administrator message: pick a strategy (rule class initial.evaluation), then let the strategy's pass-out rules choose the three cards to pass, and return them.")
        (EP.ExpertPlayer PassIn EP.PassIn
          "Administrator message: take the three cards passed in, model the passer (opponent.passin.evaluation, all rules), and re-evaluate my strategy (passin.evaluation).")
        (EP.ExpertPlayer Play EP.Play
          "Administrator message: choose a card for this trick -- the current strategy queries its lead, follow or dump rule class -- remove it from my hand and return it.")
        (EP.ExpertPlayer Trick EP.Trick
          "Administrator message: a trick is complete.  Update the History and each Opponent Model, then re-evaluate my strategy (trick.evaluation).")
        (EP.ExpertPlayer Results EP.Results
          "Administrator message at the end of a deal.  The Expert keeps no results.")
        (EP.ExpertPlayer GetOpponent EP.GetOpponent
          "The Opponent Model for a player number, or for a location (Left, Right or Across).")
        (EP.ExpertPlayer DoPass EP.DoPass
          "Used by the pass-out rules: add cards to the pass if that keeps it at three or fewer.  Returns the new count, or NIL.")
        (EP.ExpertPlayer HeartyNonShooterVoidSuits EP.HeartyNonShooterVoidSuits
          "Suits that some opponent other than the suspected shooter, and still holding hearts, is known to be void in.")
        (EP.ExpertPlayer HeartyOpponentVoidSuits EP.HeartyOpponentVoidSuits
          "Suits that some opponent still holding hearts is known to be void in.")
        (EP.Histories PrintLastGameReasons EP.PrintLastGameReasons
          "Print every Expert's play-by-play reasons for the last game, one file per player.")
        (EP.History Init EP.Init
          "Reset for a new deal: all 52 cards unplayed, and this deal's points folded into the totals.")
        (EP.History ComputeStats EP.ComputeStats
          "Record a completed trick: the cards played in each suit, the points to the winner's seat, and the new winners and losers.")
        (EP.History ComputeWinnersAndLosers EP.ComputeWinnersAndLosers
          "Recompute the highest (winner) and lowest (loser) unplayed card of each suit.")
        (EP.History Equivalent? EP.Equivalent?
          "Are two cards equivalent -- same suit, every card between them played or in my hand?  With Not? true: are they not?")
        (EP.History EquivalentCards EP.EquivalentCards
          "The cards equivalent to a card, among the given cards or else among my cards in its suit.")
        (EP.History HighestEquivalent EP.HighestEquivalent
          "The highest card equivalent to a card, among the given cards or my cards in its suit.")
        (EP.History LowestEquivalent EP.LowestEquivalent
          "The lowest card equivalent to a card, among the given cards or my cards in its suit.")
        (EP.History NonWinners EP.NonWinners
          "My cards (of a suit, or among the given cards) that are not equivalent to their suit's current winner.")
        (EP.History Winners EP.Winners
          "My cards (of a suit, or among the given cards) that are equivalent to their suit's current winner.")
        (EP.History Losers EP.Losers
          "My cards (of a suit, or among the given cards) that are equivalent to their suit's current loser.")
        (EP.History GetWinner EP.GetWinner
          "The highest unplayed card of a suit.")
        (EP.History GetLoser EP.GetLoser
          "The lowest unplayed card of a suit.")
        (EP.History WinnerSuit? EP.WinnerSuit?
          "Is this a suit where all my cards are winners, or where I hold more winners than there are other unplayed cards?")
        (EP.History WinnerSuits EP.WinnerSuits
          "The suits for which WinnerSuit? holds.")
        (EP.History FewestWinners EP.FewestWinners
          "The suit, not among the excluded ones, whose winner has the fewest equivalents in my hand.")
        (EP.History SuitWithFewestWinners EP.FewestWinners
          "My weakest suit for shooting: the suit, not among the excluded ones, whose winner has the fewest equivalents in my hand (rule compute.weak.suit).")
        (EP.History NumberWithPoints EP.NumberWithPoints
          "How many players have taken points this deal.")
        (EP.History SuitsWithCards EP.SuitsWithCards
          "The suits I still hold cards in.")
        (EP.History AllCardSuits EP.AllCardSuits
          "Suits in which every unplayed card is in my hand (reconstructed; rule edump.useless).")
        (EP.History PrintReasons EP.PrintReasons
          "Print this player's play-by-play reasons for the last game to a file or stream.")
        (EP.OpponentModel Init EP.OpInit
          "Reset for a new deal: forget known cards, voids, tricks won and the strategy certainty factors.")
        (EP.OpponentModel UpdateModel EP.UpdateModel
          "Record this opponent's card in a completed trick, note a new void, and update the certainty that it is shooting (opponent.trick.evaluation, all rules).")
        (EP.OpponentModel LastCardPlayed EP.LastCardPlayed
          "The last card this opponent played.")
        (EP.MinimizingStrategy PassOut EP.MinPass
          "Minimizing pass: query minimizing.passout until three cards are chosen.")
        (EP.MinimizingStrategy Play EP.MinPlay
          "Minimizing play: query lead.play, follow.play or dump.play for the card.")
        (EP.ShootingStrategy PassOut EP.ShootPass
          "Shooting pass: query shooting.passout until three cards are chosen.")
        (EP.ShootingStrategy Play EP.ShootPlay
          "Shooting play: query shoot.lead, shoot.follow or shoot.dump for the card.")
        (EP.EclipsingStrategy Play EP.EclipsePlay
          "Eclipsing play (stopping a shooter): query eclipse.lead, eclipse.follow or eclipse.dump for the card.")))

(DEFINEQ

(EP.BuildKB
  (LAMBDA NIL
    (* ; "Create the permanent units of the expert KB and wire the message handlers.  Run once when EXPERT loads (after the EP.* functions exist).")
    (for H in EP.Handlers do (KEE.DefHandler (CAR H) (CADR H) (CADDR H) (CADDDR H)))
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
