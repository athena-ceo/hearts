(* "Not a variant to try.  For the conformance test: every seat sets out to shoot on any hand, to reach the rarely used shooting rules.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(for Slot in (QUOTE (POMaxLowSpades POMaxLoserHearts PIMaxLowSpades PIMaxLoserHearts)) do (PUT.VALUE (QUOTE epx.personality) Slot 13))
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 0)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 0)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PILowestHeart) 2)
(ADVISE (QUOTE H.PlayGame) (QUOTE BEFORE)
  (QUOTE (for P in Players do (PUT.VALUE (fetch Object of P) (QUOTE Personality) (QUOTE epx.personality)))))
STOP
