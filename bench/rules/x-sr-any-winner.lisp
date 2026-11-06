(* "While shooting, lead any winner other than the queen first, highest first.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.lead) (QUOTE sr.lead.any.winner) 128
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE history OF ?Self IS ?Hist)
                  (EQUAL ?Winners (CardList.RemoveCard (UNITMSG ?Hist (QUOTE Winners) NIL ?Legals) (Card.Create (QUOTE Q) (QUOTE S))))
                  (Not.Null ?Winners))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Winners)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, leading any winner."))))
STOP
