(* "While shooting and unable to follow, dump the highest heart, which gives up the moon.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.dump) (QUOTE sr.dump.high) 110
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (EQUAL ?Hearts (CardList.CardsOfSuit ?Legals (QUOTE H))) (Not.Null ?Hearts))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Hearts)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, but dumping my highest heart."))))
STOP
