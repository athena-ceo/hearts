(* "Plays as the Expert; checks every propagated bound against the real hands and logs it.")
(LOAD "{DSK}/hearts/bench/rules/pr.lisp")
(SETQ PR.Checking? T)
(SETQ PR.LogFile (CONCAT BM.Results ".pr"))
STOP
