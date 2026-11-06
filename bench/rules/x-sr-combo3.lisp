(* "As x-sr-combo2, and dump the highest heart when unable to follow.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(EPX.DEFRULE (QUOTE shoot.lead) (QUOTE sr.lead.any.winner) 128
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE history OF ?Self IS ?Hist)
                  (EQUAL ?Winners (CardList.RemoveCard (UNITMSG ?Hist (QUOTE Winners) NIL ?Legals) (Card.Create (QUOTE Q) (QUOTE S))))
                  (Not.Null ?Winners))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Winners)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, leading any winner."))))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.first.high) 110
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE TrickNumber OF ?Self IS 1))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Legals)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking the first trick."))))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.last.take) 85
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQP (FLENGTH (Trick.Cards ?Trick)) 3) (EQP (Trick.Points ?Trick) 0) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?Higher (CardList.HigherCards ?Legals (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit) ?LeadSuit)) (Not.Null ?Higher))
             THEN (THE PlayCard OF ?Self IS (Card.MinCard ?Higher)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, taking this one cheaply."))))
(SETQ EPX.Removed (QUOTE (sfol.little.over)))
(EPX.DEFRULE (QUOTE shoot.follow) (QUOTE sr.little.over) 70
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (THE CurrentTrick OF ?Self IS ?Trick) (EQUAL ?LeadSuit (Card.Suit (CAR (Trick.Cards ?Trick)))) (EQUAL ?WinnerCard (Card.MaxCard (Trick.Cards ?Trick) ?LeadSuit)) (EQUAL ?HigherCards (CardList.RemoveCard (CardList.HigherCards ?Legals ?WinnerCard ?LeadSuit) (Card.Create (QUOTE Q) (QUOTE S)))) (Not.Null ?HigherCards) (EQUAL ?LowestHighCard (Card.MinCard ?HigherCards)) (LEQ (FLENGTH (Card.CardsBetween ?LowestHighCard ?WinnerCard)) 4))
             THEN (THE PlayCard OF ?Self IS ?LowestHighCard) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, going a little over, keeping the queen."))))
(EPX.DEFRULE (QUOTE shoot.dump) (QUOTE sr.dump.high) 110
  (QUOTE (IF (AND (THE CurrentPlayer OF expert.players IS ?Self) (THE LegalCards OF ?Self IS ?Legals) (EQUAL ?Hearts (CardList.CardsOfSuit ?Legals (QUOTE H))) (Not.Null ?Hearts))
             THEN (THE PlayCard OF ?Self IS (Card.MaxCard ?Hearts)) DO
             (PUT.VALUE ?Self (QUOTE LatestReason) "SR - shooting, but dumping my highest heart."))))
STOP
