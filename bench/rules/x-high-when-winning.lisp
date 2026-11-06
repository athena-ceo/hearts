(* "When following in a non-spade suit and every legal card beats the trick so far, play the highest, not the lowest.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE follow.play) (QUOTE epx.follow.high.when.winning) 65
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self)
                  (THE LegalCards OF ?Self IS ?Legals)
                  (THE CurrentTrick OF ?Self IS ?Trick)
                  (EQUAL ?LeadSuit (Trick.LeadSuit ?Trick))
                  (NEQ ?LeadSuit (QUOTE S))
                  (EQP (Trick.Points ?Trick) 0)
                  (NULL (CardList.LowerCards ?Legals (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit) ?LeadSuit)))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Legals)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "EPX - must take it anyway, so play high."))))
STOP
