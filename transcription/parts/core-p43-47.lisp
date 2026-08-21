;; ==== page 43 ====
;; (continuation of Trick.PlayerByCard's LAMBDA, begun on page 42)
  [LAMBDA (Card Trick)                                     (* hed " 2-May-86 16:18")
    (for i from (Trick.Leader Trick) as c in (Trick.Cards Trick)
        do (SETQ i (ADD1 i))
           (if (GREATERP i 4)
               then (SETQ i (DIFFERENCE i 4)))
        until (Card.Equal? c Card) finally (RETURN i])
(Trick.CardByPlayer
  [LAMBDA (Trick PlayerNum)                                (* hed " 1-May-86 04:07")
    (Trick.PlayOf PlayerNum Trick])
(Trick.Winner
  [LAMBDA (Trick)                                          (* rao "29-Apr-86 05:07")
    (fetch Winner of Trick])
(Trick.WinnerSoFar
  [LAMBDA (Trick)                                          (* hed " 2-May-86 16:14")
    (Trick.WhoPlayed (Card.MaxCard (fetch Cards of Trick)
                            (Trick.LeadSuit Trick))
                    Trick])
)

;; ==== page 44 ====
(* * Random Cruff)

(DEFINEQ

(Not.Null
  [LAMBDA (Thing)                                          (* rao "22-Apr-86 22:01")
    (NOT (NULL Thing])
)

#| BITMAP transcription note ----------------------------------------------------
   READBITMAP packing: each char is a 4-bit nibble (@=0 .. O=15, letters only),
   MSB-first, each scanline padded to a 16-bit word (so W=11 -> 4 chars/row,
   W=30 -> 8). The five CARD bitmaps below — CardOutline and the four suit pips —
   have been VERIFIED by decoding and rendering (tools/readbitmap-decode.py): a
   hollow rounded card border, a solid ♣ and ♠ (black suits), and a dithered ♦
   and ♥ (the 1986 monochrome-display convention for red suits). Corrected two OCR
   slips found this way: ClubsBits row 0 @DO@->@D@@, and CardOutline's hollow sides
   L@@@@@@L (not the solid LOOOOOOL first transcribed).
   The two 50x50 icons (HIconBM, HShadowBM) remain BEST-EFFORT and are still stubbed
   by build-loadfile.py; they are only the desktop app icon, not card-critical. |#

(RPAQ CardOutline (READBITMAP))
(30 45
"GOOOOOOH"
"OOOOOOOL"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"L@@@@@@L"
"OOOOOOOL"
"GOOOOOOH")

(RPAQ ClubsBits (READBITMAP))
(11 11
"@D@@"
"@N@@"
"AO@@"
"@N@@"
"BDH@"
"GEL@"
"OON@"
"GEL@"
"BDH@"
"@N@@"
"COH@")

(RPAQ DiamondsBits (READBITMAP))
(11 11
"JDJ@"
;; ==== page 45 ====
"DND@"
"IKB@"
"CEH@"
"FJL@"
"MEF@"
"FJL@"
"CEH@"
"IKB@"
"DND@"
"JDJ@")

(RPAQ HeartsBits (READBITMAP))
(11 11
"HDB@"
"CAH@"
"GKL@"
"FNL@"
"EED@"
"FJL@"
"CEH@"
"IKB@"
"DND@"
"JDJ@"
"EAD@")

(RPAQ SpadesBits (READBITMAP))
(11 11
"@D@@"
"@N@@"
"AO@@"
"COH@"
"GOL@"
"GOL@"
"GOL@"
"COH@"
"@D@@"
"AO@@"
"COH@")

(RPAQ HIconBM (READBITMAP))
(50 50
"@@AO@@@@CN@@@@@@"
"@@OOL@@@OOL@@@@@"
"@ANJO@@CMEN@@@@@"
"@CEEGL@OJJK@@@@@"
"@FJJJOCMEEEH@@@@"
"@MEEEGOJJJL@@@@@"
"AJJJJJMEEEEF@@@@"
"COOOOOOOOOO@@@@@"
"COOOOOOOOOO@@@@@"
"F@@@@@@@@@AH@@@@"
"GOOOOOOOOOOH@@@@"
"F@@@@@@@@@AH@@@@"
"L@IKNGCLOIL@L@@@"
"L@IJFIJFBBF@L@@@"
"L@IJ@IJFCB@@L@@@"
"L@OKHOKLCAL@L@@@"
"L@IJ@IJLC@F@L@@@"
"L@IJFIJFCBF@L@@@"
"L@IKNIJFCAL@L@@@"
"L@@@@@@@@@@L@@@@"
"OOOOOOOOOOOL@@@"
"F@@@@@@@@@AH@@@"
"GOOOOOOOOOOH@@@"
"GOOOOOOOOOOH@@@"
"CEEEEEEEEEE@@@@"
"CJJJJJJJJJK@@@@"
"AMEEEEEEEEF@@@@"
"AJJJJJJJJJN@@@@"
"@MEEEEEEEED@@@@"
"@FJJJJJJJJL@@@@"
"@CEEEEEEEEH@@@@"
"@AJJJJJJJK@@@@@"
"@@MEEEEEEEF@@@@"
;; ==== page 46 ====
"@@FJJJJJJL@@@@@"
"@@CEEEEEEH@@@@@"
"@@AJJJJJK@@@@@@"
"@@@MEEEEF@@@@@@"
"@@@FJJJJL@@@@@@"
"@@@CEEEEH@@@@@@"
"@@@AJJJK@@@@@@@"
"@@@@MEEEF@@@@@@"
"@@@@FJJJL@@@@@@"
"@@@@CEEEH@@@@@@"
"@@@@AJJK@@@@@@@"
"@@@@@MEF@@@@@@@"
"@@@@@FJL@@@@@@@"
"@@@@@CEH@@@@@@@"
"@@@@@AK@@@@@@@@"
"@@@@@N@@@@@@@@@"
"@@@@@D@@@@@@@@@")

(RPAQ HShadowBM (READBITMAP))
(50 50
"@@AO@@@@CN@@@@@@"
"@@OOL@@@OOL@@@@@"
"@AOOO@@COON@@@@@"
"@CQOOL@OOOO@@@@@"   #| ?? '@CQOOL...' — Q uncertain |#
"@GOOOOCOOOH@@@@"
"@OOOOOOOOOL@@@@"
"AOOOOOOOOON@@@@"
"COOOOOOOOOO@@@@@"
"COOOOOOOOOO@@@@@"
"GOOOOOOOOOOH@@@"
"GOOOOOOOOOOH@@@"
"GOOOOOOOOOOH@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"OOOOOOOOOOOL@@@"
"GOOOOOOOOOOH@@@"
"GOOOOOOOOOOH@@@"
"GOOOOOOOOOOH@@@"
"COOOOOOOOOO@@@@@"
"COOOOOOOOOO@@@@@"
"COOOOOOOOOON@@@@"
"AOOOOOOOOON@@@@"
"@OOOOOOOOOL@@@@"
"@GOOOOOOOOH@@@@"
"@COOOOOOOH@@@@"
"@AOOOOOOO@@@@@"
"@@OOOOOON@@@@@"
"@@GOOOOOL@@@@@"
"@@COOOOOH@@@@@"
"@@AOOOOO@@@@@@"
"@@@OOOON@@@@@@"
"@@@GOOOL@@@@@@"
"@@@COOOH@@@@@@"
"@@@AOOO@@@@@@@"
"@@@@OON@@@@@@@"
"@@@@GOL@@@@@@@"
"@@@@COH@@@@@@@"
"@@@@AO@@@@@@@@"
"@@@@@ON@@@@@@@"
"@@@@@GOL@@@@@@"
"@@@@@COH@@@@@@"
"@@@@@AO@@@@@@@"
"@@@@@N@@@@@@@@"
"@@@@@D@@@@@@@@")
#| ?? END best-effort bitmap transcription ------------------------------------- |#

(FILESLOAD {LISP:}<LispLibrary>INTERMEZZO>EVALSERVER.DCOM
           {LISP:}<LispUsers>INTERMEZZO>ACTIVEREGIONS.DCOM)
(DECLARE: DONTEVAL@LOAD DOEVAL@COMPILE DONTCOPY COMPILERVARS

;; ==== page 47 ====
(ADDTOVAR NLAMA )

(ADDTOVAR NLAML )

(ADDTOVAR LAMA CP.Think H.Apply)
)
(H.MakeIcon)
(PUTPROPS HEARTS COPYRIGHT ("Harley Davis and Ramana Rao" 1986))
STOP
