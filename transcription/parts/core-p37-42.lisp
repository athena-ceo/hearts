;; ==== page 37 ====
  [LAMBDA (Card1 Card2)                                    (* rao "22-Apr-86 22:15")
    (LET ((CV1 (fetch Value of Card1))
          (CV2 (fetch Value of Card2)))
      (if CV1
          then (for x in CardValues do (if (EQUAL CV1 x)
                                           then (RETURN NIL)
                                         elseif (EQUAL CV2 x)
                                           then (RETURN Card1])

(Card.Lower?
  [LAMBDA (Card1 Card2)                                    (* rao "12-Apr-86 18:42")
    (AND (NOT (Card.Higher? Card1 Card2))
         (NOT (Card.Equal? Card1 Card2])

(Card.MaxCard
  [LAMBDA (CardList InSuit)                                (* rao "15-Apr-86 16:08")
    (LET ((highest (CAR CardList)))
      (for c in (CDR CardList) do (if (AND (OR (NOT InSuit)
                                               (EQUAL (fetch Suit of c)
                                                      InSuit))
                                           (Card.Higher? c highest))
                                      then (SETQ highest c)))
      highest])

(Card.MinCard
  [LAMBDA (CardList InSuit)                                (* rao "14-Apr-86 16:16")
    (LET ((lowest))
      (for c in CardList do (if (AND (OR (NOT InSuit)
                                         (EQUAL (Card.Suit c)
                                                InSuit))
                                     (OR (NOT lowest)
                                         (Card.Lower? c lowest)))
                                then (SETQ lowest c)))
      lowest])

(Card.Number
  [LAMBDA (Card)                                           (* rao "11-Apr-86 00:29")
    (PLUS (TIMES (SELECTQ (fetch Suit of Card)
                          ((QUOTE C)
                            0)
                          ((QUOTE D)
                            1)
                          ((QUOTE H)
                            2)
                          ((QUOTE S)
                            3)
                          NIL)
                 13)
          (bind (Val ←(fetch Value of Card)) for i from 1 as cv in CardValues
             thereis (EQUAL cv Val) finally (RETURN i])

(Card.Print
  [LAMBDA (Card)                                           (* rao "23-Apr-86 16:09")
    (PACK (LIST (fetch Value of Card)
                (fetch Suit of Card])

(Card.Value
  [LAMBDA (C)                                              (* rao "21-Apr-86 18:26")
    (fetch Value of C])

(Card.ValueSublist
  [LAMBDA (val1 val2)                                      (* rao "24-Apr-86 20:26")
    (INTERSECTION (MEMBER val1 CardValues)
                  (MEMBER val2 (REVERSE CardValues])

(Card.Suit
  [LAMBDA (C)                                              (* rao "21-Apr-86 18:26")
    (fetch Suit of C])

(CardList.HigherCards
  [LAMBDA (CardList Card InSuit)                           (* rao "29-Apr-86 03:48")
    (for C in (CardList.CardsOfSuit CardList InSuit) collect C when (Card.Higher? C Card])

(CardList.LowerCards

;; ==== page 38 ====
  [LAMBDA (CardList Card InSuit)                           (* rao "21-Apr-86 18:26")
    (for C in (CardList.CardsOfSuit CardList InSuit) collect C when (Card.Lower? C Card])

(CardList.SecondHighest
  [LAMBDA (CardList)                                       (* rao "21-Apr-86 18:26")
    (LET ((highest (Card.MaxCard CardList)))
      (Card.MaxCard (for C in CardList collect C unless (Card.Equal? C highest])

(CardList.HighSpades?
  [LAMBDA (CardList)                                       (* rao "22-Apr-86 22:16")
    (Card.Higher? (Card.MaxCard CardList (QUOTE S))
                  (Card.Create (QUOTE J)
                               (QUOTE S])

(CardList.CardsOfSuit
  [LAMBDA (CardList Suit)                                  (* rao "10-Apr-86 17:31")
    (for c in CardList collect c when (EQUAL (fetch Suit of c)
                                             Suit])

(CardList.Member
  [LAMBDA (Card CardList)                                  (* rao "22-Apr-86 23:05")
    (for C in CardList thereis (Card.Equal? Card C])

(CardList.Sort
  [LAMBDA (CardList)                                       (* rao "10-Apr-86 12:50")
    (SORT CardList (FUNCTION Card.Lower?])

(CardList.EliminateSuit
  [LAMBDA (CardList Suit)                                  (* rao "23-Apr-86 00:38")
    (for Card in CardList collect Card unless (EQUAL (Card.Suit Card)
                                                     Suit])

(CardList.CardsOfSuits
  [LAMBDA (CardList Suits)                                 (* hed " 1-May-86 04:12")
    (for card in CardList collect card when (FMEMB (Card.Suit card)
                                                   Suits])

(CardList.PointCards
  [LAMBDA (CardList)                                       (* hed " 1-May-86 04:02")
    (for card in CardList collect card when (OR (EQUAL (Card.Suit card)
                                                       (QUOTE H))
                                                (Card.Equal? card (Card.Create (QUOTE Q)
                                                                               (QUOTE S])

(CardList.RemoveCard
  [LAMBDA (CL Card)                                        (* hed " 3-May-86 15:37")
    (REMOVE Card CL])

(CardList.ShortestSuit
  [LAMBDA (CardList)                                       (* hed " 1-May-86 04:14")
    (for suit in SuitValues smallest (FLENGTH (CardList.CardsOfSuit CardList suit))
       unless (NULL (CardList.CardsOfSuit CardList suit])

(Card.NotEqual?
  [LAMBDA (Card1 Card2)                                    (* hed "30-Apr-86 05:10")
    (NOT (Card.Equal? Card1 Card2])

(CardList.BridgePoints
  [LAMBDA (CardList)                                       (* hed "30-Apr-86 03:40")
    (for c in CardList sum (SELECTQ (Card.Value c)
                                    ((QUOTE J)
                                      1)
                                    ((QUOTE Q)
                                      2)
                                    ((QUOTE K)
                                      3)
                                    ((QUOTE A)
                                      4)
                                    0])
)

(RPAQQ CardGap 5)

(RPAQQ CardHeight 45)

;; ==== page 39 ====
(RPAQQ CardWidth 30)

(RPAQ? Card.BMCache (ARRAY 52))

;; ==== page 40 ====
(* * Hand Functions)

(DEFINEQ

(Hand.AddCard
  [LAMBDA (Hand Card)                                      (* rao "10-Apr-86 23:41")
    (LET* [(Suit (fetch Suit of Card))
           (NewCards (APPEND (Hand.CardsInSuit Hand Suit)
                             (LIST Card]
      (Hand.SetSuit Hand Suit NewCards])

(Hand.Cards
  [LAMBDA (Hand)                                           (* rao "10-Apr-86 13:15")
    (for s in SuitValues join (COPY (Hand.CardsInSuit Hand s])

(Hand.CardsInSuit
  [LAMBDA (Hand Suit)                                      (* rao "10-Apr-86 23:11")
    (SELECTQ Suit
             ((QUOTE C)
               (fetch C of Hand))
             ((QUOTE D)
               (fetch D of Hand))
             ((QUOTE H)
               (fetch H of Hand))
             ((QUOTE S)
               (fetch S of Hand))
             (SHOULDNT])

(Hand.Create
  [LAMBDA (CardList Player)                                (* rao "15-Apr-86 15:03")
    (create Hand
            C ←(CardList.CardsOfSuit CardList (QUOTE C))
            D ←(CardList.CardsOfSuit CardList (QUOTE D))
            H ←(CardList.CardsOfSuit CardList (QUOTE H))
            S ←(CardList.CardsOfSuit CardList (QUOTE S))
            Owner ←(fetch Number of Player])

(Hand.Doubleton?
  [LAMBDA (Hand Suit)                                      (* rao "12-Apr-86 15:47")
    (EQP (Hand.NumberInSuit Hand Suit)
         2])

(Hand.FaceCards
  [LAMBDA (Hand MinVal)                                    (* rao "28-Apr-86 16:27")
    (for C in (Hand.Cards Hand) collect C when (Card.Higher? C (Card.Create (OR 10 MinVal)
                                                                            (Card.Suit C])

(Hand.MaxCard
  [LAMBDA (Hand Suit)                                      (* rao "21-Apr-86 00:06")
    (Card.MaxCard (Hand.CardsInSuit Hand Suit)
                  Suit])

(Hand.Member?
  [LAMBDA (Card Hand)                                      (* rao "20-Apr-86 22:25")
    (MEMBER Card (Hand.Cards Hand])

(Hand.MinCard
  [LAMBDA (Hand Suit)                                      (* hed " 1-May-86 06:03")
    (Card.MinCard (if Suit
                      then (Hand.CardsInSuit Hand Suit)
                    else (Hand.Cards Hand))
                  Suit])

(Hand.FaceCards
  [LAMBDA (Hand MinVal)                                    (* rao "28-Apr-86 16:27")
    (for C in (Hand.Cards Hand) collect C when (Card.Higher? C (Card.Create (OR 10 MinVal)
                                                                            (Card.Suit C])

(Hand.NumberInSuit
  [LAMBDA (Hand Suit)                                      (* KY " 8-Apr-86 14:00")
    (FLENGTH (Hand.CardsInSuit Hand Suit])

(Hand.RemoveCard
  [LAMBDA (Hand Card)                                      (* rao "21-Apr-86 01:57")

;; ==== page 41 ====
    (LET* [(Suit (fetch Suit of Card))
           (NewCards (for c in (Hand.CardsInSuit Hand Suit) collect c unless (EQUAL c Card]
      (Hand.SetSuit Hand Suit NewCards)
      Card])

(Hand.RemoveCards
  [LAMBDA (Hand Cards)                                     (* HED "25-Apr-86 11:31")
    (for C in Cards do (Hand.RemoveCard Hand C))
    Cards])

(Hand.SetSuit
  [LAMBDA (Hand Suit Cards)                                (* rao "10-Apr-86 23:13")
    (SELECTQ Suit
             ((QUOTE C)
               (replace C of Hand with Cards))
             ((QUOTE D)
               (replace D of Hand with Cards))
             ((QUOTE H)
               (replace H of Hand with Cards))
             ((QUOTE S)
               (replace S of Hand with Cards))
             (SHOULDNT])

(Hand.Singleton?
  [LAMBDA (Hand Suit)                                      (* rao "12-Apr-86 15:44")
    (EQP (Hand.NumberInSuit Hand Suit)
         1])

(Hand.Sort
  [LAMBDA (Hand)                                           (* rao "10-Apr-86 13:22")
    (CardList.Sort (FETCH C OF Hand))
    (CardList.Sort (FETCH D OF Hand))
    (CardList.Sort (FETCH H OF Hand))
    (CardList.Sort (FETCH S OF Hand])

(Hand.Void?
  [LAMBDA (Hand Suit)                                      (* KY " 8-Apr-86 14:01")
    (EQP (Hand.NumberInSuit Hand Suit)
         0])
)

;; ==== page 42 ====
(* * Trick Functions)

(DEFINEQ

(Trick.Cards
  [LAMBDA (Trick)                                          (* KY " 8-Apr-86 13:16")
    (fetch Cards of Trick])

(Trick.LeadCard
  [LAMBDA (Trick)                                          (* rao "15-Apr-86 14:00")
    (CAR (fetch Cards of Trick])

(Trick.LeadSuit
  [LAMBDA (Trick)                                          (* rao "15-Apr-86 16:04")
    (fetch Suit of (Trick.LeadCard Trick])

(Trick.OrderCards
  [LAMBDA (Trick)                                          (* rao "23-Apr-86 15:43")

        (* * comment)


    (LET [(Order (SELECTC (fetch LeadPlayerNum of Trick)  #| ?? SELECTC — glyph reads C not Q, keys are unquoted numbers |#
                          (1 NIL)
                          (2 (QUOTE (4 1 2 3)))
                          (3 (QUOTE (3 4 1 2)))
                          (4 (QUOTE (2 3 4 1)))
                          (SHOULDNT]
      (if Order
          then (bind (Cards ←(fetch Cards of Trick)) for i in Order collect (CAR (NTH Cards i)))
        else (fetch Cards of Trick])

(Trick.Play
  [LAMBDA (Trick Card)                                     (* rao "15-Apr-86 14:05")
    (replace Cards of Trick with (NCONC1 (Trick.Cards Trick)
                                         Card])

(Trick.PlayerByCard
  [LAMBDA (Trick Card)                                     (* rao "15-Apr-86 16:21")
    (PlayerNum.Plus (fetch LeadPlayerNum of Trick)
                    (IDIFFERENCE 4 (LENGTH (MEMBER Card (fetch Cards of Trick])

(Trick.Points
  [LAMBDA (Trick)                                          (* rao "10-Apr-86 17:39")
    (LET ((Cards (fetch Cards of Trick)))
      (for c in Cards sum (if (EQUAL (fetch Suit of c)
                                     (QUOTE H))
                              then 1
                            elseif (AND (EQUAL (fetch Suit of c)
                                               (QUOTE S))
                                        (EQUAL (fetch Value of c)
                                               (QUOTE Q)))
                              then 13
                            else 0])

(Trick.SetWinner
  [LAMBDA (Trick)                                          (* rao "15-Apr-86 13:59")
    (replace Winner of Trick with (Trick.PlayerByCard Trick (Card.MaxCard (fetch Cards of Trick)
                                                                          (Trick.LeadSuit Trick])

(Trick.Leader
  [LAMBDA (Trick)                                          (* hed "30-Apr-86 02:38")
    (fetch LeadPlayerNum of Trick])

(Trick.PlayOf
  [LAMBDA (PlayerNum Trick)                                (* hed " 3-May-86 15:31")
    (LET ((When (IPLUS (DIFFERENCE PlayerNum (Trick.Leader Trick))
                       1)))
      (CAR (FNTH (Trick.Cards Trick)
                 (if (LEQ When 0)
                     then (PLUS When 4)
                   else When])

(Trick.WhoPlayed
