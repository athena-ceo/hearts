(* "While shooting, lead the lowest non-winner, not the highest.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(SETQ EPX.Removed (QUOTE (slead.non.op.void.loser)))
(EPX.DEFRULE (QUOTE shoot.lead) (QUOTE sr.lead.low) 125
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE history OF ?Self IS ?Hist) (EQUAL ?WinnerSuits (UNITMSG ?Hist (QUOTE WinnerSuits))) (EQUAL ?NonWinners (CardList.EliminateSuits (CardList.RemoveCard (CardList.EliminateSuits (UNITMSG ?Hist (QUOTE NonWinners) NIL ?Legals) ?WinnerSuits) (Card.Create (QUOTE Q) (QUOTE S))) (UNITMSG ?Self (QUOTE HeartyOpponentVoidSuits)))) (Not.Null ?NonWinners))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?NonWinners)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, leading lowest non-winner."))))
STOP
