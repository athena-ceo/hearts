(* "While minimizing, lead a safe winner only when propagation proves every opponent holds the suit.")
(LOAD "{DSK}/hearts/bench/rules/pr.lisp")
(SETQ PR.CashMode (QUOTE sure))
(EPX.DEFRULE (QUOTE lead.play) (QUOTE pr.cash) 75
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals)
                  (THE history OF ?Self IS ?Hist) (EQUAL ?Cards (PR.CashCards ?Self ?Hist ?Legals)) (Not.Null ?Cards))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Cards)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "PR - cashing a winner while everyone can still follow."))))
STOP
