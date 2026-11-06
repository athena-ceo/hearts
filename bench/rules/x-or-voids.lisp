(* "Oracle: seat 1's opponent models are told every opponent's true voids before each play, the most that any propagation could tell the rules about voids.  Not a fair player: an upper bound.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(DEFINEQ
(OR.TellVoids (LAMBDA (Self)
  (* ; "All seats are Experts in the benchmark, so the true hand is in each player's unit.")
  (for P in (fetch Players of H.LastGame) as N from 1
     unless (EQ (fetch Object of P) Self)
     do (LET ((Model (UNITMSG Self (QUOTE GetOpponent) N))
              (Hand (GET.VALUE (fetch Object of P) (QUOTE Hand))))
          (REMOVE.ALL.LOCAL.VALUES Model (QUOTE Voids))
          (for Suit in (QUOTE (C D H S))
             do (if (NULL (Hand.CardsInSuit Hand Suit))
                    then (ADD.VALUE Model (QUOTE Voids) Suit)))))))
)
(ADVISE (QUOTE EP.Play) (QUOTE BEFORE)
  (QUOTE (if (EQ self (fetch Object of (CAR (fetch Players of H.LastGame)))) then (OR.TellVoids self))))
STOP
