(* "While shooting, play high on the first trick, which can't hold points.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.first.high) 110
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE TrickNumber OF ?Self IS 1))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Legals)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking the first trick."))))
STOP
