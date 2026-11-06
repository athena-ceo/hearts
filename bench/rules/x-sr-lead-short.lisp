(* "While shooting, lead the lowest non-winner of the shortest suit.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(DEFINEQ
(SR.Shortest (LAMBDA (Cards)
  (* ; "The lowest card of the suit with the fewest cards among Cards.")
  (LET (Best BestCount)
    (for C in Cards
       do (LET ((Count (for D in Cards count (EQ (fetch Suit of D) (fetch Suit of C)))))
            (if (OR (NULL Best) (ILESSP Count BestCount)
                    (AND (EQP Count BestCount) (Card.Higher? Best C)))
                then (SETQ Best C) (SETQ BestCount Count))))
    Best)))
)
(EPX.DEFRULE (QUOTE shoot.lead) (QUOTE sr.lead.short) 127
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE history OF ?Self IS ?Hist) (EQUAL ?NonWinners (CardList.RemoveCard (UNITMSG ?Hist (QUOTE NonWinners) NIL ?Legals) (Card.Create (QUOTE Q) (QUOTE S)))) (Not.Null ?NonWinners))
             THEN (THE PlayCard OF ?Self IS (SR.Shortest ?NonWinners)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, leading from my shortest suit."))))
STOP
