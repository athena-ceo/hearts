;; KEELOOPS -- a small KEE compatibility layer built on LOOPS, for Medley Interlisp.
;;
;; The 1986 HEARTS Expert Player was written against IntelliCorp KEE: units with
;; (multi-valued) slots, message handlers, and RuleSystem2 backward-chaining rules with
;; weights and EMYCIN certainty factors.  KEE is gone.  This file re-provides the part
;; of the KEE API that the Expert Player uses, on top of Xerox LOOPS
;; (github.com/Interlisp/loops), so the ORIGINAL EP.* code and the ORIGINAL rules run
;; essentially unchanged.
;;
;;   KEE concept                     LOOPS realisation
;;   -------------------------       ------------------------------------------------
;;   unit                            LOOPS instance of a subclass of KEE.Unit, named
;;                                   with SetName so ($ name) / GetObjectRec find it
;;   class unit (e.g. histories)     instance of a KEE.ClassUnit subclass; its members
;;                                   are instances of its KEE.MemberClass
;;   slot                            LOOPS instance variable (IV)
;;   multi-valued slot               IV whose Cardinality property is Multiple
;;   message handler                 LOOPS method (generated wrapper -> EP.* function)
;;   UNCERTAIN.VALUES facet (CFs)    KEE.Facets IV: ((slot (value . cf) ...) ...)
;;   rule class / rule               KEE.DEFRULE data, run by QUERY (below)
;;
;; Rule semantics (from the rules themselves and the 1986 overview, section 4.1.2):
;;   * QUERY backward-chains: a rule applies when its conclusion unifies with the goal;
;;     that unification is what binds ?Self in rules like ote.no.shooting.
;;   * Rules are tried in descending WEIGHT order (listing order breaks ties).
;;   * (QUERY goal 1 class) stops at the first rule that succeeds; (QUERY goal 'ALL
;;     class) fires every rule that succeeds -- used with :UPDATE certainty factors.
;;   * Premises are proved left to right with backtracking; OR tries branches in order.
;;     Premises can have side effects (the pass-out rules call DoPass), so order matters.
;;   * (THE slot OF unit IS x) matches slot values; if the slot is empty, rules in the
;;     current class that conclude that slot are chained on to derive it.
;;   * A premise whose operator is not a defined Lisp function is an "unstructured
;;     fact" (e.g. (Poor Spades Protection)), proved from asserted facts or by chaining.
;;   * (EQUAL ?unbound expr) binds the variable -- the rules use it as LET.
;;   * A Lisp premise that signals an error fails (the rule is skipped); the error is
;;     recorded in KEE.RuleErrors so it isn't silently lost.
;;   * ?variables are matched case-insensitively (the listing mixes ?self and ?Self
;;     within single rules; see HEARTS-BUGS.md).

(DEFINE-FILE-INFO :PACKAGE "INTERLISP" :READTABLE "INTERLISP" :BASE 10)

(* "KEELOOPS -- KEE compatibility layer on LOOPS.  Requires LOOPS to be loaded.")

(DEFINEQ

(KEE.EnsureLOOPS
  (LAMBDA NIL
    (* ; "LOOPS isn't part of the Medley release; it lives at github.com/Interlisp/loops.  If it isn't loaded yet, look for a checkout: $LOOPSDIR, then loops/ beside the medley/ directory (like notecards/), then ~/loops.  LOADLOOPS expects the XCL package.")
    (OR (GETD (QUOTE DefineClass))
        (LET ((Dir (for D in (LIST (UNIX-GETENV "LOOPSDIR")
                                   (AND (UNIX-GETENV "MEDLEYDIR") (CONCAT (UNIX-GETENV "MEDLEYDIR") "/../loops"))
                                   (AND (UNIX-GETENV "HOME") (CONCAT (UNIX-GETENV "HOME") "/loops")))
                      when (AND D (INFILEP (CONCAT "{DSK}" D "/system/LOADLOOPS")))
                      do (RETURN (CONCAT "{DSK}" D "/system/"))))
              (Here (DIRECTORYNAME T)))
             (if (NULL Dir)
                 then (ERROR "KEELOOPS needs LOOPS (github.com/Interlisp/loops).  Clone it beside medley/ (or set LOOPSDIR), or load it first:  (CNDIR <loops>/system/) (FILESLOAD LOADLOOPS) (LOADLOOPS)"))
             (CNDIR Dir)
             (RESETLST
                 (RESETSAVE NIL (LIST (QUOTE CNDIR) Here))
                 (LET ((*PACKAGE* (CL:FIND-PACKAGE "XCL-USER")))
                      (DECLARE (SPECVARS *PACKAGE*))
                      (FILESLOAD LOADLOOPS)
                      (LOADLOOPS)))
             (GETD (QUOTE DefineClass))))))
)

(KEE.EnsureLOOPS)

(RPAQ? KEE.RuleClasses NIL)
(RPAQ? KEE.Facts NIL)
(RPAQ? KEE.RuleErrors NIL)
(RPAQ? KEE.Trace NIL)
(RPAQ? KEE.TraceStream T)
(RPAQ? KEE.Fired NIL)
(RPAQ? KEE.CurrentRuleClass NIL)
(RPAQ? KEE.ClassIVCache (HASHARRAY 20))
(RPAQ? *PROOF.CONSISTENCY.CHECKING* NIL)
(RPAQQ KEE.FAIL KEE.FAIL)

(DEFCLASS KEE.Unit
   (MetaClass Class) (Supers Object)
   (InstanceVariables (KEE.Parent NIL) (KEE.Facets NIL)))

(DEFCLASS KEE.ClassUnit
   (MetaClass Class) (Supers KEE.Unit)
   (InstanceVariables (KEE.MemberClass NIL) (KEE.Members NIL)))


(* ;;; "Units")
(DEFINEQ

(KEE.Resolve
  (LAMBDA (Ref NoError)
    (* ; "A unit reference -> the LOOPS object.  Accepts an object, a unit name, or KEE's (name kb) list.")
    (COND
       ((type? instance Ref) Ref)
       ((LISTP Ref) (KEE.Resolve (CAR Ref) NoError))
       ((AND Ref (LITATOM Ref) (GetObjectRec Ref)))
       (NoError NIL)
       (T (ERROR "KEE: no such unit" Ref)))))

(KEE.ClassIVs
  (LAMBDA (Class)
    (OR (GETHASH Class KEE.ClassIVCache)
        (PUTHASH Class (_ Class ListAttribute! (QUOTE IVs)) KEE.ClassIVCache))))

(KEE.CheckSlot
  (LAMBDA (Obj Slot)
    (* ; "LOOPS drops into an interactive IVMissing handler on unknown IVs; fail cleanly instead.")
    (OR (FMEMB Slot (KEE.ClassIVs (Class Obj)))
        (ERROR (CONCAT "KEE: unit " (UNIT.NAME Obj) " has no slot") Slot))
    Obj))

(KEE.Multiple?
  (LAMBDA (Obj Slot)
    (EQ (GetValue Obj Slot (QUOTE Cardinality)) (QUOTE Multiple))))

(KEE.ValueEqual
  (LAMBDA (A B)
    (* ; "EQUAL, except that a unit and its name are the same value.")
    (OR (EQUAL A B)
        (AND (type? instance A) B (LITATOM B) (EQ A (GetObjectRec B)))
        (AND (type? instance B) A (LITATOM A) (EQ B (GetObjectRec A))))))

(UNIT.NAME
  (LAMBDA (Unit)
    (COND
       ((NULL Unit) NIL)
       ((LITATOM Unit) Unit)
       ((LISTP Unit) (CAR Unit))
       ((type? instance Unit) (CAR (GetObjectNames Unit)))
       (T Unit))))

(UNITCREATE
  (LAMBDA (Name Superclasses MemberOf Doc Extra)
    (* ; "Make a new unit, a MEMBER of the class unit MemberOf, named Name.")
    (LET* ((Parent (KEE.Resolve MemberOf))
           (Obj (_ (GetObjectRec (GetValue Parent (QUOTE KEE.MemberClass))) New))
           (Old (GetObjectRec Name)))
          (if (AND Old (NEQ Old Obj))
              then (UNITDELETE Old))
          (_ Obj SetName Name)
          (PutValue Obj (QUOTE KEE.Parent) Parent)
          (PutValue Parent (QUOTE KEE.Members) (CONS Obj (GetValue Parent (QUOTE KEE.Members))))
          Obj)))

(UNITDELETE
  (LAMBDA (Unit)
    (LET ((Obj (KEE.Resolve Unit T))
          Parent)
         (if Obj
             then (SETQ Parent (GetValue Obj (QUOTE KEE.Parent)))
                  (if Parent
                      then (PutValue Parent (QUOTE KEE.Members)
                                  (DREMOVE Obj (GetValue Parent (QUOTE KEE.Members)))))
                  (for N in (GetObjectNames Obj) when (LITATOM N) do (_ Obj UnSetName N))
                  T))))

(UNIT.CHILDREN
  (LAMBDA (Unit Relation)
    (REVERSE (GetValue (KEE.Resolve Unit) (QUOTE KEE.Members)))))

(UNIT.ALLCHILDREN
  (LAMBDA (Unit Relation)
    (UNIT.CHILDREN Unit Relation)))

(KEE.MakeUnit
  (LAMBDA (ClassName UnitName)
    (* ; "Create a free-standing named unit (a class unit, a strategy, a personality).")
    (LET ((Obj (_ (GetObjectRec ClassName) New))
          (Old (GetObjectRec UnitName)))
         (if Old then (UNITDELETE Old))
         (_ Obj SetName UnitName)
         Obj)))

)

(* ;;; "Slots")
(DEFINEQ

(GET.VALUES
  (LAMBDA (Unit Slot)
    (LET* ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot))
           (V (GetValue Obj Slot)))
          (if (KEE.Multiple? Obj Slot)
              then V
            elseif V
              then (LIST V)
            else NIL))))

(GET.VALUE
  (LAMBDA (Unit Slot)
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot)))
         (if (KEE.Multiple? Obj Slot)
             then (CAR (GetValue Obj Slot))
           else (GetValue Obj Slot)))))

(PUT.VALUE
  (LAMBDA (Unit Slot Value)
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot)))
         (PutValue Obj Slot (if (AND (KEE.Multiple? Obj Slot) Value)
                                then (LIST Value)
                              else Value))
         Value)))

(PUT.VALUES
  (LAMBDA (Unit Slot Values)
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot)))
         (PutValue Obj Slot (if (KEE.Multiple? Obj Slot)
                                then (APPEND Values)
                              else (CAR Values)))
         Values)))

(ADD.VALUE
  (LAMBDA (Unit Slot Value SlotType ValueType Duplicates?)
    (* ; "KEE slots are sets, so an EQUAL value isn't added twice unless the sixth argument is true (as the EP code passes for Reasons and TricksWon).  Newest value first: EP.LastCardPlayed takes the CAR.")
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot))
          Cur)
         (if (KEE.Multiple? Obj Slot)
             then (SETQ Cur (GetValue Obj Slot))
                  (if (OR Duplicates? (NOT (MEMBER Value Cur)))
                      then (PutValue Obj Slot (CONS Value Cur)))
           else (PutValue Obj Slot Value))
         Value)))

(ADD.VALUES
  (LAMBDA (Unit Slot Values)
    (for V in Values do (ADD.VALUE Unit Slot V))
    Values))

(REMOVE.VALUE
  (LAMBDA (Unit Slot Value)
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot)))
         (if (KEE.Multiple? Obj Slot)
             then (PutValue Obj Slot (REMOVE Value (GetValue Obj Slot)))
           elseif (EQUAL Value (GetValue Obj Slot))
             then (PutValue Obj Slot NIL))
         Value)))

(REMOVE.ALL.LOCAL.VALUES
  (LAMBDA (Unit Slot)
    (PutValue (KEE.CheckSlot (KEE.Resolve Unit) Slot) Slot NIL)
    NIL))

(REPLACE.VALUE
  (LAMBDA (Unit Slot Old New SlotType Extra)
    (* ; "Replace Old by New; if Old isn't there, New is added.")
    (LET ((Obj (KEE.CheckSlot (KEE.Resolve Unit) Slot))
          Cur)
         (if (KEE.Multiple? Obj Slot)
             then (SETQ Cur (GetValue Obj Slot))
                  (PutValue Obj Slot (if (MEMBER Old Cur)
                                         then (for V in Cur collect (if (EQUAL V Old) then New else V))
                                       else (CONS New Cur)))
           else (PutValue Obj Slot New))
         New)))

(REMOVE.FACET
  (LAMBDA (Unit Slot Facet)
    (LET ((Obj (KEE.Resolve Unit)))
         (if (EQ Facet (QUOTE UNCERTAIN.VALUES))
             then (PutValue Obj (QUOTE KEE.Facets)
                         (for F in (GetValue Obj (QUOTE KEE.Facets)) collect F unless (EQ (CAR F) Slot))))
         NIL)))

)

(* ;;; "Certainty factors (the UNCERTAIN.VALUES facet)")
(DEFINEQ

(KEE.CF.Get
  (LAMBDA (Unit Slot Value)
    (LET ((Entry (CDR (FASSOC Slot (GetValue (KEE.Resolve Unit) (QUOTE KEE.Facets))))))
         (CDR (for P in Entry thereis (KEE.ValueEqual (CAR P) Value))))))

(KEE.CF.Combine
  (LAMBDA (Old New)
    (* ; "EMYCIN parallel combination of two certainty factors.")
    (COND
       ((NULL Old) New)
       ((AND (GEQ Old 0) (GEQ New 0)) (PLUS Old (TIMES New (DIFFERENCE 1 Old))))
       ((AND (LESSP Old 0) (LESSP New 0)) (PLUS Old (TIMES New (PLUS 1 Old))))
       (T (LET ((Den (DIFFERENCE 1 (MIN (ABS Old) (ABS New)))))
               (if (ZEROP Den)
                   then 0
                 else (QUOTIENT (PLUS Old New) Den)))))))

(KEE.CF.Update
  (LAMBDA (Unit Slot Value CF)
    (LET* ((Obj (KEE.Resolve Unit))
           (Facets (GetValue Obj (QUOTE KEE.Facets)))
           (Entry (FASSOC Slot Facets))
           (Pair (for P in (CDR Entry) thereis (KEE.ValueEqual (CAR P) Value)))
           (New (KEE.CF.Combine (CDR Pair) CF)))
          (if Pair
              then (RPLACD Pair New)
            elseif Entry
              then (NCONC1 Entry (CONS Value New))
            else (PutValue Obj (QUOTE KEE.Facets) (CONS (LIST Slot (CONS Value New)) Facets)))
          New)))

)

(* ;;; "Messages")
(DEFINEQ

(KEE.Send
  (LAMBDA (Unit Msg Args)
    (LET* ((Obj (KEE.Resolve Unit))
           (Fn (FetchMethod (Class Obj) Msg)))
          (if Fn
              then (APPLY Fn (CONS Obj Args))
            else (ERROR (CONCAT "KEE: unit " (UNIT.NAME Obj) " has no handler for message") Msg)))))

(UNITMSG
  (LAMBDA Args
    (KEE.Send (ARG Args 1) (ARG Args 2) (for I from 3 to Args collect (ARG Args I)))))

(UNITMSG*
  (LAMBDA (Unit Msg ArgList)
    (KEE.Send Unit Msg ArgList)))

(KEE.DefHandler
  (LAMBDA (ClassName Msg Fn)
    (* ; "Install function Fn (whose first argument is the unit) as the handler for Msg on units of LOOPS class ClassName.  LOOPS wants method functions named Class.Selector, so we generate one that calls Fn.")
    (LET ((Args (CONS (QUOTE self) (CDR (ARGLIST Fn)))))
         (EVAL (LIST (QUOTE Method) (CONS (LIST ClassName Msg) Args) (CONS Fn Args)))
         Msg)))

(GLOBAL.FLAG.SET
  (LAMBDA (Flag Value)
    (SET Flag Value)))

)

(* ;;; "Rules")
(DEFINEQ

(KEE.Var?
  (LAMBDA (X)
    (AND X (LITATOM X) (EQ (NTHCHAR X 1) (QUOTE ?)) (IGREATERP (NCHARS X) 1))))

(KEE.Canon
  (LAMBDA (Form)
    (* ; "Upper-case every ?variable, so ?self and ?Self are one variable.")
    (COND
       ((KEE.Var? Form) (U-CASE Form))
       ((NLISTP Form) Form)
       ((EQ (CAR Form) (QUOTE QUOTE)) Form)
       (T (CONS (KEE.Canon (CAR Form)) (KEE.Canon (CDR Form)))))))

(KEE.Word?
  (LAMBDA (X Word)
    (AND X (LITATOM X) (EQ (U-CASE X) Word))))

(KEE.Article?
  (LAMBDA (X)
    (* ; "THE / A / AN introduce a slot pattern; a goal (THE s OF u IS ?v) matches a conclusion (A s OF u IS v).")
    (OR (KEE.Word? X (QUOTE THE)) (KEE.Word? X (QUOTE A)) (KEE.Word? X (QUOTE AN)))))

(KEE.DEFRULE
  (LAMBDA (ClassName RuleName Weight IfForm)
    (* ; "(IF premise THEN conclusion [DO action]) -> rule record, filed in ClassName by weight.")
    (LET* ((F (KEE.Canon IfForm))
           (Then (for Tail on F thereis (KEE.Word? (CAR Tail) (QUOTE THEN))))
           (Do (for Tail on F thereis (KEE.Word? (CAR Tail) (QUOTE DO))))
           (Rule (LIST RuleName Weight (CADR F) (CADR Then) (CADR Do) ClassName))
           (Entry (FASSOC ClassName KEE.RuleClasses)))
          (if (NOT (AND (KEE.Word? (CAR F) (QUOTE IF)) Then))
              then (ERROR "KEE.DEFRULE: not an (IF .. THEN ..) rule" RuleName))
          (if (NULL Entry)
              then (SETQ Entry (LIST ClassName))
                   (SETQ KEE.RuleClasses (NCONC1 KEE.RuleClasses Entry)))
          (RPLACD Entry (for R in (CDR Entry) collect R unless (EQ (CAR R) RuleName)))
          (RPLACD Entry (KEE.InsertByWeight Rule (CDR Entry)))
          RuleName)))

(KEE.InsertByWeight
  (LAMBDA (Rule Rules)
    (if (OR (NULL Rules) (GREATERP (CADR Rule) (CADR (CAR Rules))))
        then (CONS Rule Rules)
      else (CONS (CAR Rules) (KEE.InsertByWeight Rule (CDR Rules))))))

(KEE.RulesOf
  (LAMBDA (Class)
    (CDR (FASSOC (if (LISTP Class) then (CAR Class) else Class) KEE.RuleClasses))))

(KEE.Lookup
  (LAMBDA (Var Env)
    (* ; "-> (Var . value) when bound, else NIL.")
    (FASSOC Var Env)))

(KEE.Bind
  (LAMBDA (Var Value Env)
    (CONS (CONS Var Value) Env)))

(KEE.Instantiate
  (LAMBDA (Form Env)
    (* ; "A rule expression -> an evaluable Lisp form: bound variables become quoted values, THE-terms become slot lookups.")
    (COND
       ((KEE.Var? Form)
        (LET ((B (KEE.Lookup Form Env)))
             (if B
                 then (LIST (QUOTE QUOTE) (CDR B))
               else (ERROR "KEE: unbound variable" Form))))
       ((NLISTP Form) Form)
       ((EQ (CAR Form) (QUOTE QUOTE)) Form)
       ((KEE.TheTerm? Form)
        (LIST (QUOTE KEE.TheValue) (KWOTE (CADR Form)) (KEE.Instantiate (CADDDR Form) Env)))
       (T (for X in Form collect (KEE.Instantiate X Env))))))

(KEE.TheTerm?
  (LAMBDA (Form)
    (* ; "(THE slot OF unit) -- also tolerates the listing's stray trailing IS, (THE slot OF unit IS).")
    (AND (LISTP Form)
         (KEE.Word? (CAR Form) (QUOTE THE))
         (KEE.Word? (CADDR Form) (QUOTE OF))
         (OR (NULL (CDDDDR Form))
             (AND (KEE.Word? (CAR (CDDDDR Form)) (QUOTE IS)) (NULL (CDR (CDDDDR Form))))))))

(KEE.TheValue
  (LAMBDA (Slot Unit)
    (LET ((Obj (KEE.Resolve Unit)))
         (if (KEE.Multiple? (KEE.CheckSlot Obj Slot) Slot)
             then (GET.VALUES Obj Slot)
           else (GET.VALUE Obj Slot)))))

(KEE.Eval
  (LAMBDA (Form Env)
    (EVAL (KEE.Instantiate Form Env))))

(KEE.Value
  (LAMBDA (Term Env)
    (* ; "The value of a term in pattern position: variable, constant symbol, number, or expression.")
    (COND
       ((KEE.Var? Term) (CDR (OR (KEE.Lookup Term Env) (ERROR "KEE: unbound variable" Term))))
       ((LISTP Term) (KEE.Eval Term Env))
       (T Term))))

(KEE.Try
  (LAMBDA (Rule Form Env)
    (* ; "Evaluate Form under Env.  An error fails the premise and is recorded against the rule.")
    (XCL:CONDITION-CASE (LIST (KEE.Eval Form Env))
           (CL:ERROR (C)
                  (KEE.NoteError Rule Form C)
                  NIL))))

(KEE.NoteError
  (LAMBDA (Rule Form Condition)
    (LET ((Msg (XCL:CONDITION-CASE (CL:FORMAT NIL "~A" Condition)
                      (CL:ERROR NIL "<error>"))))
         (push KEE.RuleErrors (LIST (CAR Rule) (CADR (CDDDDR Rule)) Msg))
         (if KEE.Trace
             then (printout KEE.TraceStream "   ! " (CAR Rule) ": " Msg T)))))

)

(* ;;; "Premises")
(DEFINEQ

(KEE.GoalKind
  (LAMBDA (G)
    (LET ((Op (CAR G)))
         (COND
            ((NLISTP G) (QUOTE LISP))
            ((FMEMB Op (QUOTE (AND OR NOT))) Op)
            ((AND (KEE.Word? Op (QUOTE THE)) (KEE.Word? (CADR G) (QUOTE CERTAINTY))) (QUOTE CERTAINTY))
            ((AND (OR (KEE.Word? Op (QUOTE THE)) (KEE.Word? Op (QUOTE A)) (KEE.Word? Op (QUOTE AN)))
                  (KEE.Word? (CADDR G) (QUOTE OF))
                  (CDDDDR G)
                  (KEE.Word? (CAR (CDDDDR G)) (QUOTE IS)))
             (QUOTE SLOT))
            ((AND Op (LITATOM Op) (NOT (KEE.Var? Op)) (CL:FBOUNDP Op)) (QUOTE LISP))
            (T (QUOTE FACT))))))

(KEE.Solve
  (LAMBDA (Goals Env Rule)
    (* ; "Prove Goals left to right with backtracking.  -> the extended Env, or KEE.FAIL.  Goals still to be proved are passed along as data (no closures), so OR and multi-valued slots can backtrack into the remaining premises.")
    (if (NULL Goals)
        then Env
      else (LET ((G (CAR Goals))
                 (Rest (CDR Goals)))
                (SELECTQ (KEE.GoalKind G)
                    (AND (KEE.Solve (APPEND (CDR G) Rest) Env Rule))
                    (OR (for B in (CDR G) bind R
                           do (SETQ R (KEE.Solve (CONS B Rest) Env Rule))
                              (if (NEQ R KEE.FAIL) then (RETURN R))
                           finally (RETURN KEE.FAIL)))
                    (NOT (if (EQ (KEE.Solve (CDR G) Env Rule) KEE.FAIL)
                             then (KEE.Solve Rest Env Rule)
                           else KEE.FAIL))
                    (SLOT (for E in (KEE.MatchSlot G Env Rule) bind R
                             do (SETQ R (KEE.Solve Rest E Rule))
                                (if (NEQ R KEE.FAIL) then (RETURN R))
                             finally (RETURN KEE.FAIL)))
                    (CERTAINTY (LET ((E (KEE.MatchCertainty G Env Rule)))
                                    (if (EQ E KEE.FAIL)
                                        then KEE.FAIL
                                      else (KEE.Solve Rest E Rule))))
                    (FACT (if (KEE.ProveFact (KEE.Subst G Env) Rule)
                              then (KEE.Solve Rest Env Rule)
                            else KEE.FAIL))
                    (LET ((E (KEE.MatchLisp G Env Rule)))
                         (if (EQ E KEE.FAIL)
                             then KEE.FAIL
                           else (KEE.Solve Rest E Rule))))))))

(KEE.MatchLisp
  (LAMBDA (G Env Rule)
    (* ; "(EQUAL ?unbound expr) binds; any other Lisp form must evaluate non-NIL.")
    (LET (Var Expr V)
         (if (AND (EQ (CAR G) (QUOTE EQUAL)) (KEE.Var? (CADR G)) (NOT (KEE.Lookup (CADR G) Env)))
             then (SETQ Var (CADR G)) (SETQ Expr (CADDR G))
           elseif (AND (EQ (CAR G) (QUOTE EQUAL)) (KEE.Var? (CADDR G)) (NOT (KEE.Lookup (CADDR G) Env)))
             then (SETQ Var (CADDR G)) (SETQ Expr (CADR G)))
         (SETQ V (KEE.Try Rule (OR Expr G) Env))
         (COND
            ((NULL V) KEE.FAIL)
            (Var (KEE.Bind Var (CAR V) Env))
            ((CAR V) Env)
            (T KEE.FAIL)))))

(KEE.SlotParts
  (LAMBDA (G)
    (* ; "(THE|A slot OF unit IS value) -> (slot unit value)")
    (LIST (CADR G) (CADDDR G) (CADR (CDDDDR G)))))

(KEE.MatchSlot
  (LAMBDA (G Env Rule)
    (* ; "-> list of environments, one per matching slot value (so an unbound ?x enumerates a multi-valued slot).")
    (LET* ((Parts (KEE.SlotParts G))
           (Slot (CAR Parts))
           (ValTerm (CADDR Parts))
           (Unit (KEE.Try Rule (KEE.UnitForm (CADR Parts)) Env))
           Obj Values Want)
          (SETQ Obj (AND Unit (KEE.Resolve (CAR Unit) T)))
          (if (OR (NULL Obj) (NOT (FMEMB Slot (KEE.ClassIVs (Class Obj)))))
              then (if Unit then (KEE.NoteError Rule G (CONCAT "no unit/slot for " Slot)))
                   NIL
            else (SETQ Values (GET.VALUES Obj Slot))
                 (if (AND (NULL Values) (KEE.ChainSlot Obj Slot Rule))
                     then (SETQ Values (GET.VALUES Obj Slot)))
                 (COND
                    ((AND (KEE.Var? ValTerm) (NOT (KEE.Lookup ValTerm Env)))
                     (for V in Values collect (KEE.Bind ValTerm V Env)))
                    ((NULL (SETQ Want (KEE.Try Rule (KEE.ValueForm ValTerm) Env))) NIL)
                    ((for V in Values thereis (KEE.ValueEqual V (CAR Want))) (LIST Env))
                    (T NIL))))))

(KEE.UnitForm
  (LAMBDA (Term)
    (* ; "A unit position holds a variable, a unit name, or a THE-term / expression.")
    (if (AND Term (LITATOM Term) (NOT (KEE.Var? Term)))
        then (KWOTE Term)
      else Term)))

(KEE.ValueForm
  (LAMBDA (Term)
    (if (AND Term (LITATOM Term) (NOT (KEE.Var? Term)))
        then (KWOTE Term)
      else Term)))

(KEE.MatchCertainty
  (LAMBDA (G Env Rule)
    (* ; "(THE CERTAINTY THAT THE slot OF unit IS value IS cf) -- an unknown CF is 0.")
    (LET* ((Inner (CDDDR G))
           (Parts (KEE.SlotParts Inner))
           (CFTerm (CADDDR (CDDDDR Inner)))
           (Unit (KEE.Try Rule (KEE.UnitForm (CADR Parts)) Env))
           (Val (AND Unit (KEE.Try Rule (KEE.ValueForm (CADDR Parts)) Env)))
           CF Want)
          (if (NOT (AND Unit Val (KEE.Resolve (CAR Unit) T)))
              then KEE.FAIL
            else (SETQ CF (OR (KEE.CF.Get (CAR Unit) (CAR Parts) (CAR Val)) 0))
                 (COND
                    ((AND (KEE.Var? CFTerm) (NOT (KEE.Lookup CFTerm Env))) (KEE.Bind CFTerm CF Env))
                    ((AND (SETQ Want (KEE.Try Rule (KEE.ValueForm CFTerm) Env)) (EQUAL CF (CAR Want))) Env)
                    (T KEE.FAIL))))))

(KEE.Subst
  (LAMBDA (Form Env)
    (* ; "Replace bound variables by their values (for facts); unbound ones stay.")
    (COND
       ((KEE.Var? Form) (LET ((B (KEE.Lookup Form Env))) (if B then (CDR B) else Form)))
       ((NLISTP Form) Form)
       (T (CONS (KEE.Subst (CAR Form) Env) (KEE.Subst (CDR Form) Env))))))

(KEE.FactMatch?
  (LAMBDA (Pattern Fact)
    (AND (EQ (LENGTH Pattern) (LENGTH Fact))
         (for P in Pattern as F in Fact always (OR (KEE.Var? P) (KEE.ValueEqual P F))))))

(KEE.ProveFact
  (LAMBDA (Fact Rule)
    (* ; "An unstructured fact holds if asserted, or if a rule of the current class concludes it.")
    (OR (for F in KEE.Facts thereis (KEE.FactMatch? Fact F))
        (AND KEE.CurrentRuleClass
             (for R in (KEE.RulesOf KEE.CurrentRuleClass)
                thereis (AND (NEQ R Rule)
                             (EQ (KEE.GoalKind (CADDDR R)) (QUOTE FACT))
                             (KEE.FactMatch? Fact (CADDDR R))
                             (KEE.FireRule R Fact)))))))

(KEE.ChainSlot
  (LAMBDA (Obj Slot Rule)
    (* ; "Derive an empty slot from rules of the current class that conclude it.")
    (AND KEE.CurrentRuleClass
         (LET ((Goal (LIST (QUOTE THE) Slot (QUOTE OF) (UNIT.NAME Obj) (QUOTE IS) (QUOTE ?VALUE))))
              (for R in (KEE.RulesOf KEE.CurrentRuleClass)
                 thereis (AND (NEQ R Rule)
                              (EQ (KEE.GoalKind (CADDDR R)) (QUOTE SLOT))
                              (EQ (CADR (CADDDR R)) Slot)
                              (KEE.FireRule R Goal)))))))

(ASSERT.UNKNOWN
  (LAMBDA (Fact)
    (SETQ KEE.Facts (for F in KEE.Facts collect F unless (KEE.FactMatch? Fact F)))
    NIL))

)

(* ;;; "Firing rules")
(DEFINEQ

(KEE.Unify
  (LAMBDA (Goal Concl)
    (* ; "Match a query goal against a rule conclusion.  Goal constants bind the rule's variables (this is how ?Self gets bound); goal variables are unconstrained.  -> Env or KEE.FAIL.")
    (LET ((Env NIL))
         (if (NEQ (LENGTH Goal) (LENGTH Concl))
             then KEE.FAIL
           elseif (for G in Goal as C in Concl
                     always (COND
                               ((KEE.Var? G) T)
                               ((KEE.Var? C) (LET ((B (KEE.Lookup C Env)))
                                                  (if B
                                                      then (KEE.ValueEqual (CDR B) G)
                                                    else (SETQ Env (KEE.Bind C G Env))
                                                         T)))
                               ((LISTP C) T)
                               ((AND (KEE.Article? G) (KEE.Article? C)) T)
                               (T (OR (KEE.ValueEqual G C) (AND (LITATOM G) (LITATOM C) (EQ (U-CASE G) (U-CASE C)))))))
             then Env
           else KEE.FAIL))))

(KEE.Conclude
  (LAMBDA (Concl Env Rule Goal)
    (* ; "Assert the conclusion.  -> T, or NIL if it can't be (value unbound, NIL, or not what the goal asked for).")
    (SELECTQ (KEE.GoalKind Concl)
        (SLOT (LET* ((Parts (KEE.SlotParts Concl))
                     (Unit (KEE.Try Rule (KEE.UnitForm (CADR Parts)) Env))
                     (Val (AND Unit (KEE.Try Rule (KEE.ValueForm (CADDR Parts)) Env)))
                     (Wanted (CADR (CDDDDR Goal))))
                    (COND
                       ((NOT (AND Unit Val (CAR Val))) NIL)
                       ((AND Goal (NOT (KEE.Var? Wanted)) (NOT (KEE.ValueEqual Wanted (CAR Val)))) NIL)
                       (T (if (KEE.Word? (CAR Concl) (QUOTE THE))
                              then (PUT.VALUE (CAR Unit) (CAR Parts) (CAR Val))
                            else (ADD.VALUE (CAR Unit) (CAR Parts) (CAR Val)))
                          T))))
        (CERTAINTY (LET* ((Inner (CDDDR Concl))
                          (Parts (KEE.SlotParts Inner))
                          (Unit (KEE.Try Rule (KEE.UnitForm (CADR Parts)) Env))
                          (Val (AND Unit (KEE.Try Rule (KEE.ValueForm (CADDR Parts)) Env)))
                          (CF (AND Val (KEE.Try Rule (KEE.ValueForm (CADDDR (CDDDDR Inner))) Env))))
                         (if (AND Unit Val CF (NUMBERP (CAR CF)))
                             then (KEE.CF.Update (CAR Unit) (CAR Parts) (CAR Val) (CAR CF))
                                  T)))
        (FACT (push KEE.Facts (KEE.Subst Concl Env))
              T)
        NIL)))

(KEE.FireRule
  (LAMBDA (Rule Goal)
    (* ; "Try one rule for Goal: unify, prove the premise, assert the conclusion, run the DO action.  -> T if it fired.")
    (LET ((Env (KEE.Unify Goal (CADDDR Rule)))
          Action)
         (if (AND (NEQ Env KEE.FAIL)
                  (NEQ (SETQ Env (KEE.Solve (LIST (CADDR Rule)) Env Rule)) KEE.FAIL)
                  (KEE.Conclude (CADDDR Rule) Env Rule Goal))
             then (push KEE.Fired (CAR Rule))
                  (if KEE.Trace
                      then (printout KEE.TraceStream "   fired " (CAR Rule) " (" (CADR (CDDDDR Rule)) ")" T))
                  (if (SETQ Action (CAR (CDDDDR Rule)))
                      then (KEE.Try Rule Action Env))
                  T))))

(KEE.Known?
  (LAMBDA (Goal)
    (* ; "Backward chaining starts from what is already known: a fact that is asserted, or a slot that already has a matching value.")
    (SELECTQ (KEE.GoalKind Goal)
        (FACT (for F in KEE.Facts thereis (KEE.FactMatch? Goal F)))
        (SLOT (LET* ((Parts (KEE.SlotParts Goal))
                     (Obj (KEE.Resolve (CADR Parts) T))
                     (Values (AND Obj (GET.VALUES Obj (CAR Parts)))))
                    (AND Values (OR (KEE.Var? (CADDR Parts))
                                    (for V in Values thereis (KEE.ValueEqual V (CADDR Parts)))))))
        NIL)))

(QUERY
  (LAMBDA (Goal HowMany RuleClass)
    (* ; "KEE's backward-chaining query.  HowMany is 1 (first rule that succeeds) or ALL (every rule; used with :UPDATE certainty factors).  -> list of the names of the rules that fired.")
    (LET ((KEE.CurrentRuleClass (if (LISTP RuleClass) then (CAR RuleClass) else RuleClass))
          (Goal (KEE.Canon Goal))
          (Fired NIL))
         (DECLARE (SPECVARS KEE.CurrentRuleClass))
         (if KEE.Trace
             then (printout KEE.TraceStream "QUERY " KEE.CurrentRuleClass " " HowMany T))
         (if (AND (NEQ HowMany (QUOTE ALL)) (KEE.Known? Goal))
             then NIL
           else (for R in (KEE.RulesOf KEE.CurrentRuleClass)
                   do (if (KEE.FireRule R Goal)
                          then (push Fired (CAR R))
                               (if (NEQ HowMany (QUOTE ALL)) then (RETURN NIL))))
                (REVERSE Fired)))))

(KEE.ClearState
  (LAMBDA NIL
    (SETQ KEE.Facts NIL)
    (SETQ KEE.RuleErrors NIL)
    (SETQ KEE.Fired NIL)))
)

STOP
