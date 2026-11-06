(* "Pass the ace or king of spades whenever I don't hold the queen, however long my spades are.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE minimizing.passout) (QUOTE epx.pass.hi.s.no.queen) 95
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self)
                  (THE Hand OF ?Self IS ?Hand)
                  (EQUAL ?HighestSpade (Hand.MaxCard ?Hand (QUOTE S)))
                  (Card.Higher? ?HighestSpade (Card.Create (QUOTE Q) (QUOTE S)))
                  (NULL (CardList.Member (Card.Create (QUOTE Q) (QUOTE S)) (Hand.Cards ?Hand)))
                  (NUMBERP (UNITMSG ?Self (QUOTE DoPass) (LIST ?HighestSpade))))
             THEN (More Cards Selected))))
STOP
