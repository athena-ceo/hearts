;; ==== page 19 ====
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
                                                then (HP.MarkSelected Win CardReg CardBM]
          (RETURN Win])

(Dealer.Reshape
  [LAMBDA (Win Width)
    (LET [(OldReg (WINDOWPROP HWin (QUOTE REGION]                (* rao "29-Apr-86 02:33")
      [SHAPEW Win (CREATEREGION (fetch LEFT of OldReg)
                               (fetch BOTTOM of OldReg)
                               (PLUS 10 Width)
                               (PLUS (FONTHEIGHT (DSPFONT NIL WindowTitleDisplayStream))
                                     (fetch HEIGHT of OldReg]
      (REDISPLAYW Win])

(Dealer.Remake
  [LAMBDA (HWin Cards)
    (PROG ((ND 0)                                                (* rao "29-Apr-86 02:36")
           (NC 0)
           (NH 0)
           (NS 0)
           (CardMap NIL)
           ARList HeartsMenu)
          (WINDOWPROP HWin (QUOTE CardSet)
                      Cards)
          (SETQ ARList (for C in Cards collect (LET ((Suit (fetch Suit of C))
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
                                                                        UPFN ←(FUNCTION Dealer.Select)
                                                                        DATA ←(LIST C CardBM)))
                                               [SETQ CardMap
                                                  (APPEND CardMap (LIST (LIST C CardBM CReg NewAR]
                                               NewAR)))
          (SETACTIVEREGIONS HWin ARList)
          (WINDOWPROP HWin (QUOTE CardMap)
                      CardMap)
          (Dealer.Reshape HWin (MAX (HP.SuitLength ND)
                                    (HP.SuitLength NC)
                                    (HP.SuitLength NH)
                                    (HP.SuitLength NS)
                                    300))
          (RETURN HWin])

(Dealer.Select
  [LAMBDA (HWin CReg Data)
    (PROG ((Card (CAR Data))                                     (* rao "29-Apr-86 02:38")
           (SelectedCards (WINDOWPROP HWin (QUOTE SelectedCards)))
           MaxSelected NumSelected)

;; ==== page 20 ====
          (if (FMEMB Card SelectedCards)
              then (Dealer.UnSelect HWin Card)
                   (RETURN))
          (SETQ MaxSelected 13)
          (SETQ NumSelected (LENGTH SelectedCards))
          (if (GEQ NumSelected MaxSelected)
              then (Dealer.UnSelect HWin (CAR SelectedCards)))
          (ACTIVEREGIONS/DOLOWLIGHT HWin (GETPICKREGION HWin))
          (HP.MarkSelected HWin CReg)
          (WINDOWADDPROP HWin (QUOTE SelectedCards)
                         Card])

(Dealer.UnSelect
  [LAMBDA (HWin Card)
    (LET ((PickAR (GETPICKREGION HWin))                          (* rao "10-Apr-86 19:28")
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

(Dealer.Remove
  [LAMBDA (HWin Cards)
    (LET [(AllCards (WINDOWPROP HWin (QUOTE CardSet]             (* rao "29-Apr-86 03:25")
      (WINDOWPROP HWin (QUOTE CardSet)
                  (LDIFFERENCE AllCards Cards))
      (Dealer.Remake HWin (WINDOWPROP HWin (QUOTE CardSet])
)

;; ==== page 21 ====
(* * Human Player Interface)


(RPAQQ CY 160)

(RPAQQ DY 110)

(RPAQQ HPImmediatePlay T)

(RPAQQ HPMapping ((GiveHand . HP.GiveHand)
                  (PassOut . HP.PassOut)
                  (PassIn . HP.PassIn)
                  (Play . HP.Play)))

(RPAQQ HPSelectShade 10260)

(RPAQQ HPSelectShade2 49731)

(RPAQQ HY 60)

(RPAQQ SY 10)

(RPAQQ SuitLabelOffset 90)
(DEFINEQ

(HP.Create
  [LAMBDA (Name)
    (LET [(Name (OR Name (TTYIN "Enter player's name: " NIL NIL (QUOTE (STRING NORAISE]
          (create Player
                  Name ← Name
                  Type ←(QUOTE Lisp)
                  Object ←(HP.CreateWindow Name)
                  Mapping ← HPMapping])

(HP.GiveHand
  [LAMBDA (HWin Hand)                                            (* rao "11-Apr-86 00:02")
    (PROG (HeartsMenu)
          (HP.RemakeHand HWin Hand)
          (WINDOWPROP HWin (QUOTE PassOrPlay)
                      (QUOTE Pass))
          (SETQ HeartsMenu (WINDOWPROP HWin (QUOTE HeartsMenu)))
          (SHADEITEM (CAR (fetch ITEMS of HeartsMenu))
                     HeartsMenu GRAYSHADE)
          (SHADEITEM (CADR (fetch ITEMS of HeartsMenu))
                     HeartsMenu WHITESHADE)
          (RETURN HWin])

(HP.PassIn
  [LAMBDA (HWin PassIn)                                          (* rao "17-Apr-86 13:01")
    (for C in PassIn do (Hand.AddCard (WINDOWPROP HWin (QUOTE Hand))
                                      C))
    (HP.RemakeHand HWin (WINDOWPROP HWin (QUOTE Hand)))
    (SHADEITEM [CAR (fetch ITEMS of (WINDOWPROP HWin (QUOTE HeartsMenu]
               (WINDOWPROP HWin (QUOTE HeartsMenu))
               WHITESHADE)
    (WINDOWPROP HWin (QUOTE Ready?)
                NIL])

(HP.PassOut
  [LAMBDA (HWin Pass)                                            (* rao "17-Apr-86 13:26")

          (* * Waits for Ready? to be true, indicating the human has chosen his cards. Returns the three cards and removes
          them from the human.)


    (PROG [(Ready? (WINDOWPROP HWin (QUOTE Ready?)))
           (SelectedCards (WINDOWPROP HWin (QUOTE SelectedCards)))
           (HeartsMenu (WINDOWPROP HWin (QUOTE HeartsMenu)))
           (Hand (WINDOWPROP HWin (QUOTE Hand]
          (if Pass
              then (PROMPTPRINT (CONCAT "Pass to the " Pass))
                   [HP.WaitForReady HWin (CONCAT "Please choose and pass 3 cards, "
                                                 (WINDOWPROP HWin (QUOTE Name]
                   (SETQ SelectedCards (WINDOWPROP HWin (QUOTE SelectedCards)))

;; ==== page 22 ====
                   (for C in SelectedCards do (Hand.RemoveCard Hand C))
                   (HP.RemakeHand HWin Hand)
                   (WINDOWPROP HWin (QUOTE SelectedCards)
                               NIL)
              else (PROMPTPRINT "Hold Hand.  Any chosen cards will be ignored.")
                   (for Card in SelectedCards do (HP.Unselect HWin Card)))

          (* * Cards ready to be passed back.)


          (WINDOWPROP HWin (QUOTE PassOrPlay)
                      (QUOTE Play))
          (RETURN SelectedCards])

(HP.Play
  [LAMBDA (HWin Trick HeartsBroken?)                             (* rao "15-Apr-86 22:12")
    (LET ((Possibles (H.GetLegals (WINDOWPROP HWin (QUOTE Hand))
                                  Trick HeartsBroken?))
          Card)
      (WINDOWPROP HWin (QUOTE CurrentTrick)
                  Trick)
      (WINDOWPROP HWin (QUOTE HeartsBroken?)
                  HeartsBroken?)
      [PROMPTPRINT (CONCAT "Your turn, " (WINDOWPROP HWin (QUOTE Name]
      (HP.WaitForReady HWin "Please hurry. There are many impatient players here.")
      [SETQ Card (CAR (WINDOWPROP HWin (QUOTE SelectedCards]
      [while (NOT (MEMBER Card Possibles))
         do (HP.Unselect HWin Card)
            (PROMPTPRINT "Illegal card. Try again.")
            (WINDOWPROP HWin (QUOTE Ready?)
                        NIL)
            (HP.WaitForReady HWin "Please hurry. There are many impatient players here.")
            (SETQ Card (CAR (WINDOWPROP HWin (QUOTE SelectedCards]
      (if (WINDOWPROP HWin (QUOTE Legal))
          then [DOSELECTEDITEM (WINDOWPROP HWin (QUOTE HeartsMenu))
                               (CADDDR (fetch ITEMS of (WINDOWPROP HWin (QUOTE HeartsMenu]
                                                       (* Undoes Legal stuff for next round.)
               )
      (HP.Unselect HWin Card)
      (HP.RemoveCard HWin Card)
      (WINDOWPROP HWin (QUOTE Ready?)
                  NIL)
      Card])

(HP.Trick
  [LAMBDA (Trick)                                                (* hed " 3-May-86 17:14")
    (CLEARW PROMPTWINDOW])
)
(DEFINEQ

(HP.AddCard
  [LAMBDA (HWin Card)                                            (* rao "10-Apr-86 20:38")

          (* * Adds Card to Hand and to the display)


    (LET [(Hand (WINDOWPROP HWin (QUOTE Hand]
      (Hand.AddCard (WINDOWPROP HWin (QUOTE Hand))
                    Card)
      (HP.RemakeHand HWin Hand])

(HP.ChooseSomeCards
  [LAMBDA (n Deck)                                               (* rao "10-Apr-86 19:40")
    (LET ((n (OR n 13))
          Res)
      [for i from 1 to n do (LET ((next (RAND 1 52))
                                  nc)
                                 (SETQ nc (CAR (NTH Deck next)))
                                 [while (FMEMB nc Res)
                                    do (SETQ next (RAND 1 52))
                                       (SETQ nc (CAR (NTH Deck next]
                                 (SETQ Res (APPEND Res (LIST nc]
      Res])

;; ==== page 23 ====
(HP.CreateWindow
  [LAMBDA (HumanName)                                            (* hed " 4-May-86 22:17")
    (LET* ([HumanName (OR HumanName (SETQ HumanName (TTYIN "Enter your name: " NIL NIL
                                                           (QUOTE (STRING NORAISE]
           (Win (CREATEW (GETBOXREGION 300 245 NIL NIL NIL (CONCAT "Position for your interface window, "
                                                                   HumanName))
                         (CONCAT "Hearts Window for " HumanName)))
           HeartsMenu DS)
      [SETQ HeartsMenu (create MENU
                               ITEMS ←(for x in (QUOTE (Play Pass Score LegalCards))
                                         collect (LIST x Win))
                               WHENSELECTEDFN ←(FUNCTION HP.Menuer)
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


      (for Prop in (QUOTE (CardMap Hand SelectedCards PassOrPlay Ready?))
         do (WINDOWPROP Win Prop NIL))
      (WINDOWPROP Win (QUOTE Name)
                  HumanName)
      (WINDOWPROP Win (QUOTE HeartsMenu)
                  HeartsMenu)
      (WINDOWADDPROP Win (QUOTE REPAINTFN)
                     (FUNCTION HP.Repaintfn))
      (WINDOWADDPROP Win (QUOTE RESHAPEFN)
                     (FUNCTION RESHAPEBYREPAINTFN))

          (* * Attach the option menu)


      (ATTACHWINDOW (MENUWINDOW HeartsMenu)
                    Win
                    (QUOTE TOP))

          (* * Return the window)


      Win])

(HP.GetName
  [LAMBDA (HWin)                                                 (* rao "10-Apr-86 10:53")
    (WINDOWPROP HWin (QUOTE Name])

(HP.MakeDeck
  [LAMBDA NIL                                                    (* rao "10-Apr-86 19:32")
    (for v in CardValues join (for s in SuitValues collect (Card.Create v s])

(HP.MarkSelected
  [LAMBDA (HWin CardReg Shade2?)                                 (* rao "10-Apr-86 22:09")
    (DSPFILL CardReg (if Shade2?
                         then HPSelectShade2
                         else HPSelectShade)
             (QUOTE PAINT)
             (WINDOWPROP HWin (QUOTE DSP])

(HP.MarkUnselected
  [LAMBDA (HWin CardReg CardBM)                                  (* rao "10-Apr-86 19:24")
    (BITBLT CardBM 0 0 HWin (fetch LEFT of CardReg)
            (fetch BOTTOM of CardReg)
            CardWidth CardHeight (QUOTE INPUT)
            (QUOTE REPLACE])

;; ==== page 24 ====
(HP.Menuer
  [LAMBDA (Item Menu MouseKey)                                   (* rao "14-Apr-86 16:29")
    (LET ((HWin (CADR Item))
          (Type (CAR Item))
          Pass?)
      (SETQ Pass? (EQUAL (WINDOWPROP HWin (QUOTE PassOrPlay))
                         (QUOTE Pass)))
      (SELECTQ Type
               [(QUOTE Pass)
                (PROMPTPRINT "Pass noted.")
                (if (AND Pass? (EQP (LENGTH (WINDOWPROP HWin (QUOTE SelectedCards)))
                                    3))
                    then (WINDOWPROP HWin (QUOTE Ready?)
                                     T)
                         (SHADEITEM Item Menu GRAYSHADE)
                         (WINDOWPROP HWin (QUOTE PassOrPlay)
                                     (QUOTE Play]
               ((QUOTE Play)
                (PromptPrint "Play noted.")
                (if (AND (NOT Pass?)
                         (EQP (LENGTH (WINDOWPROP HWin (QUOTE SelectedCards)))
                              1))
                    then (WINDOWPROP HWin (QUOTE Ready?)
                                     T)))
               ((QUOTE Score)
                (PromptPrint "Score noted"))
               [(QUOTE LegalCards)
                (PromptPrint "Legal Cards noted.")
                (LET ((Trick (WINDOWPROP HWin (QUOTE CurrentTrick)))
                      Possibles)
                     [SETQ Possibles (H.GetLegals (WINDOWPROP HWin (QUOTE Hand))
                                                  (OR Trick (create Trick))
                                                  (WINDOWPROP HWin (QUOTE HeartsBroken?]
                     (if (WINDOWPROP HWin (QUOTE Legal))
                         then (for C in Possibles
                                 do (LET [[CardReg (CADDR (for c in (WINDOWPROP HWin (QUOTE CardMap))
                                                             thereis (EQUAL (CAR c)
                                                                            C]
                                          (CardBM (CADR (for c in (WINDOWPROP HWin (QUOTE CardMap))
                                                           thereis (EQUAL (CAR c)
                                                                          C]
                                         (HP.MarkUnselected HWin CardReg CardBM)))
                              (for C in (WINDOWPROP HWin (QUOTE SelectedCards))
                                 do (LET [(CardReg (CADDR (for c in (WINDOWPROP HWin (QUOTE CardMap))
                                                            thereis (EQUAL (CAR c)
                                                                           C]
                                         (HP.MarkSelected HWin CardReg)))
                              (SHADEITEM Item Menu WHITESHADE)
                              (WINDOWPROP HWin (QUOTE Legal)
                                          NIL)
                         else (for C in Possibles
                                 do (LET [(CardReg (CADDR (for c in (WINDOWPROP HWin (QUOTE CardMap))
                                                            thereis (EQUAL (CAR c)
                                                                           C]
                                         (HP.MarkSelected HWin CardReg T)))
                              (SHADEITEM Item Menu GRAYSHADE)
                              (WINDOWPROP HWin (QUOTE Legal)
                                          T]
               NIL])

(HP.RemakeHand
  [LAMBDA (HWin Hand)                                            (* rao "11-Apr-86 00:31")
    (Hand.Sort Hand)
    (PROG ((Cards (Hand.Cards Hand))
           (ND 0)
           (NC 0)
           (NH 0)
           (NS 0)
           (CardMap NIL)
           ARList HeartsMenu)
          (WINDOWPROP HWin (QUOTE Hand)
                      Hand)
          (SETQ ARList (for C in Cards collect (LET ((Suit (fetch Suit of C))
