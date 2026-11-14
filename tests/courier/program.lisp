(* "TRIAL: a Courier program of our own, in the manner of REMOTEPSW: one typed procedure, a declared error, no evaluation.")
(COURIERPROGRAM HEARTSTRIAL (1986 1)
    TYPES ((CARD (RECORD (SUIT STRING) (VALUE CARDINAL)))
           (CARDS (SEQUENCE CARD)))
    PROCEDURES ((LOWEST 0 (CARDS) RETURNS (CARD) REPORTS (NO.CARDS) IMPLEMENTEDBY HCT.Lowest))
    ERRORS ((NO.CARDS 0 (STRING))))
(DEFINEQ
(HCT.Lowest
  (LAMBDA (CourierStream Program Procedure Cards)
    (* ; "The lowest card of CARDS, each a (suit value) record.")
    (if Cards
        then (LIST (QUOTE RETURN) (for C in Cards smallest (CADR C)))
      else (LIST (QUOTE ABORT) (QUOTE NO.CARDS) "no cards"))))
)
STOP
