(* "Shooting rules together: lead the lowest non-winner, keep the queen, take first trick and cheap last tricks.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.lead) (QUOTE sr.lead.low) 125
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE history OF ?Self IS ?Hist) (EQUAL ?WinnerSuits (UNITMSG ?Hist (QUOTE WinnerSuits))) (EQUAL ?NonWinners (CardList.EliminateSuits (CardList.RemoveCard (CardList.EliminateSuits (UNITMSG ?Hist (QUOTE NonWinners) NIL ?Legals) ?WinnerSuits) (Card.Create (QUOTE Q) (QUOTE S))) (UNITMSG ?Self (QUOTE HeartyOpponentVoidSuits)))) (Not.Null ?NonWinners))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?NonWinners)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, leading lowest non-winner."))))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.first.high) 110
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE TrickNumber OF ?Self IS 1))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Legals)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking the first trick."))))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.last.take) 85
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQP (FLENGTH (Trick.Cards ?Trick)) 3) (EQP (Trick.Points ?Trick) 0) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?Higher (CardList.HigherCards ?Legals (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit) ?LeadSuit)) (Not.Null ?Higher))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Higher)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking this one cheaply."))))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.little.over) 70
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?WinnerCard (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit)) (EQUAL ?HigherCards (CardList.RemoveCard (CardList.HigherCards ?Legals ?WinnerCard ?LeadSuit) (Card.Create (QUOTE Q) (QUOTE S)))) (Not.Null ?HigherCards) (EQUAL ?LowestHighCard (Card.MinCard ?HigherCards)) (LEQ (FLENGTH (Card.CardsBetween ?LowestHighCard ?WinnerCard)) 4))
             THEN (THE PlayCard OF ?Self IS ?LowestHighCard) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, going a little over, keeping the queen."))))
(SETQ EPX.Removed (QUOTE (slead.non.op.void.loser sfol.little.over)))
STOP
