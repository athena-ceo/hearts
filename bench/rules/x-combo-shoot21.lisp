(* "As x-combo, but still shoot with 21 or more high-card points.")
(LOAD "{DSK}/hearts/bench/rules/x-high-when-winning.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 21)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 21)
(PUT.VALUE (QUOTE epx.personality) (QUOTE TriggerHappiness) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE SpadeProtLen) 5)
STOP
