(* "TRIAL: a Medley that serves the stock EVAL Courier program (COURIEREVALSERVE) and one of our own.")
(FILESLOAD COURIEREVALSERVE)
(LOAD "{DSK}/hearts/tests/courier/program.lisp")
(DEFINEQ
(Greet
  (LAMBDA (Who)
    (CONCAT "Hello " Who ", this is the server")))
)
(COURIER.START.SERVER)
(HT.LOG (LIST (QUOTE SERVER-ADDRESS) \MY.NSADDRESS))
(DISMISS 75000)
