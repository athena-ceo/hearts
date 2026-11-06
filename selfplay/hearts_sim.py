"""The HEARTS game outside Medley, with the exact rules of the 1986 code (H.GetLegals, H.Deal,
Deal.SetScore), for training.  tests in selfplay/test_sim.py replay real Medley games through it.

A player sees the same request the LLM player's helper gets from Medley, so anything trained here
can play there unchanged.  Cards are strings such as "S10"; seats are 1-4.
"""
SUITS = "CDHS"
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
DECK = [s + r for s in SUITS for r in RANKS]
INDEX = {card: i for i, card in enumerate(DECK)}
RANK_ORDER = {r: i for i, r in enumerate(RANKS)}
RANK_OF = {card: RANK_ORDER[card[1:]] for card in DECK}
PASS_OFFSET = {"Left": 1, "Across": 2, "Right": 3}
DIRECTIONS = ["Left", "Across", "Right", None]


def points(card):
    return 13 if card == "SQ" else 1 if card[0] == "H" else 0


def legal_cards(hand, trick_cards, hearts_broken, first_trick):
    """H.GetLegals."""
    if trick_cards:
        suit = trick_cards[0][0]
        follow = [c for c in hand if c[0] == suit]
        if follow:
            return follow
        if first_trick:
            return [c for c in hand if c[0] != "H" and c != "SQ"] or list(hand)
        return list(hand)
    if first_trick:
        return ["C2"]
    if hearts_broken:
        return list(hand)
    return [c for c in hand if c[0] != "H"] or list(hand)


def trick_winner(leader, cards):
    """The seat that played the highest card of the led suit."""
    suit = cards[0][0]
    best = max((i for i, c in enumerate(cards) if c[0] == suit), key=lambda i: RANK_OF[cards[i]])
    return (leader - 1 + best) % 4 + 1


def deal_scores(taken):
    """Deal.SetScore: 26 points become -26 for the shooter, and the others keep what they took."""
    return [-26 if t == 26 else t for t in taken]


def pass_target(seat, direction):
    return (seat - 1 + PASS_OFFSET[direction]) % 4 + 1


def play_deal(players, deck, direction, on_trick=None):
    """Play one deal.  players[i].choose_pass(request) -> 3 cards, .choose_play(request) -> card.
    deck is 52 cards: seat 1 gets the first 13, as in H.Deal.  Returns (scores, taken)."""
    hands = [list(deck[i * 13:(i + 1) * 13]) for i in range(4)]
    passed = [[], [], [], []]
    received = [[], [], [], []]
    if direction:
        for i, player in enumerate(players):
            passed[i] = player.choose_pass({"decision": "pass", "seat": i + 1, "deal": 1, "direction": direction,
                                            "hand": list(hands[i]), "scores": [0, 0, 0, 0]})
        for i in range(4):
            target = pass_target(i + 1, direction) - 1
            received[target] = passed[i]
        for i in range(4):
            hands[i] = [c for c in hands[i] if c not in passed[i]] + list(received[i])
    leader = next(i + 1 for i in range(4) if "C2" in hands[i])
    history = []
    hearts_broken = False
    taken = [0, 0, 0, 0]
    for number in range(13):
        cards = []
        first = number == 0
        for offset in range(4):
            seat = (leader - 1 + offset) % 4 + 1
            hand = hands[seat - 1]
            legal = legal_cards(hand, cards, hearts_broken, first)
            if len(legal) == 1:
                card = legal[0]
                players[seat - 1].forced()
            else:
                card = players[seat - 1].choose_play({
                    "decision": "play", "seat": seat, "deal": 1, "direction": direction, "hand": hand,
                    "legal": legal, "trick": {"leader": leader, "cards": cards},
                    "hearts_broken": hearts_broken, "first_trick": first,
                    "passed": passed[seat - 1], "received": received[seat - 1],
                    "history": history, "scores": [0, 0, 0, 0]})
            hand.remove(card)
            cards.append(card)
            if card[0] == "H":
                hearts_broken = True
        winner = trick_winner(leader, cards)
        taken[winner - 1] += sum(points(c) for c in cards)
        history.append({"leader": leader, "cards": cards, "winner": winner})
        if on_trick:
            on_trick(taken)
        leader = winner
    return deal_scores(taken), taken
