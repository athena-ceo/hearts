;; ==== page 31 ====
                                                  (if (EQ thing T)
                                                      then thing
                                                    else (KWOTE thing]
                  (EVAL (APPEND (QUOTE (printout))
                                (LIST (if (fetch CP.OpenHand? of self)
                                          then (GETPROMPTWINDOW (fetch CP.HandWindow of self))
                                        else (fetch ThoughtWindow of self)))
                                PrintItems])

(CP.Trick
  [LAMBDA (self Trick)                                     (* rao "22-Apr-86 21:36")
    (LET ((TrickCards (Trick.Cards Trick)))
      (if (CardList.Member (CP.Maggie)
                           (Trick.Cards Trick))
          then (replace MaggiePlayed? of self with T])

(CPTest
  [LAMBDA NIL                                              (* rao "22-Apr-86 21:37")
    (CP.GiveHand (CP.Create T)
                 (Hand.Create (HP.ChooseSomeCards 13 (HP.MakeDeck])

(CP.Results
  [LAMBDA NIL                                              (* rao "17-Apr-86 11:25")

          (* * (Presently no storing of results))


    NIL])
)

;; ==== page 32 ====
(* * House Clown)

[DECLARE: EVAL@COMPILE

(DATATYPE Clown (Clown.Hand))
]
(/DECLAREDATATYPE (QUOTE Clown)
                  (QUOTE (POINTER))
                  (QUOTE ((Clown 0 POINTER)))
                  (QUOTE 2))
(DEFINEQ

(CLOWN.Create
  [LAMBDA (PlayerNumber)                                   (* hed " 5-May-86 01:14")
    (create Player
            Name ←[GENSYM (CAR (FNTH ClownNames (RAND 1 (FLENGTH ClownNames]
            Type ←(QUOTE Lisp)
            Object ←(create Clown)
            Mapping ←(QUOTE ((GiveHand . CLOWN.GiveHand)
                             (PassOut . CLOWN.PassOut)
                             (PassIn . CLOWN.PassIn)
                             (Play . CLOWN.Play])

(CLOWN.GiveHand
  [LAMBDA (Clown Hand PlayerNum)                           (* hed " 5-May-86 01:15")
    (replace Clown.Hand of Clown with Hand])

(CLOWN.PassOut
  [LAMBDA (Clown Pass)                                     (* rao "17-Apr-86 12:07")
    (if Pass
        then (bind (Hand ←(fetch Clown.Hand of Clown))
                   Card for i from 1 to 3
              collect [SETQ Card (CAR (NTH (Hand.Cards Hand)
                                           (RAND 1 (DIFFERENCE 14 i]
                       (Hand.RemoveCard Hand Card)
                       Card])

(CLOWN.PassIn
  [LAMBDA (Clown PassIn)                                   (* rao "17-Apr-86 12:07")
    (bind (Hand ←(fetch Clown.Hand of Clown)) for Card in PassIn do (Hand.AddCard Hand Card])

(CLOWN.Play
  [LAMBDA (Clown Trick HeartsBroken?)                      (* rao "17-Apr-86 12:07")

          (* * Picks Random Card from all Legal Plays)


    (LET* [(Possibles (H.GetLegals (fetch Clown.Hand of Clown)
                                   Trick HeartsBroken?))
           (Card (CAR (NTH Possibles (RAND 1 (LENGTH Possibles]
      (Hand.RemoveCard (fetch Clown.Hand of Clown)
                       Card)
      Card])
)

;; ==== page 33 ====
(* * DATA Structures)

[DECLARE: EVAL@COMPILE

(RECORD Game (Players Deals Score Winners))

(RECORD Player (Name Number Type Object Mapping))

(RECORD Deal (Hands Tricks D.Score D.CumScore PassDir PassOut PassIn D.RealHands))

(RECORD Card (Suit . Value))

(RECORD Hand (C D H S Owner))

(RECORD Trick (LeadPlayerNum Cards Winner))
]

(RPAQQ CardValues (2 3 4 5 6 7 8 9 10 J Q K A))

(RPAQQ SuitValues (C D H S))

(RPAQQ Game.OverScore 100)

(RPAQ Player.Array (ARRAY 4))
(DEFINEQ

(Game.Update
  [LAMBDA (Game Deal)                                      (* rao "23-Apr-86 16:39")
    (replace Deals of Game with (NCONC1 (fetch Deals of Game)
                                        Deal))
    (replace D.CumScore of Deal with (replace Score of Game with (for col
                                                                    in (fetch Score of Game)
                                                                    as dcol
                                                                    in (fetch D.Score of Deal)
                                                                    collect (IPLUS col dcol])

(Game.Winner
  [LAMBDA (Game)                                           (* rao "15-Apr-86 14:49")
    (if (for col in (fetch Score of Game) thereis (IGREATERP col Game.OverScore))
        then (bind (best ←(PLUS Game.OverScore 26))
                   Winners for i from 1 to 4 as col in (fetch Score of Game)
              do (if (NOT (IGREATERP col best))
                     then (SETQ best col)
                          (SETQ Winners (NCONC1 Winners i)))
              finally (replace Winners of Game with Winners)
                      (RETURN Winners])

(Game.PrintOut
  [LAMBDA (Game File)                                      (* hed " 5-May-86 02:05")

          (* * comment)


    (LET [(File (if (STREAMP File)
                    then File
                  else (OPENSTREAM File (QUOTE OUTPUT]
      (for i from 1 to 4 as p in (fetch Players of Game) do (printout File i -1
                                                                      (fetch Name of p)
                                                                      T))
      (bind H1 H2 H3 H4 for Deal in (fetch Deals of Game)
         do                                                (* Print Hands)
            (for HN in (QUOTE (H1 H2 H3 H4)) as H in (fetch Hands of Deal) do (SET HN H))
                                                           (* Hand 1)
            (printout File 30 "C" -2 (for c in (fetch C of H1) collect (fetch Value of c))
                      T)
            (printout File 30 "D" -2 (for c in (fetch D of H1) collect (fetch Value of c))
                      T)
            (printout File 30 "H" -2 (for c in (fetch H of H1) collect (fetch Value of c))
                      T)
            (printout File 30 "S" -2 (for c in (fetch S of H1) collect (fetch Value of c))
                      T T)                                 (* Hand 2 and 3)
            (printout File "C" -2 (for c in (fetch C of H2) collect (fetch Value of c))
                      40 "C" -2 (for c in (fetch C of H3) collect (fetch Value of c))
                      T)

;; ==== page 34 ====
            (printout File "D" -2 (for c in (fetch D of H2) collect (fetch Value of c))
                      40 "D" -2 (for c in (fetch D of H3) collect (fetch Value of c))
                      T)
            (printout File "H" -2 (for c in (fetch H of H2) collect (fetch Value of c))
                      40 "H" -2 (for c in (fetch H of H3) collect (fetch Value of c))
                      T)
            (printout File "S" -2 (for c in (fetch C of H2) collect (fetch Value of c))
                      40 "S" -2 (for c in (fetch C of H3) collect (fetch Value of c))
                      T T)                                 (* Hand 4)
            (printout File 30 "C" -2 (for c in (fetch C of H4) collect (fetch Value of c))
                      T)
            (printout File 30 "D" -2 (for c in (fetch D of H4) collect (fetch Value of c))
                      T)
            (printout File 30 "H" -2 (for c in (fetch H of H4) collect (fetch Value of c))
                      T)
            (printout File 30 "S" -2 (for c in (fetch S of H4) collect (fetch Value of c))
                      T T)
            (printout File (fetch PassDir of Deal)
                      T)
            (for PassOut in (fetch PassOut of Deal) do (printout File (for c in PassOut
                                                                         collect (Card.Print c))
                                                                 T))
            (printout File T)                              (* Passes)
            (for Trick in (fetch Tricks of Deal) do (for Card in (Trick.OrderCards Trick)
                                                       as Pos from 2 by 6 as i from 1
                                                       do (printout File .TAB Pos (Card.Print Card))
                                                          (if (EQP i (fetch LeadPlayerNum
                                                                            of Trick))
                                                              then (printout File "*"))
                                                       finally (printout File T)))
            (printout File T (fetch D.Score of Deal))
            (printout File T (fetch D.CumScore of Deal)
                      T T T))
      (printout File T (fetch Score of Game)
                T T])
)
(DEFINEQ

(PlayerLoc
  [LAMBDA (BaseNum GoalNum)                                (* rao "24-Apr-86 22:06")
    (LET ((Dif (DIFFERENCE BaseNum GoalNum)))
      (if (LESSP Dif 0)
          then (SETQ Dif (PLUS 4 Dif)))
      (SELECTQ Dif
               (1 (QUOTE Right))
               (2 (QUOTE Across))
               (3 (QUOTE Left))
               NIL])

(PlayerNum
  [LAMBDA (BaseNum Location)                               (* rao "24-Apr-86 22:00")
    (LET [(Num (PLUS BaseNum (SELECTQ Location
                                      ((QUOTE Left)
                                       1)
                                      ((QUOTE Across)
                                       2)
                                      ((QUOTE Right)
                                       3)
                                      0]
      (if (GREATERP Num 4)
          then (DIFFERENCE Num 4)
        else Num])

(Player?.Record
  [LAMBDA (Player)                                         (* rao "15-Apr-86 17:55")
    (if (NUMBERP Player)
        then (ELT Player.Array Player)
      else Player])

(Player?.Number
  [LAMBDA (Player)                                         (* rao "15-Apr-86 17:40")
    (if (NUMBERP Player)
        then Player
      else (fetch Number of Player])

;; ==== page 35 ====
(PlayerNum.Increment
  [LAMBDA (Num)                                            (* rao "15-Apr-86 13:53")
    (IPLUS (IREMAINDER Num 4)
           1])

(PlayerNum.Plus
  [LAMBDA (X Y)                                            (* rao "15-Apr-86 16:19")
    (LET ((Z (IPLUS X Y)))
      (if (IGREATERP Z 4)
          then (IDIFFERENCE Z 4)
        else Z])

(PlayerNum.Difference
  [LAMBDA (X Y)                                            (* rao "15-Apr-86 13:50")
    (LET ((Z (IDIFFERENCE X Y)))
      (if (LESSP Z 0)
          then (IPLUS Z 4)
        else Z])
)
(DEFINEQ

(Deal.SetScore
  [LAMBDA (Deal)                                           (* rao "29-Apr-86 00:49")
    (bind (Scores ←(ARRAY 4 (QUOTE FIXP))) for Trick in (fetch Tricks of Deal)
       do (add (ELT Scores (fetch Winner of Trick))
               (Trick.Points Trick))
       finally (replace D.Score of Deal with (for i from 1 to 4
                                                collect (LET ((Score (ELT Scores i)))
                                                          (if (EQP Score 26)
                                                              then -26
                                                            else Score])
)

;; ==== page 36 ====
(* * Card Functions)

(DEFINEQ

(Card.Better?
  [LAMBDA (Best Card)                                      (* rao " 8-Apr-86 18:55")
    (AND (EQUAL (fetch Suit of Best)
                (fetch Suit of Card))
         (Card.Higher? Card Best])

(Card.Create
  [LAMBDA (Value Suit)                                     (* rao "10-Apr-86 12:12")
    (if (AND (FMEMB Suit SuitValues)
             (FMEMB Value CardValues))
        then (create Card
                     Suit ← Suit
                     Value ← Value)
      else (ERROR (CONCAT "Illegal card suit: " Suit " or value: " Value "!")
                  NIL T])

(Card.CreateBM
  [LAMBDA (Card)                                           (* rao "11-Apr-86 00:45")
    (OR (ELT Card.BMCache (Card.Number Card))
        (LET ((Val (fetch Value of Card))
              (Suit (fetch Suit of Card))
              (Result (BITMAPCOPY CardOutline))
              ResDS SuitBits)
          (SETQ ResDS (DSPCREATE Result))
          (SETQ SuitBits (SELECTQ Suit
                                  ((QUOTE C)
                                   ClubsBits)
                                  ((QUOTE D)
                                   DiamondsBits)
                                  ((QUOTE H)
                                   HeartsBits)
                                  ((QUOTE S)
                                   SpadesBits)
                                  NIL))
          (DSPFONT (QUOTE (HELVETICA 12 BOLD))
                   ResDS)
          (BITBLT SuitBits 0 0 Result 3 (DIFFERENCE CardHeight 14)
                  11 11 (QUOTE INPUT)
                  (QUOTE REPLACE))
          (BITBLT SuitBits 0 0 Result (DIFFERENCE CardWidth 14)
                  3 11 11 (QUOTE INPUT)
                  (QUOTE REPLACE))
          (CENTERPRINTINREGION Val (CREATEREGION 0 16 CardWidth 13)
                               ResDS)
          (SETA Card.BMCache (Card.Number Card)
                Result)
          Result])

(Card.CreateDeck
  [LAMBDA NIL                                              (* rao " 8-Apr-86 15:56")
    (bind (I ← 0)
          (Deck ←(ARRAY 52)) for Suit in SuitValues do (for Card in CardValues
                                                          do (SETA Deck (add I 1)
                                                                   (Card.Create Card Suit)))
       finally (RETURN Deck])

(Card.Equal?
  [LAMBDA (Card1 Card2)                                    (* rao "22-Apr-86 23:00")
    (if (AND (EQUAL (fetch Suit of Card1)
                    (fetch Suit of Card2))
             (EQUAL (fetch Value of Card1)
                    (fetch Value of Card2)))
        then Card1])

(Card.EqualVal?
  [LAMBDA (Card1 Card2)                                    (* rao "12-Apr-86 14:30")
    (EQUAL (fetch Value of Card1)
           (fetch Value of Card2])

(Card.Higher?
