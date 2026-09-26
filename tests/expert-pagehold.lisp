(* "Load the dist files with Medley's normal page holding ON (the harness usually turns it
    off): EXPERT must suppress holds while it loads LOOPS, and restore them.  Run WITHOUT
    --loops.  A page hold shows up as a timeout.  The runner checks the dribble for LOOPS
    'No doc string' warnings.")
(UNADVISE (QUOTE PAGEFULLFN))
(CNDIR "{DSK}/hearts/dist/")
(HT.CHECK "FILESLOAD ACTIVEREGIONS HEARTS EXPERT with page holds on" (NLSETQ (FILESLOAD ACTIVEREGIONS HEARTS EXPERT)))
(HT.CHECK "LOOPS loaded" (GETD (QUOTE DefineClass)))
(HT.CHECK "Exec window's page hold restored" (NULL (WINDOWPROP (WFROMDS (TTYDISPLAYSTREAM)) (QUOTE PAGEFULLFN))))
(HT.CHECK "handlers have doc strings" (STRPOS "Administrator message" (GetMethod (GetObjectRec (QUOTE EP.ExpertPlayer)) (QUOTE Play) (QUOTE doc))))
