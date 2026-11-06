(* "While shooting, never use the queen of spades to go a little over.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(SETQ EPX.Removed (QUOTE (sfol.little.over)))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.little.over) 70
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?WinnerCard (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit)) (EQUAL ?HigherCards (CardList.RemoveCard (CardList.HigherCards ?Legals ?WinnerCard ?LeadSuit) (Card.Create (QUOTE Q) (QUOTE S)))) (Not.Null ?HigherCards) (EQUAL ?LowestHighCard (Card.MinCard ?HigherCards)) (LEQ (FLENGTH (Card.CardsBetween ?LowestHighCard ?WinnerCard)) 4))
             THEN (THE PlayCard OF ?Self IS ?LowestHighCard) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, going a little over, keeping the queen."))))
STOP
