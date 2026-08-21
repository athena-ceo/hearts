;; ==== page 25 ====
                          NewAR CReg CountVar CardBM)
                         (SETQ CountVar (PACK* (QUOTE N)
                                               Suit))
                         (SETQ CReg (CREATEREGION (HP.SuitLength
                                                          (EVAL CountVar))
                                                  (EVAL (PACK* Suit
                                                              (QUOTE Y)))
                                                  CardWidth CardHeight))
                         (SET CountVar (ADD1 (EVAL CountVar)))
                         (SETQ CardBM (Card.CreateBM C))
                         (SETQ NewAR (create ACTIVEREGION
                                            REGION ← CReg
                                            HELPSTRING ←(CONCAT
                                             "Selects "
                                             (Card.PrintCard C))
                                            DOWNFN ← NIL
                                            UPFN ←(FUNCTION HP.Select)
                                            DATA ←(LIST C CardBM)))
                    [SETQ CardMap
                       (APPEND CardMap (LIST (LIST C CardBM CReg NewAR]
                    NewAR)))
        (SETACTIVEREGIONS HWin ARList)
        (WINDOWPROP HWin (QUOTE CardMap)
                    CardMap)
        (HP.Reshape HWin (MAX (HP.SuitLength ND)
                              (HP.SuitLength NC)
                              (HP.SuitLength NH)
                              (HP.SuitLength NS)
                              300))
        (RETURN HWin])

(HP.RemoveCard
  [LAMBDA (HWin Card)                                     (* rao "10-Apr-86 20:45")
    (LET [(Hand (WINDOWPROP HWin (QUOTE Hand]
      (Hand.RemoveCard Hand Card)
      (HP.RemakeHand HWin Hand])

(HP.Repaintfn
  [LAMBDA (Win)                                           (* rao "10-Apr-86 19:45")
    (PROG [(DS (WINDOWPROP Win (QUOTE DSP)))
           (CardMap (WINDOWPROP Win (QUOTE CardMap)))
           (SelectedCards (WINDOWPROP Win (QUOTE SelectedCards]

          (* * Print names of suits in window)


          (for suit in (QUOTE (Clubs: Diamonds: Hearts: Spades:)) as i from 0 to 3
             do (MOVETO 2 (DIFFERENCE 176 (TIMES i 50))
                        DS)
                (printout DS suit))

          (* * Display Card Map)


          [for CardEntry in CardMap do (LET ((Card (CAR CardEntry))
                                             (CardBM (CADR CardEntry))
                                             (CardReg (CADDR CardEntry))
                                             Selected?)
                                         (SETQ Selected? (FMEMB Card SelectedCards))
                                         (HP.MarkUnselected Win CardReg CardBM)
                                         (if Selected?
                                             then (HP.MarkSelected Win CardReg]
          (RETURN Win])

(HP.Reshape
  [LAMBDA (HWin Width)                                    (* rao "17-Apr-86 13:20")
    (LET [(OldReg (WINDOWPROP HWin (QUOTE REGION]
      [SHAPEW HWin (CREATEREGION (fetch LEFT of OldReg)
                                 (fetch BOTTOM of OldReg)
                                 (PLUS 10 Width)
                                 (PLUS (FONTHEIGHT (DSPFONT NIL WindowTitleDisplayStream))
                                       (fetch HEIGHT of OldReg]
      (REDISPLAYW HWin])

;; ==== page 26 ====
(HP.Select
  [LAMBDA (HWin CReg Data)                                (* rao "11-Apr-86 13:00")
    (PROG ((Card (CAR Data))
           (Pass? (EQ (WINDOWPROP HWin (QUOTE PassOrPlay))
                      (QUOTE Pass)))
           (SelectedCards (WINDOWPROP HWin (QUOTE SelectedCards)))
           MaxSelected NumSelected)
          (if (FMEMB Card SelectedCards)
              then (HP.Unselect HWin Card)
                   (RETURN))
          (if (NOT (WINDOWPROP HWin (QUOTE Ready?)))
              then (SETQ MaxSelected (if Pass?
                                         then 3
                                         else 1))
                   (SETQ NumSelected (LENGTH SelectedCards))
                   (if (GEQ NumSelected MaxSelected)
                       then (HP.Unselect HWin (CAR SelectedCards)))
                   (ACTIVEREGIONS/DOLOWLIGHT HWin (GETPICKREGION HWin))
                   (HP.MarkSelected HWin CReg)
                   (WINDOWADDPROP HWin (QUOTE SelectedCards)
                          Card)
                   (if (AND (NOT Pass?)
                            HPImmediatePlay)
                       then (WINDOWPROP HWin (QUOTE Ready?)
                                   T])

(HP.SuitLength
  [LAMBDA (Count)                                         (* rao "10-Apr-86 12:23")
    (PLUS (TIMES Count (PLUS CardWidth CardGap))
          SuitLabelOffset])

(HP.Unselect
  [LAMBDA (HWin Card)                                     (* rao "10-Apr-86 19:28")
    (LET ((PickAR (GETPICKREGION HWin))
          Creg CardBM CardData)
      (for C in (WINDOWPROP HWin (QUOTE CardMap)) do (SETQ CardData C) when (EQUAL (CAR C)
                                                                                   Card))
      (SETQ CardBM (CADR CardData))
      (SETQ Creg (CADDR CardData))
      (WINDOWDELPROP HWin (QUOTE SelectedCards)
             Card)
      (if (EQUAL (fetch REGION of PickAR)
                 Creg)
          then (ACTIVEREGIONS/DOLOWLIGHT HWin PickAR))
      (HP.MarkUnselected HWin Creg CardBM])

(HP.WaitForReady
  [LAMBDA (HWin Message)                                  (* rao "15-Apr-86 22:12")

    (* * Waits for Ready? to be true, indicating the human has chosen his cards.)


    (PROG [(Ready? (WINDOWPROP HWin (QUOTE Ready?]
          (while (NOT Ready?) as i from 1
             do (if (EQP i 10)
                    then (PROMPTPRINT Message))
                (DISMISS 3000)
                (SETQ Ready? (WINDOWPROP HWin (QUOTE Ready?)])

(TestHP
  [LAMBDA NIL                                             (* rao "10-Apr-86 19:38")
    (HP.GiveHand (fetch Object of (HP.Create (QUOTE Harley)))
                 (Hand.Create (HP.ChooseSomeCards 13 (HP.MakeDeck])
)

;; ==== page 27 ====
(* * Conservative Player)

[DECLARE: EVAL@COMPILE

(RECORD CP (Name Hand ThoughtWindow MaggiePlayed? CP.OpenHand? CP.HandWindow))
]

(RPAQQ ConservativeNames (BoringBart PredictablePete TheFork LiplessWonder Mabel SimpleSimon
                                VikingHelga Larry Curly Moe Shep Alfalfa Gilligan TheSkipper
                                TheProfessor MaryAnn MrHowell MrsHowell Ginger TheMinnow
                                FerdinandMarcos RonReagan Rambo Eisenhower RMNixon Kissinger
                                GeorgeBush Prince JerryLewis Dorothy TheScarecrow TheTinMan
                                CowardlyLion Toto JohnnyRotten LyndonLarouche Babbitt
                                MickeyMouse DonaldDuck Goofy Pluto MinnieMouse DaffyDuck
                                BugsBunny MrMagoo ElmerFudd))

(RPAQQ CPMapping ((GiveHand . CP.GiveHand)
                  (PassOut . CP.PassOut)
                  (PassIn . CP.PassIn)
                  (Play . CP.Play)
                  (Trick . CP.Trick)
                  (Results . CP.Results)))

(RPAQQ Maggie (S . Q))

(RPAQQ ThinkFlag? NIL)
(DEFINEQ

(CP.Create
  [LAMBDA (OpenHand?)                                     (* hed "4-May-86 16:38")
    (LET ([PlayerName (GENSYM (CAR (FNTH ConservativeNames (RAND 1 (FLENGTH ConservativeNames]
          ThoughtWindow NewPlayer)
      [if ThinkFlag?
          then (SETQ ThoughtWindow (CREATEW (GETBOXREGION 500 250 NIL NIL NIL (CONCAT
                                                    "Please find a place for the thinking window for "
                                                    PlayerName))
                                            (CONCAT "Thoughts of " PlayerName)))
               (WINDOWPROP ThoughtWindow (QUOTE SCROLLFN)
                      (FUNCTION SCROLLBYREPAINTFN))
               (DSPSCROLL T (WINDOWPROP ThoughtWindow (QUOTE DSP]
      (SETQ NewPlayer (create Player
                             Name ← PlayerName
                             Type ←(QUOTE Lisp)
                             Object ←[create CP
                                       Name ← PlayerName
                                       ThoughtWindow ← ThoughtWindow
                                       CP.OpenHand? ← OpenHand?
                                       CP.HandWindow ←(if OpenHand?
                                                          then (Open.CreateWindow
                                                                 PlayerName
                                                                 (QUOTE CP]
                             Mapping ← CPMapping))
      NewPlayer])

(CP.Follow
  [LAMBDA (self Trick HeartsBroken? FirstTrick?)          (* rao "3-May-86 12:08")
    (LET ((LeadSuit (Trick.LeadSuit Trick))
          [PlayNumber (ADD1 (FLENGTH (Trick.Cards Trick]
          (TWin (fetch ThoughtWindow of self))
          (Hand (fetch Hand of self))
          Spades SpadeLength LegalPlays LeadSuitCards HighestLeadInSuit LowerLeadSuitCards PlayCard)
      (SETQ LeadSuitCards (CP.GetCards self LeadSuit))
      [if LeadSuitCards
          then                                            (* Can follow suit: play highest card beneath the highest played so far.)
               (CP.Think self "I can follow suit: " LeadSuit T)
               [SETQ HighestLeadInSuit (Card.MaxCard (for card in (Trick.Cards Trick) collect card
                                                          when (EQUAL (fetch Suit of card)
                                                                      LeadSuit]

          (* Lead the highest card under the highest played so far in the lead suit unless there aren't any, in which case play the lowest in the suit)

;; ==== page 28 ====
               (SETQ PlayCard (if (SETQ LowerLeadSuitCards (for card in LeadSuitCards collect card
                                                                unless (Card.Higher? card
                                                                                     HighestLeadInSuit)))
                                  then                     (* There are lower cards to play. Guaranteed not to win trick.)
                                       (CP.Think self "I won't win this one!" T)
                                       (Card.MaxCard LowerLeadSuitCards)
                                elseif (EQP PlayNumber 4)
                                  then                     (* We're the last player. Guaranteed to win trick; might as well win big.)
                                       (CP.Think self "Oh well, I might as well win big." T)
                                       (if (AND (EQUAL LeadSuit (QUOTE S))
                                                (Card.Equal? [Card.MaxCard (SETQ Spades
                                                                                (Hand.CardsInSuit
                                                                                  Hand
                                                                                  (QUOTE S]
                                                            (CP.HasMaggie? self))
                                                (GREATERP (SETQ SpadeLength (FLENGTH Spades))
                                                          1))
                                           then (CAR (FNTH Spades (RAND 1 SpadeLength)))
                                           else (Card.MaxCard LeadSuitCards))
                                  else                     (* Make our best shot at losing. Play the lowest card in the suit.)
                                       (CP.Think self "Sure hope someone plays higher than me." T)
                                       (Card.MinCard LeadSuitCards)))
          else                                            (* The fun. Chance to dump cards. Order is: Maggie, high spades if Maggie, not yet played, winners, hearts, highest card in hand)
               (LET ((AllCards (H.GetLegals Hand Trick HeartsBroken? FirstTrick?))
                     Maggie HighSpade HighHeart Winner Hearts)
                 (SETQ PlayCard (if (AND (SETQ Maggie (CP.HasMaggie? self))
                                         (CardList.Member Maggie AllCards))
                                    then (CP.Think self "Eat this, sucker." T)
                                         Maggie
                                    elseif (AND (NOT (fetch MaggiePlayed? of self))
                                                (SETQ HighSpade (CP.HighSpades self))
                                                (CardList.Member HighSpade AllCards))
                                    then (CP.Think self "Don't want to eat the Black Bitch." T)
                                         HighSpade
                                    elseif (AND (SETQ Hearts (Hand.CardsInSuit Hand (QUOTE H)))
                                                (CardList.Member (SETQ HighHeart (Card.MaxCard Hearts))
                                                                 AllCards))
                                    then (CP.Think self "Munch, munch." T)
                                         HighHeart
                                    else (CP.Think self "My highest card." T)
                                         (Card.MaxCard AllCards]
      (CP.Think self "I will play the " (Card.PrintCard PlayCard)
             T)
      (CP.LoseCard self PlayCard)
      PlayCard])

(CP.GetCards
  [LAMBDA (self Suit)                                     (* rao "22-Apr-86 21:13")
    (Hand.CardsInSuit (fetch Hand of self)
           Suit])

(CP.GiveHand
  [LAMBDA (self Hand)                                     (* rao "23-Apr-86 09:54")
    (CP.Start self)
    (replace Hand of self with Hand)
    (if (fetch CP.OpenHand? of self)
        then (Open.RemakeWindow (fetch CP.HandWindow of self)
                    Hand])

(CP.HasMaggie?
  [LAMBDA (self)                                          (* rao "22-Apr-86 21:13")
    (LET ((TestMaggie (CP.Maggie)))
      (for card in (CP.GetCards self (QUOTE S)) thereis (Card.Equal? card TestMaggie])

(CP.HighSpades
  [LAMBDA (self)                                          (* rao "22-Apr-86 21:14")
    (LET [(HighestSpade (Card.MaxCard (CP.GetCards self (QUOTE S]
      (if (Card.Higher? HighestSpade (Card.Create (QUOTE J)
                                             (QUOTE S)))

;; ==== page 29 ====
          then HighestSpade])

(CP.Lead
  [LAMBDA (self Trick HeartsBroken? FirstTrick?)          (* rao "24-Apr-86 21:51")
    (LET ((LegalLeads (H.GetLegals (fetch Hand of self)
                              Trick HeartsBroken? FirstTrick?))
          [PossibleLeads (APPEND (CP.GetCards self (QUOTE C))
                                 (CP.GetCards self (QUOTE D]
          (HighSpades? (CP.HighSpades self))
          LeadCard)
      (SETQ PossibleLeads (INTERSECTION PossibleLeads LegalLeads))
      [if (OR (NOT HighSpades?)
              (fetch MaggiePlayed? of self))
          then                                            (* Can lead a spade if we don't have any high ones or if the queen has already been played)
               (CP.Think self "Spades would be good to lead..." T)
               (SETQ PossibleLeads (APPEND PossibleLeads (INTERSECTION (CP.GetCards self
                                                                              (QUOTE S))
                                                                       LegalLeads]
      [if HeartsBroken?
          then                                            (* OK to lead a heart if they have been broken.)
               (CP.Think self "I could lead hearts..." T)
               (SETQ PossibleLeads (APPEND PossibleLeads (INTERSECTION (CP.GetCards self
                                                                              (QUOTE H))
                                                                       LegalLeads]
      (if (NULL PossibleLeads)
          then                                            (* if none of the good ideas pan out, just lead whatever.)
               (CP.Think self "Nothing good to lead." T)
               (SETQ PossibleLeads LegalLeads))
      (CP.Think self "Out of possible leads ")
      (for card in PossibleLeads do (CP.Think self (Card.PrintCard card)
                                           " "))
      (CP.Think self T)
      (SETQ LeadCard (Card.MinCard PossibleLeads))
      (CP.Think self "    I will lead the " (Card.PrintCard LeadCard)
             T)
      (CP.LoseCard self LeadCard)
      LeadCard])

(CP.LoseCard
  [LAMBDA (self Card)                                     (* rao "22-Apr-86 21:23")
    (Hand.RemoveCard (fetch Hand of self)
             Card)
    (if (fetch CP.OpenHand? of self)
        then (Open.RemakeWindow (fetch CP.HandWindow of self)
                            (fetch Hand of self)))
    Card])

(CP.Maggie
  [LAMBDA NIL                                             (* rao "12-Apr-86 14:59")
    (OR Maggie (SETQ Maggie (create Card
                                   Suit ←(QUOTE S)
                                   Value ←(QUOTE Q])

(CP.PassIn
  [LAMBDA (self PassIn)                                   (* rao "23-Apr-86 00:06")
    (LET ((Hand (fetch Hand of self)))
      (for Card in PassIn do (Hand.AddCard Hand Card))
      (if (fetch CP.OpenHand? of self)
          then (Open.RemakeWindow (fetch CP.HandWindow of self)
                      Hand])

(CP.PassOut
  [LAMBDA (self PassDir)                                  (* rao "23-Apr-86 00:08")
    (LET ((Thoughts (fetch ThoughtWindow of self))
          (Hand (fetch Hand of self))
          (PassCards NIL)
          HighestSpade HighestHeart)
      (if PassDir
          then [SETQ PassCards
                 (for i from 1 to 3 bind HighestSpade HighestHeart HighestCard
                    collect (LET* [(PassCard (OR (CP.HasMaggie? self)
                                             (if (Card.Higher? [SETQ HighestSpade

;; ==== page 30 ====
                                                                (Card.MaxCard
                                                                  (Hand.CardsInSuit
                                                                    Hand
                                                                    (QUOTE S]
                                                              (CP.Maggie))
                                                        then     (* Found A or K of spades)
                                                             (CP.Think self
                                                                    "I will pass my highest spade, the ")
                                                             HighestSpade
                                                      elseif (Card.Higher? [SETQ HighestHeart
                                                                            (Card.MaxCard
                                                                              (Hand.CardsInSuit
                                                                                Hand
                                                                                (QUOTE H]
                                                                          (Card.Create 10 (QUOTE H)))
                                                        then     (* Found A, K, Q, or J of hearts)
                                                             (CP.Think self
                                                                    "I will pass my highest heart, the ")
                                                             HighestHeart
                                                      elseif (Hand.Singleton? Hand (QUOTE D))
                                                        then     (* Dump that single diamond!)
                                                             (CP.Think self
                                                                    "I will pass my singleton, the ")
                                                             (CAR (Hand.CardsInSuit Hand (QUOTE D)))
                                                      elseif (OR (Hand.Singleton? Hand (QUOTE C))
                                                                 (Hand.Doubleton? Hand (QUOTE C)))
                                                        then     (* Dump the club. Allow doubletons because first trick is always clubs and always safe.)
                                                             (CP.Think self
                                       "I will pass my singleton or doubleton club, the ")
                                                             (Card.MaxCard (Hand.CardsInSuit
                                                                             Hand
                                                                             (QUOTE C)))
                                                      else     (* If nothing, pick highest card in hand)
                                                           (CP.Think self
                                                                  "I will pass my highest card, the ")
                                                           (SETQ HighestCard (Card.MaxCard (Hand.Cards
                                                                                             Hand]
                            (CP.Think self (Card.PrintCard PassCard)
                                   T)
                            (Hand.RemoveCard Hand PassCard]
      (if (fetch CP.OpenHand? of self)
          then (Open.RemakeWindow (fetch CP.HandWindow of self)
                      Hand))
      PassCards])

(CP.Play
  [LAMBDA (self Trick HeartsBroken? FirstTrick?)          (* rao "22-Apr-86 21:33")
    (LET ((CardsPlayed? (fetch Cards of Trick)))
      (if (NULL CardsPlayed?)
          then                                            (* Mr. Conservative is the lead.)
               (CP.Lead self Trick HeartsBroken? FirstTrick?)
          else (CP.Follow self Trick HeartsBroken? FirstTrick?])

(CP.Start
  [LAMBDA (self)                                          (* rao "23-Apr-86 10:19")
    (replace Hand of self with NIL)
    (replace MaggiePlayed? of self with NIL)
    (if ThinkFlag?
        then (CLEARW (fetch ThoughtWindow of self])

(CP.TestPass
  [LAMBDA (self)                                          (* rao "22-Apr-86 21:35")
    (for c in (Hand.Cards (fetch Hand of self)) do (printout T (Card.PrintCard c)
                                                            ,,))   #| ?? two printout separators; render as ",," (commas); could be ".." |#
    (printout T T)
    (for c in (CP.PassOut self T) do (printout T (Card.PrintCard c)
                                             ,,])

(CP.Think
  [LAMBDA Args                                            (* rao "23-Apr-86 10:18")
    (if (OR ThinkFlag? (fetch CP.OpenHand? of self))
        then (LET [(self (ARG Args 1))
                   (PrintItems (for i from 2 to Args collect (LET ((thing (ARG Args i)))
