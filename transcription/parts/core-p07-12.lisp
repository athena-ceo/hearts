;; ==== page 7 ====
                              [SETQ Fcn (CDR (FASSOC Op (fetch Mapping of Player]
                              (if Fcn
                                  then (APPLY Fcn (CONS (fetch Object of Player)
                                                       OpArgs))
                                elseif (FMEMB Op H.PlayerMustOps)
                                  then (SHOULDN'T)))
                          ((QUOTE Kee)
                           (UNITMSG* (fetch Object of Player)
                                  Op OpArgs))
                          [(QUOTE Net)
                            (if (FMEMB Op HNET.ResponseOps)
                                then (REMOTEVAL (LIST (FUNCTION HNET.Apply)
                                                     (KWOTE (fetch Number of Player))
                                                     (KWOTE Op)
                                                     (KWOTE OpArgs))
                                              (fetch HNP.Host of (fetch Object of Player]
                          (SHOULDNT)))
       (CT.InformAll Player Op OpArgs RetVal)
       RetVal])
)
(DEFINEQ

(H.GetLegals
  [LAMBDA (Hand Trick HeartsBroken? FirstTrick?)               (* rao "23-Apr-86 10:23")
    (LET ((LeadCard (Trick.LeadCard Trick))
          Possibilities)
      (OR (if LeadCard
              then (if (Hand.Void? Hand (fetch Suit of LeadCard))
                       then (if FirstTrick?
                                then [for card in (Hand.Cards Hand) collect card
                                          unless (OR (EQUAL (Card.Suit card)
                                                            (QUOTE H))
                                                     (Card.Equal? card (CP.Maggie]
                                else (Hand.Cards Hand))
                     else (Hand.CardsInSuit Hand (fetch Suit of LeadCard)))
            elseif FirstTrick?
              then (OR [LIST (CardList.Member (Card.Create 2 (QUOTE C))
                                             (Hand.CardsInSuit Hand (QUOTE C]
                       (SHOULDNT "Leader of first trick does not have the 2 of clubs."))
            elseif HeartsBroken?
              then (Hand.Cards Hand)
            else (CardList.EliminateSuit (Hand.Cards Hand)
                                        (QUOTE H)))
          (Hand.Cards Hand])
)

(RPAQQ OpenSelectShade 10260)

(RPAQQ OpenSelectShade2 49731)

(RPAQ H.PlayerArray (ARRAY 4))

(RPAQ H.WaitingToPlay NIL)

(RPAQQ H.PlayerMustOps (GiveHand PassOut PassIn Play))

;; ==== page 8 ====
(* * Hearts Network Handler)

[DECLARE: EVAL@COMPILE

(RECORD HN.Player (HNP.Name HNP.Host))
]
(DEFINEQ

(HNET.Apply
  [LAMBDA (Player Op OpArgs)                                   (* rao "15-Apr-86 17:38")

         (* * comment)


    (LET ((Player (Player?.Record Player))
          RetVal Fcn)
      (SELECTQ (fetch Type of Player)
          ((QUOTE Lisp)
            [SETQ Fcn (CDR (FASSOC Op (fetch Mapping of Player]
            (if Fcn
                then (APPLY Fcn (CONS (fetch Object of Player)
                                     OpArgs))
              elseif (FMEMB Op H.PlayerMustOps)
                then (SHOULDN'T)))
          ((QUOTE Kee)
            (UNITMSG* (fetch Object of Player)
                  Op OpArgs))
          (SHOULDNT])

(HNET.Inform
  [LAMBDA (PlayerNum Op OpArgs RetVal)                         (* rao "15-Apr-86 22:08")
    (SELECTQ Op
        ((QUOTE Play)
          (CT.Play HNET.CardTable PlayerNum RetVal))
        ((QUOTE GiveHand)
          (CT.GiveHand HNET.CardTable))
        ((QUOTE Trick)
          (CT.Trick HNET.CardTable (CAR OpArgs)))
        ((QUOTE PassOut)
          (CT.PassOut HNET.CardTable (CAR OpArgs)))
        ((QUOTE PassIn))
        ((QUOTE Results)
          (CT.Results HNET.CardTable (CAR OpArgs)))
        (SHOULDNT))
    (if (AND (ELT Player.Array PlayerNum)
             (NOT (FMEMB Op HNET.ResponseOps)))
        then (if (FMEMB Op (QUOTE (GiveHand PassIn)))
                 then (HNET.Apply PlayerNum Op OpArgs)
               else (for Player in HNET.MyPlayers do (HNET.Apply Player Op OpArgs])

(HNET.Hello
  [LAMBDA (StartNumber)                                        (* hed " 5-May-86 01:59")
    (bind HNETPlayers New (PlayerNum ← StartNumber)
       while [AND (ILESSP PlayerNum 5)
                  (SETQ New (CAR (NLSETQ (REMOTEVAL (LIST (FUNCTION HNET.DoIWantToPlay?)
                                                         (KWOTE PlayerNum))
                                                  NIL T 3000]
       do (SETQ HNETPlayers (NCONC HNETPlayers New))
          (SETQ PlayerNum (IPLUS PlayerNum (LENGTH New)))
          (SETQ CT.All (NCONC1 CT.All (fetch HNP.Host of (CAR New]
       finally (RETURN (for P in HNETPlayers collect (create Player
                                                          Name ←(fetch HNP.Name of P)
                                                          Type ←(QUOTE Net)
                                                          Object ← P])

(HNET.HelloAgain
  [LAMBDA (Players)                                            (* rao "15-Apr-86 20:49")
    (for Host in CT.All unless (WINDOWP Host) do (REMOTEVAL (LIST (QUOTE HNET.CT.Open)
                                                                 (KWOTE Players))
                                                          Host 0])

(HNET.CT.Open
  [LAMBDA (Players)                                            (* rao "15-Apr-86 20:50")
    (SETQ HNET.CardTable (CT.Open Players HNET.CTReg])

;; ==== page 9 ====
(HNET.GoodBye
  [LAMBDA NIL                                                  (* hed " 5-May-86 01:39")
    (for Host in CT.All unless (WINDOWP Host) do (NLSETQ (REMOTEVAL (LIST (QUOTE SETQ)
                                                                        (QUOTE HNET.MyPlayers))
                                                                 Host 0 3000])

(HNET.DoIWantToPlay?
  [LAMBDA (PlayerNum)                                          (* rao "20-Apr-86 17:21")
    (if HNET.MyPlayers
        then (DISMISS 3000)
             NIL
      else (SETQ Player.Array (ARRAY 4))
           (for Player in H.WaitingToPlay as PN from PlayerNum while (LEQ PN 4)
              collect (replace Number of Player with PN)
                      (SETA Player.Array PN Player)
                      (SETQ HNET.MyPlayers (NCONC1 HNET.MyPlayers Player))
                      (SETQ H.WaitingToPlay (REMOVE Player H.WaitingToPlay))
                      (create HN.Player
                          HNP.Name ←(fetch Name of Player)
                          HNP.Host ← HNET.Address])
)

(RPAQQ HNET.CTReg (475 390 450 400))

(RPAQQ HNET.CardTable NIL)

(RPAQQ HNET.MyPlayers NIL)

(RPAQ HNET.Address (PORTSTRING (ETHERHOSTNUMBER)))

(RPAQQ HNET.ResponseOps (PassOut Play))

;; ==== page 10 ====
(* * CardTable Routines and Data Structures)

(DEFINEQ

(CT.InformAll
  [LAMBDA (Player Op OpArgs RetVal)                            (* rao "15-Apr-86 19:44")
    (if (OR (FMEMB Op (QUOTE (Play GiveHand PassIn)))
            (EQP (fetch Number of Player)
                 1))
        then (for CT in CT.All do (if (WINDOWP CT)
                                      then (SELECTQ Op
                                               ((QUOTE Play)
                                                 (CT.Play CT Player RetVal))
                                               ((QUOTE Trick)
                                                 (CT.Trick CT (CAR OpArgs)))
                                               ((QUOTE PassOut)
                                                 (CT.PassOut CT (CAR OpArgs)))
                                               ((QUOTE PassIn))
                                               ((QUOTE GiveHand)
                                                 (CT.GiveHand CT))
                                               ((QUOTE Results)
                                                 (CT.Results CT (CAR OpArgs)))
                                               (SHOULDNT))
                                    else (REMOTEVAL (LIST (FUNCTION HNET.Inform)
                                                         (KWOTE (fetch Number of Player))
                                                         (KWOTE Op)
                                                         (KWOTE OpArgs)
                                                         (KWOTE RetVal))
                                                  CT 0])

(CT.Open
  [LAMBDA (Players Reg)                                        (* hed " 4-May-86 16:25")
    (LET* ((Win (CREATEW (OR Reg (GETBOXREGION CTWidth CTHeight NIL NIL NIL
                                       "Please position the Card Table."))
                         "Hearts Card Table"))
           Name1 Name2 Name3 Name4 DS)
      (for Player in Players as N in (QUOTE (Name1 Name2 Name3 Name4))
         do (SET N (fetch Name of Player)))
      (SETQ DS (WINDOWPROP Win (QUOTE DSP)))
      (WINDOWPROP Win (QUOTE Score)
             (QUOTE (0 0 0 0)))
      (WINDOWPROP Win (QUOTE Tricks)
             (QUOTE (0 0 0 0)))
      (WINDOWPROP Win (QUOTE Delay)
             2000)
      (WINDOWPROP Win (QUOTE NumTricks)
             0)
      (CT.MakeTitle Win)

         (* * Layout All Positions)


      (SETQ CT.X1 (DIFFERENCE (QUOTIENT CTWidth 2)
                             (QUOTIENT (STRINGWIDTH Name1 (QUOTE (TIMESROMAN 12 BOLD)))
                                    2)))
      (SETQ CT.Y1 (DIFFERENCE CTHeight 35))
      (SETQ CT.X2 (DIFFERENCE [DIFFERENCE CTWidth (STRINGWIDTH Name2 (QUOTE (TIMESROMAN 12 BOLD]
                             15))
      (SETQ CT.Y2 (QUOTIENT CTHeight 2))
      (SETQ CT.X3 (DIFFERENCE (QUOTIENT CTWidth 2)
                             (QUOTIENT (STRINGWIDTH Name3 (QUOTE (TIMESROMAN 12 BOLD)))
                                    2)))
      (SETQ CT.Y3 2)
      (SETQ CT.X4 2)
      (SETQ CT.Y4 CT.Y2)

         (* * Card Positions)


      (SETQ CT.LeftX (DIFFERENCE (QUOTIENT CTWidth 2)
                                (TIMES 2 CardWidth)))
      (SETQ CT.MidX (DIFFERENCE (QUOTIENT CTWidth 2)
                               (QUOTIENT CardWidth 2)))
      (SETQ CT.RightX (PLUS (QUOTIENT CTWidth 2)

;; ==== page 11 ====
                                  CardWidth))
      (SETQ CT.TopY (PLUS (QUOTIENT CTHeight 2)
                         CardHeight))
      (SETQ CT.MidY (DIFFERENCE (QUOTIENT CTHeight 2)
                               (QUOTIENT CardHeight 2)))
      (SETQ CT.BottomY (DIFFERENCE (QUOTIENT CTHeight 2)
                                  (TIMES 2 CardHeight)))

         (* * Print names of players in window)


      (DSPFONT (QUOTE (TIMESROMAN 12 BOLD))
             DS)
      (MOVETO CT.X1 CT.Y1 DS)
      (WINDOWPROP Win (QUOTE Name1Reg)
             (STRINGREGION Name1 Win))
      (printout DS Name1)
      (MOVETO CT.X2 CT.Y2 DS)
      (WINDOWPROP Win (QUOTE Name2Reg)
             (STRINGREGION Name2 Win))
      (printout DS Name2)
      (MOVETO CT.X3 CT.Y3 DS)
      (WINDOWPROP Win (QUOTE Name3Reg)
             (STRINGREGION Name3 Win))
      (printout DS Name3)
      (MOVETO CT.X4 CT.Y4 DS)
      (WINDOWPROP Win (QUOTE Name4Reg)
             (STRINGREGION Name4 Win))
      (printout DS Name4)
      (CT.PrintStats Win)

         (* * Return the window)


      Win])

(CT.MakeTitle
  [LAMBDA (Window Pass)                                        (* rao "10-Apr-86 22:30")
    (WINDOWPROP Window (QUOTE TITLE)
           (APPLY (FUNCTION CONCAT)
                  (LIST "Hearts Card Table - " "Score: " (WINDOWPROP Window (QUOTE Score))
                        (if Pass
                            then (CONCAT " Pass: " Pass)
                          else ""])

(CT.GiveHand
  [LAMBDA (Win)                                                (* rao "15-Apr-86 21:37")
    (WINDOWPROP Win (QUOTE Tricks)
           (QUOTE (0 0 0 0)))
    (CT.PrintStats Win])

(CT.PassOut
  [LAMBDA (Window Pass)                                        (* rao "15-Apr-86 16:47")
    (CT.MakeTitle Window Pass])

(CT.Play
  [LAMBDA (Window Player Card)                                 (* rao "15-Apr-86 22:24")
    (WITH.MONITOR CT.TrickMonitor (LET (X Y)
                     (SELECTQ (Player?.Number Player)
                         (1 (SETQ X CT.MidX)
                            (SETQ Y CT.TopY))
                         (2 (SETQ X CT.RightX)
                            (SETQ Y CT.MidY))
                         (3 (SETQ X CT.MidX)
                            (SETQ Y CT.BottomY))
                         (4 (SETQ X CT.LeftX)
                            (SETQ Y CT.MidY))
                         (SHOULDNT))
                     (BITBLT (Card.CreateBM Card)
                            0 0 Window X Y CardWidth CardHeight (QUOTE INPUT)
                            (QUOTE REPLACE])

(CT.PrintStats
  [LAMBDA (Win)                                                (* rao "14-Apr-86 18:52")

;; ==== page 12 ====
         (* * Prints score and number of tricks for each player.)


    (PROG [(DS (WINDOWPROP Win (QUOTE DSP)))
           (Tricks (WINDOWPROP Win (QUOTE Tricks)))
           (Score (WINDOWPROP Win (QUOTE Score]
          (DSPFONT (QUOTE (GACHA 10 BOLD))
                 DS)
          (MOVETO CT.X1 (DIFFERENCE CT.Y1 12)
                 DS)
          (printout DS "S: " (CAR Score)
                 " T: "
                 (CAR Tricks)
                 "  ")
          (MOVETO CT.X2 (DIFFERENCE CT.Y2 12)
                 DS)
          (printout DS "S: " (CADR Score)
                 " T: "
                 (CADR Tricks)
                 "  ")
                                                              (* Exception: 3rd player's stuff goes above his name)
          (MOVETO CT.X3 (PLUS CT.Y3 15)
                 DS)
          (printout DS "S: " (CADDR Score)
                 " T: "
                 (CADDR Tricks)
                 "  ")
          (MOVETO CT.X4 (DIFFERENCE CT.Y4 12)
                 DS)
          (printout DS "S: " (CADDDR Score)
                 " T: "
                 (CADDDR Tricks)
                 "  ")
          (RETURN Win])

(CT.Trick
  [LAMBDA (Win Trick)                                          (* rao "15-Apr-86 22:25")
    (WITH.MONITOR CT.TrickMonitor (LET ((DS (WINDOWPROP Win (QUOTE DSP)))
                     WinReg WinNum TrickStats)

         (* * Only called on first time)


                     (SETQ TrickStats (WINDOWPROP Win (QUOTE Tricks)))
                     (SETQ WinNum (fetch Winner of Trick))
                     [WINDOWPROP Win (QUOTE Tricks)
                            (SELECTQ WinNum
                                (1 (APPEND (LIST (ADD1 (CAR TrickStats)))
                                          (CDR TrickStats)))
                                (2 (APPEND (LIST (CAR TrickStats))
                                          (LIST (ADD1 (CADR TrickStats)))
                                          (CDDR TrickStats)))
                                (3 (APPEND (LIST (CAR TrickStats))
                                          (LIST (CADR TrickStats))
                                          (LIST (ADD1 (CADDR TrickStats)))
                                          (CDDDR TrickStats)))
                                [4 (LIST (CAR TrickStats)
                                         (CADR TrickStats)
                                         (CADDR TrickStats)
                                         (ADD1 (CAR (CDDDR TrickStats]
                                (SHOULDNT (CONCAT "Illegal Winner Number: " WinNum]
                     (CT.PrintStats Win)
                     [SETQ WinReg (WINDOWPROP Win (SELECTQ WinNum
                                                     (1 (QUOTE Name1Reg))
                                                     (2 (QUOTE Name2Reg))
                                                     (3 (QUOTE Name3Reg))
                                                     (4 (QUOTE Name4Reg))
                                                     (SHOULDNT (CONCAT "Illegal winner region: "
                                                                     WinReg]
                     (InvertRegion Win WinReg)
                     (DISMISS (WINDOWPROP Win (QUOTE Delay)))
                     (InvertRegion Win WinReg)
                     (DSPFILL (CREATEREGION CT.MidX CT.TopY CardWidth CardHeight)
                            WHITESHADE
