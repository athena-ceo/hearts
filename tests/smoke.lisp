(* "Self-test for the headless harness (docker/).  Expect: 2 PASS, one trapped ERROR line
    is NOT expected here, so exit status 0.")
(HT.CHECK "arithmetic" (PLUS 2 2) 4)
(HT.CHECK "errors are trapped, not broken into" (NULL (NLSETQ (UNDEFINED-FN-XYZ 3))))
(HT.SNAP "smoke")
