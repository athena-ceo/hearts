;; ==== page 1 ====
(FILECREATED " 5-May-86 02:06:24" {MITFS1-E40:SLOAN% SCHOOL:MASSINSTTECH}<RAMANA% RAO>HEART #| ?? line truncated at right margin of page |#

      changes to:  (FNS H.QueueNPs CLOWN.Create CLOWN.GiveHand HNET.Hello HNET.GoodBye Game.PrintOut
                        Hearts LHearts H.PlayGame H.Shuffle H.Deal CP.Follow Deal.SetScore
                        Hand.FaceCards Trick.CardByPlayer CT.Open Open.CreateWindow CP.Create
                        CardList.RemoveCard Trick.PlayOf HP.IconMenu HP.Create HP.GiveHand HP.PassIn
                        HP.PassOut HP.Play HP.AddCard HP.ChooseSomeCards HP.CreateWindow HP.GetName
                        HP.MakeDeck HP.MarkSelected HP.MarkUnselected HP.Menuer HP.RemakeHand
                        HP.RemoveCard HP.Repaintfn HP.Reshape HP.Select HP.SuitLength HP.Unselect
                        HP.WaitForReady TestHP H.MakePlayer H.Setup)
                   (RECORDS Deal)
                   (VARS ConservativeNames HEARTSCOMS HPMapping HIconBM HShadowBM)
      previous date: "25-Apr-86 13:46:47"
{MITFS1-E40:SLOAN% SCHOOL:MASSINSTTECH}<RAMANA% RAO>HEARTS.;54)


(* Copyright (c) 1986 by Harley Davis and Ramana Rao. All rights reserved.)

(PRETTYCOMPRINT HEARTSCOMS)

(RPAQQ HEARTSCOMS ((FNS H.IconMenu H.MakeIcon H.MakePlayer H.Setup H.QueueNPs)
        (FNS LHearts Hearts NetHearts)
        (INITVARS (H.LastGame)
                (H.GameList))
        (* * HOUSE Routines and Data Structures)
        (FNS H.Initialize H.PlayGame H.Shuffle H.Deal)
        (FNS H.Apply)
        (FNS H.GetLegals)
        (VARS OpenSelectShade OpenSelectShade2 (H.PlayerArray (ARRAY 4))
                (H.WaitingToPlay)
                H.PlayerMustOps)
        (* * Hearts Network Handler)
        (RECORDS HN.Player)
        (FNS HNET.Apply HNET.Inform HNET.Hello HNET.HelloAgain HNET.CT.Open HNET.GoodBye
                HNET.DoIWantToPlay?)
        (VARS (HNET.CTReg (QUOTE (475 390 450 400)))
                (HNET.CardTable)
                (HNET.MyPlayers)
                (HNET.Address (PORTSTRING (ETHERHOSTNUMBER)))
                HNET.ResponseOps)
        (* * CardTable Routines and Data Structures)
        (FNS CT.InformAll CT.MakeTitle CT.GiveHand CT.PassOut CT.Play CT.PrintStats CT.Trick
                CT.Results InvertRegion)
        (VARS (CT.All)
                (CT.CurrentTrick)
                CTWidth CTHeight)
        (* * Open Hand Utilities)
        (VARS OpenSelectShade OpenSelectShade2)
        (FNS Open.CreateWindow Open.MarkSelected Open.MarkUnselected Open.Print Open.RemakeWindow
                Open.Repaintfn Open.Reshape Open.SuitLength)
        (* * Dealing functions)
        (FNS Dealer.CreateWindow Dealer.Menuer Dealer.Repaintfn Dealer.Reshape Dealer.Remake
                Dealer.Select Dealer.UnSelect Dealer.Remove)
        (* * Human Player Interface)
        (VARS CY DY HPImmediatePlay HPMapping HPSelectShade HPSelectShade2 HY SY SuitLabelOffset)
        (FNS HP.Create HP.GiveHand HP.PassIn HP.PassOut HP.Play HP.Trick)
        (FNS HP.AddCard HP.ChooseSomeCards HP.CreateWindow HP.GetName HP.MakeDeck HP.MarkSelected
                HP.MarkUnselected HP.Menuer HP.RemakeHand HP.RemoveCard HP.Repaintfn HP.Reshape
                HP.Select HP.SuitLength HP.Unselect HP.WaitForReady TestHP)
        (* * Conservative Player)
        (RECORDS CP)
        (VARS ConservativeNames CPMapping Maggie ThinkFlag?)
        (FNS CP.Create CP.Follow CP.GetCards CP.GiveHand CP.HasMaggie? CP.HighSpades CP.Lead
                CP.LoseCard CP.Maggie CP.PassIn CP.PassOut CP.Play CP.Start CP.TestPass CP.Think
                CP.Trick CPTest CP.Results)
        (* * House Clown)
        (RECORDS Clown)
        (FNS CLOWN.Create CLOWN.GiveHand CLOWN.PassOut CLOWN.PassIn CLOWN.Play)
        (* * DATA Structures)
        (RECORDS Game Player Deal Card Hand Trick)
        (VARS CardValues SuitValues Game.OverScore (Player.Array (ARRAY 4)))
        (FNS Game.Update Game.Winner Game.PrintOut)

;; ==== page 2 ====
        (FNS PlayerLoc PlayerNum Player?.Record Player?.Number PlayerNum.Increment PlayerNum.Plus
                PlayerNum.Difference)
        (FNS Deal.SetScore)
        (* * Card Functions)
        (FNS Card.Better? Card.Create Card.CreateBM Card.CreateDeck Card.Equal? Card.EqualVal?
                Card.Higher? Card.Lower? Card.MaxCard Card.MinCard Card.Number Card.Print Card.Value
                Card.ValueSublist Card.Suit CardList.HigherCards CardList.LowerCards
                CardList.SecondHighest CardList.HighSpades? CardList.CardsOfSuit CardList.Member
                CardList.Sort CardList.EliminateSuit CardList.CardsOfSuits CardList.PointCards
                CardList.RemoveCard CardList.ShortestSuit Card.NotEqual? CardList.BridgePoints)
        (VARS CardGap CardHeight CardWidth)
        (INITVARS (Card.BMCache (ARRAY 52)))
        (* * Hand Functions)
        (FNS Hand.AddCard Hand.Cards Hand.CardsInSuit Hand.Create Hand.Doubleton? Hand.FaceCards
                Hand.MaxCard Hand.Member? Hand.MinCard Hand.FaceCards Hand.NumberInSuit Hand.RemoveCard
                Hand.RemoveCards Hand.SetSuit Hand.Singleton? Hand.Sort Hand.Void?)
        (* * Trick Functions)
        (FNS Trick.Cards Trick.LeadCard Trick.LeadSuit Trick.OrderCards Trick.Play Trick.PlayerByCard
                Trick.Points Trick.SetWinner Trick.Leader Trick.PlayOf Trick.WhoPlayed
                Trick.CardByPlayer Trick.Winner Trick.WinnerSoFar)
        (* * Random Cruff)
        (FNS Not.Null)
        (BITMAPS CardOutline ClubsBits DiamondsBits HeartsBits SpadesBits HIconBM HShadowBM)
        (FILES {LISP:}<LispLibrary>INTERMEZZO>EVALSERVER.DCOM
                {LISP:}<LispUsers>INTERMEZZO>ACTIVEREGIONS.DCOM)
        (DECLARE: DONTEVAL@LOAD DOEVAL@COMPILE DONTCOPY COMPILERVARS (ADDVARS (NLAMA)
                                                                            (NLAML)
                                                                            (LAMA CP.Think H.Apply))
                )
        (P (H.MakeIcon))))
(DEFINEQ

(H.IconMenu
  [LAMBDA (Win)                                              (* rao "4-May-86 23:50")
    (MENU (create MENU
                ITEMS ←[QUOTE (["Play Game" (ADD.PROCESS (LIST (QUOTE LHearts)
                                                               (KWOTE (WINDOWPROP Win (QUOTE Config)
                                                                             ))
                                                               (WINDOWPROP Win (QUOTE Open?))
                                                               (WINDOWPROP Win (QUOTE ManualDeal?)]
                              ("Set Up Game" (H.Setup Win))
                              ("Queue Net Players" (H.QueueNPs Win))
                              ["Print Last Game"
                                (Game.PrintOut H.LastGame
                                       (MENU (create MENU
                                                    ITEMS ←[QUOTE
                                                              (("Terminal" T)
                                                                ("File HGAME.OUT"
                                                                  (OPENSTREAM (QUOTE HGAME.OUT)
                                                                         (QUOTE APPEND]
                                                    TITLE ← "Print Game To..."]
                              ("List Rules" (PROGN (ListRules (QUOTE HRULES.OUT))
                                                   (CLOSEALL)))
                              ("Kill Experts" (KillExperts))
                              ("View Current Configuration" (printout T "Players: "
                                                                    (WINDOWPROP Win
                                                                           (QUOTE Config))
                                                                    T "Open? :"
                                                                    (WINDOWPROP Win
                                                                           (QUOTE Open?))
                                                                    ": Manual Deal? :"
                                                                    (WINDOWPROP Win
                                                                           (QUOTE
                                                                            ManualDeal?))
                                                                    ":" T]
                TITLE ← "Let's play Hearts!"
                MENUFONT ←(QUOTE (HELVETICA 10 (QUOTE BRR])

(H.MakeIcon
  [LAMBDA NIL                                                (* hed "4-May-86 14:58")
    (WINDOWPROP (ICONW HIconBM HShadowBM)
           (QUOTE BUTTONEVENTFN)
           (FUNCTION H.IconMenu])

;; ==== page 3 ====
(H.MakePlayer
  [LAMBDA (Type Open?)                                       (* rao "4-May-86 22:48")
    (SELECTQ Type
        ((QUOTE EP)
          (UNITMSG (QUOTE expert.players)
                 (QUOTE Create)
                 Open?))
        ((QUOTE CP)
          (CP.Create Open?))
        ((QUOTE HP)
          (HP.Create))
        ((QUOTE CLOWN)
          (CLOWN.Create))
        (SHOULDNT (CONCAT "Illegal player type: " Type " (Legals are: EP, CP, HP, CLOWN) "])

(H.Setup
  [LAMBDA (Win)                                              (* rao "4-May-86 23:11")
    (WINDOWPROP Win (QUOTE Config)
           (bind val vals for i from 1 to 4
              do [SETQ val (MENU (create MENU
                                        ITEMS ←(QUOTE (("Expert Player" (QUOTE EP))
                                                        ("Conservative Player" (QUOTE CP))
                                                        ("Human Player" (QUOTE HP))
                                                        ("Clown (Blah)" (QUOTE CLOWN))
                                                        ("Get Rest from Net" NIL)))
                                        TITLE ←(CONCAT "Type of player " i)
                                        MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
                 (if val
                     then (SETQ vals (NCONC1 vals val))
                   else (RETURN vals))
              finally (RETURN vals)))
    [WINDOWPROP Win (QUOTE Open?)
           (MENU (create MENU
                        ITEMS ←(QUOTE (("Yes" T)
                                        ("No" NIL)))
                        TITLE ← "Play Open Hand?"
                        MENUCOLUMNS ← 2
                        MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
    [WINDOWPROP Win (QUOTE ManualDeal?)
           (MENU (create MENU
                        ITEMS ←(QUOTE (("Yes" T)
                                        ("No" NIL)))
                        TITLE ← "Deal Manually?"
                        MENUCOLUMNS ← 2
                        MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
    (if [MENU (create MENU
                     ITEMS ←(QUOTE (("Yes" T)
                                     ("No" NIL)))
                     TITLE ← "Play Now?"
                     MENUCOLUMNS ← 2
                     MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
        then (ADD.PROCESS (LIST (QUOTE LHearts)
                                (KWOTE (WINDOWPROP Win (QUOTE Config)))
                                (WINDOWPROP Win (QUOTE Open?))
                                (WINDOWPROP Win (QUOTE ManualDeal?])

(H.QueueNPs
  [LAMBDA (Win)                                              (* hed "5-May-86 01:38")
    (bind [Open? ←(WINDOWPROP Win (QUOTE Open?)
                        (MENU (create MENU
                                     ITEMS ←(QUOTE (("Yes" T)
                                                     ("No" NIL)))
                                     TITLE ← "Play Open Hand?"
                                     MENUCOLUMNS ← 2
                                     MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
          val vals for i from 1
       do [val ←(MENU (create MENU
                             ITEMS ←(QUOTE (("Expert Player" (UNITMSG (QUOTE expert.players)
                                                                    (QUOTE Create)
                                                                    Open?))
                                             ("Conservative Player" (CP.Create Open?))
                                             ("Human Player" (HP.Create))
                                             ("Clown (Blah)" (CLOWN.Create))
                                             ("STOP" NIL)))

;; ==== page 4 ====
                                     TITLE ←(CONCAT "Type of player " i)
                                     MENUFONT ←(QUOTE (GACHA 10 (QUOTE BOLD]
          (if val
              then (SETQ vals (NCONC1 vals val))
            else (RETURN (NetHearts vals])
)
(DEFINEQ

(LHearts
  [LAMBDA (Config Open? ManualDeal?)                         (* rao "4-May-86 23:15")
    (LET [(Config (OR Config (QUOTE (EP EP EP EP]
         (bind (Players ←(for XP in Config collect (H.MakePlayer XP Open?)))
            do (Hearts Players Open? ManualDeal?)
               (SETQ H.GameList (NCONC1 H.GameList H.LastGame])

(Hearts
  [LAMBDA (Players Open? ManualDeal?)                        (* rao "4-May-86 23:16")
    (LET NIL
        (H.Initialize)
        [if (OR (NOT Players)
                (ILESSP (LENGTH Players)
                       4))
            then [SETQ Players (NCONC Players (HNET.Hello (PLUS (LENGTH Players)
                                                                1]
                 (SETQ Players (NCONC Players (for PlayerNum from (IPLUS (LENGTH Players)
                                                                         1)
                                                 to 4 collect (CP.Create Open?]
        (for Player in Players as i from 1 do (replace Number of Player with i))
        (HNET.HelloAgain Players)
        (push CT.All (CT.Open Players))
        (H.PlayGame Players ManualDeal?])

(NetHearts
  [LAMBDA (Players)                                          (* rao "15-Apr-86 20:26")
    (EVALSERVER)
    (for P in Players do (SETQ H.WaitingToPlay (NCONC1 H.WaitingToPlay P])
)

(RPAQ? H.LastGame )

(RPAQ? H.GameList )

;; ==== page 5 ====
(* * HOUSE Routines and Data Structures)

(DEFINEQ

(H.Initialize
  [LAMBDA NIL                                                (* rao "15-Apr-86 19:22")
    (HNET.GoodBye)
    (SETQ CT.All])

(H.PlayGame
  [LAMBDA (Players ManualDeal?)                              (* hed "30-Apr-86 00:00")

        (* * Game Administration)


    (LET ((Deck (Card.CreateDeck))
          (Pass (QUOTE Left))
          (Game (create Game
                       Players ← Players
                       Score ←(LIST 0 0 0 0)))
          (LeadCard (Card.Create 2 (QUOTE C)))
          OriginalHands)
         (SETQ H.LastGame Game)
         (for Player in Players as i from 1
            do (replace Number of Player with i)
               (SETA Player.Array i Player))
         [bind Deal until (Game.Winner Game)
            do

               (* * Next Deal)


               (SETQ Deck (Card.CreateDeck))
               (H.Shuffle Deck ManualDeal?)
               (SETQ Deal (H.Deal Players Pass Deck))
               (SETQ OriginalHands (fetch D.RealHands of Deal))

               (* * Play Deal)


               (replace Tricks of Deal
                  with (bind [Lead ←(for i from 1 to 4 Hand in OriginalHands
                                       thereis (CardList.Member LeadCard (Hand.Cards Hand]
                             (HeartsBroken? ← NIL)
                             LastCard for TrickNum from 1 to 13
                          collect (SETQ Trick (create Trick
                                                     Cards ← NIL
                                                     LeadPlayerNum ← Lead))
                                                            (* Play Trick)
                                  (bind (PlayerNum ← Lead)
                                        Player
                                     do (SETQ Player (ELT Player.Array PlayerNum))
                                        [Trick.Play Trick (SETQ LastCard (H.Apply Player (QUOTE Play)
                                                                               Trick HeartsBroken?
                                                                               (EQP TrickNum 1]
                                        (if (AND (NOT HeartsBroken?)
                                                 (EQUAL (fetch Suit of LastCard)
                                                        (QUOTE H)))
                                            then (SETQ HeartsBroken? T))
                                        (SETQ PlayerNum (PlayerNum.Increment PlayerNum))
                                     repeatwhile (NEQ PlayerNum Lead) finally (SETQ Lead (
                                                                                    Trick.SetWinner Trick))
                                        )                   (* Inform Players of Trick Result)
                                  (for Player in Players do (H.Apply Player (QUOTE Trick)
                                                                  Trick))
                                  Trick))
               (Deal.SetScore Deal)

               (* * Update Variables)


               (Game.Update Game Deal)
               (for Player in Players do (H.Apply Player (QUOTE Results)
                                               (fetch Score of Game)))

;; ==== page 6 ====
               (SETQ Pass (CDR (FASSOC Pass (QUOTE ((Left . Across)
                                                     (Across . Right)
                                                     (Right)
                                                     (NIL . Left]
         T])

(H.Shuffle
  [LAMBDA (Deck ManualDeal?)                                 (* rao "29-Apr-86 20:50")
    (if ManualDeal?
        then [LET ((DealWin (Dealer.CreateWindow Deck)))
                  (while (WINDOWPROP DealWin (QUOTE NotReady)) do (DISMISS 2000))
                  finally (RETURN (WINDOWPROP DealWin (QUOTE Deck]
      else (first (RANDSET T) bind X Y TEMP for i from 1 to 100
              do (SETQ X (RAND 1 52))
                 (SETQ Y (RAND 1 52))
                 (SETQ TEMP (ELT Deck X))
                 (SETA Deck X (ELT Deck Y))
                 (SETA Deck Y TEMP)
              finally (RETURN Deck])

(H.Deal
  [LAMBDA (Players Pass Deck)                                (* rao "29-Apr-86 02:04")

        (* * comment)


    (LET ((Deal (create Deal
                       D.Score ←(LIST 0 0 0 0)
                       D.CumScore ←(LIST 0 0 0 0)
                       PassDir ← Pass)))
         (replace D.RealHands of Deal
            with (bind Hand for PlayerNum from 1 to 4 as Player in Players
                    collect                             (* First player gets first 13 cards of deck, etc.)
                            (SETQ Hand (Hand.Create (for j from (ADD1 (TIMES (SUB1 PlayerNum)
                                                                            13))
                                                       to (TIMES PlayerNum 13) collect (ELT Deck j))
                                              Player))
                            (H.Apply Player (QUOTE GiveHand)
                                   Hand PlayerNum))
                    Hand))
         (replace Hands of Deal with (COPY (fetch D.RealHands of Deal)))
         (bind Passes for Player in Players do (SETQ Passes (NCONC1 Passes (H.Apply Player (QUOTE
                                                                                       PassOut)
                                                                                   Pass)))
            finally (replace PassOut of Deal with Passes)
                    (if Pass
                        then [SETQ Passes (for i in (SELECTQ Pass
                                                        ((QUOTE Left)
                                                          (QUOTE (4 1 2 3)))
                                                        ((QUOTE Across)
                                                          (QUOTE (3 4 1 2)))
                                                        ((QUOTE Right)
                                                          (QUOTE (2 3 4 1)))
                                                        (SHOULDNT))
                                             collect (CAR (NTH Passes i]
                             (for PassIn in Passes as Player in Players do (H.Apply Player (QUOTE PassIn)
                                                                                  PassIn))
                             (replace PassIn of Deal with Passes)))
         Deal])
)
(DEFINEQ

(H.Apply
  [LAMBDA Args                                               (* rao "15-Apr-86 16:29")

        (* * comment)


    (LET ((Player (ARG Args 1))
          (Op (ARG Args 2))
          (OpArgs (for i from 3 to Args collect (ARG Args i)))
          RetVal Fcn)
         (SETQ RetVal (SELECTQ (fetch Type of Player)
                          ((QUOTE Lisp)
