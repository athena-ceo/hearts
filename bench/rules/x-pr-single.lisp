(* "While minimizing, lead low into a suit where an opponent is proved to hold exactly one card.")
(LOAD "{DSK}/hearts/bench/rules/pr.lisp")
(EPX.DEFRULE (QUOTE lead.play) (QUOTE pr.under.single) 78
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals)
                  (THE history OF ?Self IS ?Hist) (EQUAL ?Cards (PR.UnderSingle ?Hist ?Legals)) (Not.Null ?Cards))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Cards)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "PR - leading into a forced singleton."))))
STOP
