(* "Manual-deal window (LHearts ... ManualDeal? T): build it and select/unselect cards --
    the three Dealer.* functions whose edit-date comments were transcribed into their
    variable lists (HEARTS-BUGS T-section).")
(LOAD "{DSK}/hearts/medley/HEARTS")
(HT.AUTOPLACE)
(SETQ DECK (Card.CreateDeck))
(SETQ DW (Dealer.CreateWindow DECK))
(HT.CHECK "dealing window made (Dealer.Remake ran)" (WINDOWP DW))
(SETQ C1 (CAR (WINDOWPROP DW (QUOTE CardSet))))
(Dealer.Select DW NIL (LIST C1 NIL))
(HT.CHECK "Dealer.Select records the card" (MEMBER C1 (WINDOWPROP DW (QUOTE SelectedCards))))
(HT.SNAP "dealer")
