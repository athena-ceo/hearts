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

(* "Give the selected card to Player1, then Done: the rest are dealt at random.")
(DEFINEQ
(DT.FullDeck? (LAMBDA (D)
  (AND (ARRAYP D)
       (for i from 1 to 52 always (ELT D i))
       (for i from 1 to 52 always (for j from (ADD1 i) to 52 never (Card.Equal? (ELT D i) (ELT D j)))))))
)
(Dealer.Menuer (LIST (QUOTE Player1) DW) NIL NIL)
(HT.CHECK "Player1 gets the selected card" (AND (MEMBER C1 (ELT (WINDOWPROP DW (QUOTE Cards)) 1)) T) T)
(Dealer.Menuer (LIST (QUOTE Done) DW) NIL NIL)
(HT.CHECK "Done deals 52 different cards" (DT.FullDeck? (WINDOWPROP DW (QUOTE Deck))) T)
(HT.CHECK "Player1's card is first in the deck" (AND (Card.Equal? C1 (ELT (WINDOWPROP DW (QUOTE Deck)) 1)) T) T)

(* "H.Shuffle with ManualDeal? T (HEARTS-BUGS H5): it waits for Done, then returns the deck.
    A second process presses Done as soon as the dealing window is made.")
(ADVISE (QUOTE Dealer.CreateWindow) (QUOTE AFTER)
        (QUOTE (ADD.PROCESS (LIST (QUOTE Dealer.Menuer) (KWOTE (LIST (QUOTE Done) !VALUE)) NIL NIL))))
(SETQ D2 (H.Shuffle (Card.CreateDeck) T))
(UNADVISE (QUOTE Dealer.CreateWindow))
(HT.CHECK "H.Shuffle by hand returns a full deck" (DT.FullDeck? D2) T)
