;; -*- Mode: Lisp; Package: Interlisp -*-
;; ACTIVEREGIONS — a small reimplementation of the 1986 INTERMEZZO LispUsers library
;; of the same name, written for the HEARTS revival (github.com/athena-ceo/hearts)
;; because the original library is not shipped with modern Medley Interlisp.
;;
;; It gives a window a set of clickable / highlightable rectangular regions, driven by
;; the window's BUTTONEVENTFN — the same job the classic ACTIVEREGIONS did, and the
;; mechanism HEARTS's human player uses to click cards. Modeled on Medley's FREEMENU.
;;
;; Public interface (matches the calls the 1986 HEARTS code makes):
;;   (create ACTIVEREGION REGION _ r DATA _ d UPFN _ fn HELPSTRING _ s)
;;                                     — one region: a screen REGION, arbitrary DATA,
;;                                       and UPFN called (Win region data) when clicked.
;;   (SETACTIVEREGIONS win arlist)     — install the regions + the click handler on win.
;;   (GETPICKREGION win)               — the ACTIVEREGION last clicked (or NIL).
;;   (ACTIVEREGIONS/DEFAULTHIGHLIGHTFN win ar)  — invert-video highlight ar's region.
;;   (ACTIVEREGIONS/DOLOWLIGHT win ar)          — undo the highlight (invert again).
;;
;; Coordinates are window-relative (LASTMOUSEX/Y and the card REGIONs both are).

(RECORD ACTIVEREGION (REGION DATA HELPSTRING UPFN DOWNFN HIGHLIGHTFN))

(DEFINEQ

(ACTIVEREGIONS/DEFAULTHIGHLIGHTFN
  (LAMBDA (Win AR)
    (COND (AR (INVERTREGION (fetch (ACTIVEREGION REGION) of AR)
                            (WINDOWPROP Win (QUOTE DSP)))))))

(ACTIVEREGIONS/DOLOWLIGHT
  (LAMBDA (Win AR)
    (COND (AR (INVERTREGION (fetch (ACTIVEREGION REGION) of AR)
                            (WINDOWPROP Win (QUOTE DSP)))))))

(GETPICKREGION
  (LAMBDA (Win)
    (WINDOWPROP Win (QUOTE PickRegion))))

(SETACTIVEREGIONS
  (LAMBDA (Win ARList)
    (WINDOWPROP Win (QUOTE ActiveRegions) ARList)
    (WINDOWPROP Win (QUOTE BUTTONEVENTFN) (FUNCTION \AR.BUTTONEVENTFN))
    ARList))

(\AR.REGIONUNDER
  (LAMBDA (Win X Y)
    (for AR in (WINDOWPROP Win (QUOTE ActiveRegions))
       thereis (AND (INSIDEP (fetch (ACTIVEREGION REGION) of AR) X Y) AR))))

(\AR.BUTTONEVENTFN
  (LAMBDA (Win)
    (TOTOPW Win)
    (PROG ((AR (\AR.REGIONUNDER Win (LASTMOUSEX Win) (LASTMOUSEY Win))))
      (COND (AR
             (WINDOWPROP Win (QUOTE PickRegion) AR)
             (ACTIVEREGIONS/DEFAULTHIGHLIGHTFN Win AR)
             [while (NOT (MOUSESTATE UP)) do (BLOCK]
             (ACTIVEREGIONS/DOLOWLIGHT Win AR)
             (COND ((fetch (ACTIVEREGION UPFN) of AR)
                    (APPLY* (fetch (ACTIVEREGION UPFN) of AR)
                           Win
                           (fetch (ACTIVEREGION REGION) of AR)
                           (fetch (ACTIVEREGION DATA) of AR)))))))))

)
