(* "Count spades as poor protection only below 3, not below 4, so high spades are passed less often.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE SpadeProtLen) 3)
STOP
