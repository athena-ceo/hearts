(* "Count spades as poor protection below 5, not below 4, so high spades are passed more often.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE SpadeProtLen) 5)
STOP
