;; ==== page 13 ====
                                    (QUOTE REPLACE)
                                    DS)
                        (DSPFILL (CREATEREGION CT.RightX CT.MidY CardWidth CardHeight)
                                 WHITESHADE
                                 (QUOTE REPLACE)
                                 DS)
                        (DSPFILL (CREATEREGION CT.MidX CT.BottomY CardWidth CardHeight)
                                 WHITESHADE
                                 (QUOTE REPLACE)
                                 DS)
                        (DSPFILL (CREATEREGION CT.LeftX CT.MidY CardWidth CardHeight)
                                 WHITESHADE
                                 (QUOTE REPLACE)
                                 DS])

(CT.Results
  [LAMBDA (Window Score)                                       (* rao "15-Apr-86 16:49")
    (WINDOWPROP Window (QUOTE Score)
                Score)
    (CT.MakeTitle Window])

(InvertRegion
  [LAMBDA (Win Reg)                                            (* rao "11-Apr-86 17:58")
    (ACTIVEREGIONS/DEFAULTHIGHLIGHTFN Win (create ACTIVEREGION
                                                  REGION ← Reg])
)

(RPAQ CT.TrickMonitor (CREATE.MONITORLOCK (QUOTE CT.Trick)))

(RPAQQ CT.All NIL)

(RPAQQ CT.CurrentTrick NIL)

(RPAQQ CTWidth 450)

(RPAQQ CTHeight 400)

;; ==== page 14 ====
(* * Open Hand Utilities)


(RPAQQ OpenSelectShade 10260)

(RPAQQ OpenSelectShade2 49731)
(DEFINEQ

(Open.CreateWindow
  [LAMBDA (PlayerName Type)                                    (* hed "5-May-86 00:15")
    (PROG ([Win (CREATEW (GETBOXREGION 300 245 NIL NIL NIL (CONCAT
                                                             "Position for the interface window of "
                                                                    PlayerName))
                         (CONCAT "Hearts window for " (OR Type "")
                                 " "
                                 (OR PlayerName (SETQ PlayerName (PromptRead "What is your name? "
                                                                            NIL T]
           TextWin DS)
          (SETQ DS (WINDOWPROP Win (QUOTE DSP)))

          (* * Print names of suits in window)


          (DSPFONT (QUOTE (TIMESROMAN 12 BOLD))
                   DS)
          (for suit in (QUOTE (Clubs: Diamonds: Hearts: Spades:)) as i from 0 to 3
             do (MOVETO 2 (DIFFERENCE 176 (TIMES i 50))
                        DS)
                (printout DS suit))

          (* * Add Text Window)


          (GETPROMPTWINDOW Win 5 (QUOTE (HELVETICA 8)))
          [SETQ OWinHeight (PLUS 245 (fetch HEIGHT of (WINDOWPROP (GETPROMPTWINDOW Win)
                                                                  (QUOTE REGION]

          (* * Add appropriate window properties)


          (for Prop in (QUOTE (CardMap Hand SelectedCards)) do (WINDOWPROP Win Prop NIL))
          (WINDOWPROP Win (QUOTE Name)
                      PlayerName)
          (WINDOWADDPROP Win (QUOTE REPAINTFN)
                         (FUNCTION Open.Repaintfn))
          (WINDOWADDPROP Win (QUOTE RESHAPEFN)
                         (FUNCTION RESHAPEBYREPAINTFN))
          (WINDOWPROP Win (QUOTE TextWindow)
                      TextWin)

          (* * Return the window)


          (RETURN Win])

(Open.MarkSelected
  [LAMBDA (HWin CardReg Shade2?)                               (* rao "17-Apr-86 13:04")
    (DSPFILL CardReg (if Shade2?
                         then OpenSelectShade2
                       else OpenSelectShade)
             (QUOTE PAINT)
             (WINDOWPROP HWin (QUOTE DSP])

(Open.MarkUnselected
  [LAMBDA (HWin CardReg CardBM)                                (* rao "10-Apr-86 19:24")
    (BITBLT CardBM 0 0 HWin (fetch LEFT of CardReg)
            (fetch BOTTOM of CardReg)
            CardWidth CardHeight (QUOTE INPUT)
            (QUOTE REPLACE])

(Open.Print
  [LAMBDA (Win Text SameLine?)                                 (* rao "23-Apr-86 09:57")
    (if SameLine?
        then (printout (WINDOWPROP (GETPROMPTWINDOW Win)

;; ==== page 15 ====
                                   (QUOTE DSP))
                Text)
      else (printout (WINDOWPROP (GETPROMPTWINDOW Win)
                                 (QUOTE DSP))
                  Text T])

(Open.RemakeWindow
  [LAMBDA (HWin Hand)                                          (* rao "17-Apr-86 13:17")
    (Hand.Sort Hand)
    (PROG ((Cards (Hand.Cards Hand))
           (ND 0)
           (NC 0)
           (NH 0)
           (NS 0)
           (CardMap NIL)
           ARList)
          (WINDOWPROP HWin (QUOTE Hand)
                      Hand)
          (SETQ ARList (for C in Cards collect (LET ((Suit (fetch Suit of C))
                                                     NewAR CReg CountVar CardBM)
                                                    (SETQ CountVar (PACK* (QUOTE N)
                                                                          Suit))
                                                    (SETQ CReg (CREATEREGION (Open.SuitLength
                                                                              (EVAL CountVar))
                                                                             (EVAL (PACK* Suit
                                                                                          (QUOTE Y)))
                                                                             CardWidth CardHeight))
                                                    (SET CountVar (ADD1 (EVAL CountVar)))
                                                    (SETQ CardBM (Card.CreateBM C))
                                                    (SETQ NewAR (create ACTIVEREGION
                                                                        REGION ← CReg
                                                                        DATA ←(LIST C CardBM)))
                                                    [SETQ CardMap
                                                      (APPEND CardMap (LIST (LIST C CardBM CReg NewAR]
                                                    NewAR)))    (* (SETACTIVEREGIONS HWin ARList))
          (WINDOWPROP HWin (QUOTE CardMap)
                      CardMap)
          (Open.Reshape HWin (MAX (PLUS (Open.SuitLength ND)
                                        10)
                                  (PLUS (Open.SuitLength NC)
                                        10)
                                  (PLUS (Open.SuitLength NH)
                                        10)
                                  (PLUS (Open.SuitLength NS)
                                        10)
                                  300))
          (RETURN HWin])

(Open.Repaintfn
  [LAMBDA (Win)                                                (* rao "17-Apr-86 13:02")
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
                                            (Open.MarkUnselected Win CardReg CardBM)
                                            (if Selected?
                                                then (Open.MarkSelected Win CardReg]
          (RETURN Win])

;; ==== page 16 ====
(Open.Reshape
  [LAMBDA (HWin Width)                                         (* rao "23-Apr-86 10:36")
    (LET [(OldReg (WINDOWPROP HWin (QUOTE REGION]
         (SHAPEW HWin (CREATEREGION (fetch LEFT of OldReg)
                                    (fetch BOTTOM of OldReg)
                                    Width OWinHeight))
         (REDISPLAYW HWin])

(Open.SuitLength
  [LAMBDA (Count)                                              (* rao "10-Apr-86 12:23")
    (PLUS (TIMES Count (PLUS CardWidth CardGap))
          SuitLabelOffset])
)

;; ==== page 17 ====
(* * Dealing functions)

(DEFINEQ

(Dealer.CreateWindow
  [LAMBDA (Deck)                                               (* rao "29-Apr-86 02:43")
    (PROG ((Win (CREATEW (GETBOXREGION 300 245 NIL NIL NIL "Position for the dealing window")
                         "Dealing Window"))
           (Cards (for i from 1 to 52 collect (ELT Deck i)))
           HeartsMenu DS)
          [SETQ HeartsMenu (create MENU
                                   ITEMS ←(for x in (QUOTE (Player1 Player2 Player3 Player4 Done))
                                             collect (LIST x Win))
                                   WHENSELECTEDFN ←(FUNCTION Dealer.Menuer)
                                   MENUROWS ← 1
                                   MENUFONT ←(QUOTE (GACHA 10 BOLD]
          (SETQ DS (WINDOWPROP Win (QUOTE DSP)))

          (* * Print names of suits in window)


          (DSPFONT (QUOTE (TIMESROMAN 12 BOLD))
                   DS)
          (for suit in (QUOTE (Clubs: Diamonds: Hearts: Spades:)) as i from 0 to 3
             do (MOVETO 2 (DIFFERENCE 176 (TIMES i 50))
                        DS)
                (printout DS suit))

          (* * Add appropriate window properties)


          (for Prop in (QUOTE (CardMap SelectedCards NotReady)) do (WINDOWPROP Win Prop NIL))
          (WINDOWPROP Win (QUOTE HeartsMenu)
                      HeartsMenu)
          (WINDOWPROP Win (QUOTE Cards)
                      (ARRAY 4))
          (WINDOWPROP Win (QUOTE CardSet)
                      Cards)
          (WINDOWPROP Win (QUOTE Deck)
                      Deck)
          (WINDOWPROP Win (QUOTE NotReady)
                      T)
          (WINDOWADDPROP Win (QUOTE REPAINTFN)
                         (FUNCTION Dealer.Repaintfn))
          (WINDOWADDPROP Win (QUOTE RESHAPEFN)
                         (FUNCTION RESHAPEBYREPAINTFN))

          (* * Attach the option menu)


          (ATTACHWINDOW (MENUWINDOW HeartsMenu)
                        Win
                        (QUOTE TOP))

          (* * Put the cards in the window)


          (Dealer.Remake Win Cards)

          (* * Return the window)


          (RETURN Win])

(Dealer.Menuer
  [LAMBDA (Item Menu MouseKey)                                 (* rao "29-Apr-86 03:41")
    (LET* [(Win (CADR Item))
           (Type (CAR Item))
           (SelectedCards (WINDOWPROP Win (QUOTE SelectedCards)))
           (Cards (WINDOWPROP Win (QUOTE Cards]
         (SELECTQ
             Type
             ((QUOTE Player1)
               (LET [(PCards (APPEND (WINDOWPROP Win (QUOTE SelectedCards))

;; ==== page 18 ====
                                     (ELT Cards 1]
                    (SETA Cards 1 (if (GREATERP (FLENGTH PCards)
                                                13)
                                      then (NLEFT PCards 13)
                                    else PCards))
                    (WINDOWPROP Win (QUOTE SelectedCards)
                                NIL)
                    (Dealer.Remove Win SelectedCards)))
             ((QUOTE Player2)
               (LET [(PCards (APPEND (WINDOWPROP Win (QUOTE SelectedCards))
                                     (ELT Cards 2]
                    (SETA Cards 2 (if (GREATERP (FLENGTH PCards)
                                                13)
                                      then (NLEFT PCards 13)
                                    else PCards))
                    (WINDOWPROP Win (QUOTE SelectedCards)
                                NIL)
                    (Dealer.Remove Win SelectedCards)))
             ((QUOTE Player3)
               (LET [(PCards (APPEND (WINDOWPROP Win (QUOTE SelectedCards))
                                     (ELT Cards 3]
                    (SETA Cards 3 (if (GREATERP (FLENGTH PCards)
                                                13)
                                      then (NLEFT PCards 13)
                                    else PCards))
                    (WINDOWPROP Win (QUOTE SelectedCards)
                                NIL)
                    (Dealer.Remove Win SelectedCards)))
             ((QUOTE Player4)
               (LET [(PCards (APPEND (WINDOWPROP Win (QUOTE SelectedCards))
                                     (ELT Cards 4]
                    (SETA Cards 4 (if (GREATERP (FLENGTH PCards)
                                                13)
                                      then (NLEFT PCards 13)
                                    else PCards))
                    (WINDOWPROP Win (QUOTE SelectedCards)
                                NIL)
                    (Dealer.Remove Win SelectedCards)))
             ((QUOTE Done)
               (LET [(Deck (WINDOWPROP Win (QUOTE Deck)))
                     (CardsLeft (WINDOWPROP Win (QUOTE CardSet]
                    [for i from 1 to 4 bind PLen
                       do (LET ((PCards (ELT Cards i)))
                               [if (LESSP (SETQ PLen (FLENGTH PCards))
                                          13)
                                   then (SETQ PCards
                                          (APPEND PCards
                                                  (for k from PLen to 12
                                                     collect (LET ((NewCard (CAR (FNTH CardsLeft
                                                                                       (RAND 1 (FLENGTH
                                                                                                 CardsLeft]
                                                                   (SETQ CardsLeft
                                                                     (for c in CardsLeft collect c
                                                                        unless (Card.Equal? c NewCard)))
                                                                   NewCard]
                               (for j from 1 to 13 as c in PCards do (SETA Deck (PLUS j (TIMES 13 (SUB1 i)))
                                                                           c]
                    (WINDOWPROP Win (QUOTE Deck)
                                Deck)
                    (WINDOWPROP Win (QUOTE NotReady)
                                NIL)
                    (CLOSEW Win)))
             NIL])

(Dealer.Repaintfn
  [LAMBDA (Win)                                                (* rao "10-Apr-86 19:45")
    (PROG [(DS (WINDOWPROP Win (QUOTE DSP)))
           (CardMap (WINDOWPROP Win (QUOTE CardMap)))
           (SelectedCards (WINDOWPROP Win (QUOTE SelectedCards]

          (* * Print names of suits in window)


          (for suit in (QUOTE (Clubs: Diamonds: Hearts: Spades:)) as i from 0 to 3
