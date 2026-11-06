(* "Not a variant to try.  For the conformance test: seat 1 sets out to shoot on any hand and the other three suspect at once.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(for Slot in (QUOTE (POMaxLowSpades POMaxLoserHearts PIMaxLowSpades PIMaxLoserHearts)) do (PUT.VALUE (QUOTE epx.personality) Slot 13))
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 0)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 0)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PILowestHeart) 2)
(PUT.VALUE (QUOTE standard.personality) (QUOTE TriggerHappiness) 0.1)
STOP
