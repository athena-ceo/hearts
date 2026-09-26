(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "Headless test harness for Medley.  Loaded by medley-run's REM.CM, then HT.MAIN
    reads a script of Interlisp forms, evaluates each one with errors trapped, and
    writes a transcript that the host can read.  See docker/README.md.")

(RPAQ? HT.OUT NIL)
(RPAQ? HT.SNAPDIR NIL)
(RPAQ? HT.PASS 0)
(RPAQ? HT.FAIL 0)
(RPAQ? HT.ECHO T)
(RPAQ? HT.NEXTPLACE 0)

(DEFINEQ

(HT.BOOT
  (LAMBDA NIL
    (* "Entry point from medley-run's REM.CM.  Parameters come from the environment.")
    (LET ((Out (UNIX-GETENV "HTOUT")))
         (DRIBBLE (CONCAT Out "dribble.txt"))
         (HT.MAIN (UNIX-GETENV "HTSCRIPT")
                (CONCAT Out "transcript.txt")
                Out
                (EQUAL (UNIX-GETENV "HTLOOPS")
                       "T"))
         (DRIBBLE)
         (LOGOUT T))))

(HT.MAIN
  (LAMBDA (ScriptFile OutFile SnapDir LoadLoops?)
    (SETQ HT.SNAPDIR SnapDir)
    (SETQ HT.PASS 0)
    (SETQ HT.FAIL 0)
    (SETQ HELPFLAG NIL)
    (* "Never stop for a full exec window: no one is there to press a key.  (Medley's own
        loadup scripts do the same.)")
    (ADVISE (QUOTE PAGEFULLFN) (QUOTE (RETURN)))
    (* "The transcript is reopened in APPEND mode for every write, so whatever was logged
        is on disk even if the run hangs and gets killed.")
    (CLOSEF (OPENSTREAM OutFile (QUOTE OUTPUT) (QUOTE NEW)))
    (SETQ HT.OUT OutFile)
    (HT.LOG "==HT-BEGIN==")
    (if LoadLoops?
        then (HT.EVAL (QUOTE (HT.LOADLOOPS))))
    (HT.RUNFILE ScriptFile)
    (HT.LOG (CONCAT "==HT-SUMMARY== pass " HT.PASS " fail " HT.FAIL))
    (HT.LOG "==HT-END==")
    (SETQ HT.OUT NIL)))

(HT.WRITE
  (LAMBDA (X Readably?)
    (* "Append X (and a newline) to the transcript.  Readably? prints with PRINT, bounded
        so circular or huge structures can't hang.")
    (if HT.OUT
        then (LET ((S (OPENSTREAM HT.OUT (QUOTE APPEND))))
                  (if Readably?
                      then (RESETFORM (PRINTLEVEL 6 60)
                                  (PRINT X S))
                    else (PRIN1 X S)
                         (TERPRI S))
                  (CLOSEF S)))
    X))

(HT.LOG
  (LAMBDA (X)
    (HT.WRITE X NIL)))

(HT.SHOW
  (LAMBDA (X Prefix)
    (HT.WRITE (if Prefix
                  then (CONCAT Prefix (RESETFORM (PRINTLEVEL 6 60)
                                             (MKSTRING X T)))
                else X)
           (NOT Prefix))))

(HT.ERRSTRING
  (LAMBDA (C)
    (XCL:CONDITION-CASE (CL:FORMAT NIL "~A" C)
           (CL:ERROR NIL (CONCAT "<unprintable condition " (CL:TYPE-OF C)
                                ">")))))

(HT.RUNFILE
  (LAMBDA (File)
    (* "Read with the Interlisp readtable into the INTERLISP package, whatever exec we
        were started from.")
    (LET ((S (OPENSTREAM File (QUOTE INPUT)
                    (QUOTE OLD)))
          (RT (FIND-READTABLE "INTERLISP"))
          (*PACKAGE* (CL:FIND-PACKAGE "INTERLISP"))
          (*READTABLE* (FIND-READTABLE "INTERLISP"))
          Form)
         (until (PROGN (SKIPSEPRS S RT)
                       (EOFP S))
            do (SETQ Form (XCL:CONDITION-CASE (READ S RT)
                                 (CL:ERROR (C)
                                        (HT.LOG (CONCAT "READ-ERROR: " (HT.ERRSTRING C)))
                                        (QUOTE HT.READ-FAILED))))
               (if (EQ Form (QUOTE HT.READ-FAILED))
                   then (RETURN NIL))
               (if (NOT (AND (LISTP Form)
                             (FMEMB (CAR Form)
                                    (QUOTE (DEFINE-FILE-INFO *)))))
                   then (HT.EVAL Form)))
         (CLOSEF S))))

(HT.EVAL
  (LAMBDA (Form)
    (* "Evaluate Form, echoing it and its value (or the error) to the transcript.
        Returns the value, or NIL on error.")
    (if HT.ECHO
        then (HT.SHOW Form "> "))
    (XCL:CONDITION-CASE (LET ((V (EVAL Form)))
                          (if HT.ECHO
                              then (HT.SHOW V "= "))
                          V)
           (CL:ERROR (C)
                  (HT.LOG (CONCAT "ERROR: " (HT.ERRSTRING C)))
                  NIL))))

(HT.CHECK
  (NLAMBDA (Label Form Expected)
    (* "(HT.CHECK label form [expected])  -- PASS if form evaluates non-NIL (or EQUAL to
        the evaluated Expected, when given).  Errors count as FAIL.")
    (LET* ((Err NIL)
           (V (XCL:CONDITION-CASE (EVAL Form)
                     (CL:ERROR (C)
                            (SETQ Err (HT.ERRSTRING C))
                            NIL)))
           (Want (AND Expected (EVAL Expected)))
           (OK (AND (NOT Err)
                    (if Expected
                        then (EQUAL V Want)
                      else V))))
          (if OK
              then (SETQ HT.PASS (ADD1 HT.PASS))
                   (HT.LOG (CONCAT "PASS " Label))
            else (SETQ HT.FAIL (ADD1 HT.FAIL))
                 (HT.LOG (CONCAT "FAIL " Label (if Err
                                                   then (CONCAT "  -- ERROR: " Err)
                                                 else "")))
                 (if (NOT Err)
                     then (HT.SHOW V "   got: ")
                          (if Expected
                              then (HT.SHOW Want "  want: "))))
          OK)))

(HT.SNAP
  (LAMBDA (Name)
    (* "Ask the host-side runner to screenshot the virtual display as <Name>.png.
        Drops a request file and waits (up to ~15s) for the runner to consume it.")
    (if HT.SNAPDIR
        then (LET ((Req (CONCAT HT.SNAPDIR Name ".req")))
                  (CLOSEF (OPENSTREAM Req (QUOTE OUTPUT)
                                 (QUOTE NEW)))
                  (for i from 1 to 75 while (INFILEP Req) do (DISMISS 200))
                  (HT.LOG (CONCAT "SNAP " Name ".png"))))
    Name))

(HT.AUTOPLACE
  (LAMBDA NIL
    (* "Headless there is no one to sweep out window positions, so answer GETBOXREGION /
        GETREGION prompts with cascading regions down the screen.")
    (SETQ HT.NEXTPLACE 0)
    (ADVISE (QUOTE GETBOXREGION) (QUOTE BEFORE) (QUOTE (RETURN (HT.NEXTREGION WIDTH HEIGHT))))
    (ADVISE (QUOTE GETREGION) (QUOTE BEFORE) (QUOTE (RETURN (HT.NEXTREGION (OR MINWIDTH 300) (OR MINHEIGHT 200)))))
    T))

(HT.NEXTREGION
  (LAMBDA (W H)
    (LET ((X (PLUS 20 (TIMES 330 (IREMAINDER HT.NEXTPLACE 3))))
          (Y (DIFFERENCE (DIFFERENCE SCREENHEIGHT (OR H 200)) (PLUS 40 (TIMES 330 (IREMAINDER (IQUOTIENT HT.NEXTPLACE 3) 3))))))
         (SETQ HT.NEXTPLACE (ADD1 HT.NEXTPLACE))
         (CREATEREGION X (MAX 0 Y) (OR W 300) (OR H 200)))))

(HT.LOADLOOPS
  (LAMBDA NIL
    (* "Load LOOPS (github.com/Interlisp/loops) from $LOOPSDIR/system.  LOADLOOPS wants
        the XCL package context; binding *PACKAGE* here is enough.")
    (LET ((Dir (CONCAT "{DSK}" (UNIX-GETENV "LOOPSDIR")
                      "/system/")))
         (CNDIR Dir)
         (LET ((*PACKAGE* (CL:FIND-PACKAGE "XCL-USER")))
              (DECLARE (SPECVARS *PACKAGE*))
              (FILESLOAD LOADLOOPS)
              (LOADLOOPS))
         (CNDIR (UNIX-GETENV "HTWORKDIR"))
         (AND (GETD (QUOTE $!))
              (QUOTE LOOPS-LOADED)))))
)
STOP
