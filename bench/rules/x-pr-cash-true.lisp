(* "Oracle: while minimizing, lead a safe winner when no opponent is truly void in the suit.  An upper bound.")
(LOAD "{DSK}/hearts/bench/rules/pr.lisp")
(SETQ PR.CashMode (QUOTE true))
(EPX.DEFRULE (QUOTE lead.play) (QUOTE pr.cash) 75
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals)
                  (THE history OF ?Self IS ?Hist) (EQUAL ?Cards (PR.CashCards ?Self ?Hist ?Legals)) (Not.Null ?Cards))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Cards)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "PR - cashing a winner while everyone can still follow."))))
STOP
