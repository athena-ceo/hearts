(* "Not a variant to try.  For the conformance test: no seat sets out to shoot and all suspect at once, to reach the rarely used eclipsing rules.")
(LOAD "{DSK}/hearts/bench/rules/epx.lisp")
(PUT.VALUE (QUOTE epx.personality) (QUOTE POMinShootPoints) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE PIMinShootPoints) 999)
(PUT.VALUE (QUOTE epx.personality) (QUOTE TriggerHappiness) 0.05)
(ADVISE (QUOTE H.PlayGame) (QUOTE BEFORE)
  (QUOTE (for P in Players do (PUT.VALUE (fetch Object of P) (QUOTE Personality) (QUOTE epx.personality)))))
STOP
