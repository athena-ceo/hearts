(* "Set out to shoot only with 18 or more high-card points, not 15.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 18)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 18)
STOP
