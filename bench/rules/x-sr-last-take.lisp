(* "While shooting and last on a trick with no points, take it with the lowest card that wins.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.last.take) 85
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQP (FLENGTH (Trick.Cards ?Trick)) 3) (EQP (Trick.Points ?Trick) 0) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?Higher (CardList.HigherCards ?Legals (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit) ?LeadSuit)) (Not.Null ?Higher))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Higher)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking this one cheaply."))))
STOP
