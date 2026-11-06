(* "Both: pass the ace or king of spades when I don't hold the queen, and never set out to shoot.")
(LOAD "{DSK}/hearts/bench/rules/x-pass-high-spades.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 999)
STOP
