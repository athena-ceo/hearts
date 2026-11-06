(* "Round 2's winners together: never set out to shoot, never eclipse, more spade protection, play high when winning anyway.")
(LOAD "{DSK}/hearts/bench/rules/x-high-when-winning.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE TriggerHappiness) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE SpadeProtLen) 5)
STOP
