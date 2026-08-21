# The Hearts Expert System

*Original 1986 write-up by Harley Davis and Ramana Rao (MIT 6.871). Transcribed from `original/hearts-overview.pdf` by Claude Code (Anthropic coding agent). Wording is verbatim; only the layout is reformatted as Markdown.*

## 1 Introduction

HEARTS[^1] is an expert system written in KEE and InterLisp-D for the Xerox Dandelion-series computer. It is a full system for playing the card game of hearts and for developing and integrating different types of computerized hearts players. A core system (called the *Administrator*) knows the rules of the game and co-ordinates the playing. The Administrator is written in LISP. *Players* are the actual players of the game. There may be any number of different kinds of players, written in LISP, KEE, or LOOPS, and any four of them may get together for a game of hearts. Currently, there are four types of players: a Clown, who plays random legal cards, a Conservative Player, who plays with a very limited strategy, a Human Player, which is an interface to a human user, and an Expert Player, which is a fairly sophisticated expert system. In addition, the system is capable of playing over a network with any number of players on other Dandelions.

Most of the attention of this write-up will be on the Expert Player, which was written in KEE. Some time must necessarily be devoted to explaining the interface between the players and the Administrator to gain a full understanding of the Expert Player's functioning. An introductory section explaining the rules and basic human strategies of hearts is also included. If you are familiar with the game of hearts, this section may be skipped. (However, section 2.2 *Major Human Strategies* contains useful back-pointers to the motivation behind the structure of our Expert Player.)

## 2 The Game Of Hearts

### 2.1 The Rules

Hearts is played with one full deck of cards and four players, each playing for him/herself. The basic idea of the game is to win as *few* points for yourself as possible, through taking or losing tricks. A full game of hearts lasts until one player reaches 100 points. At this point, the game ends and the player with the least points wins.

The deck is first shuffled and dealt out, so that each player begins with 13 cards. The players examine their cards, and then pass away three cards they don't want to another player. The direction in which to pass rotates from deal to deal: in the first deal, the cards are passed to the left, in the second deal, across the table, and third, to the right. The fourth deal is a "hold" hand, and no passing takes place. After the fourth deal the cycle begins again. Of course, a player may not examine the cards passed to her until she has put down her pass cards.

Once each player has 13 cards again, the play begins. In the first trick, the player with the two of clubs must lead that card. Thereafter, each player must follow suit if possible. If this is not possible, he may "dump" any card in his hand on the trick. The person who has played the highest card in the suit which was lead (e.g., clubs for the first trick) takes the trick and may lead any card in his hand. There are two special rules: no hearts or the queen of spades may be placed on the first trick, and hearts or the queen of spades (referred to as the *Maggie* or *the Black Bitch*) may not be lead until someone has dumped one of them on another trick.

A player gets one point for every heart in a trick she wins, and 13 points for taking the Maggie. Taking a heart or the Queen is often called "eating" points, so talk of "munching", "chomping", or "masticating" merely refers to taking points, not some bizarre ritual with the deck. There is an important "however" to this scoring: if a player manages to take all 26 points (13 hearts + 13 points for Maggie), he either loses 26 points or adds 26 points to the score of all the other players. This phenomenon is known as "shooting the moon", and gives the game any excitement it has for human players. For computer players, it is merely a big pain in the butt.

### 2.2 Major Human Strategies

The nature of the game lends itself to three basic types of playing: Minimizing, or trying to take as few points as possible; Shooting, trying to take all the points; and Eclipsing (as in an eclipse of the moon), trying to stop someone else from shooting. Other, more subtle strategies which occur near the end of a game (such as trying to "screw" a particular player when one is winning so that she will lose), will be ignored in this discussion.

1. **Minimizing** - When a person has a large number of losers (cards which aren't likely to win a trick) in his hand, it is usually best to try to win as few tricks as possible. This is accomplished by passing high cards and by playing low when possible and as high as possible when safe or unavoidable. Some sophistication is necessary in deciding which suits are best to lead and which cards are best to dump. Most beginning players exclusively use this strategy, and it has been suggested that it is optimal for a huge majority of hands dealt.

2. **Shooting** - When a person is feeling adventuresome or has a hand with many winners, shooting is preferred. Shooting is a much more subtle strategy than Minimizing, because if a player has a hand which is not quite perfect, another player might stop the shooter if the shooter makes it too obvious he is shooting. Usually, a shooter will try to play his losers early on the game, hoping the other players will play their high cards early, leaving him a free hand to win all the tricks with points in the last part of the game.

3. **Eclipsing** - There are many signs that a player is shooting the moon. For example, a pass with low cards, or too many tricks with points taken by a single player are strong indications of shooting. When a player thinks another player is shooting, it is advantageous to stop her. This is usually done by dumping losers and non-point cards on a shooter's tricks, and by taking any points possible. Once more than one player has points, nobody can shoot and this strategy may be abandoned in favor of Minimizing.

## 3 System Overview

### 3.1 System Administrator

The system administrator is given a list of four player objects, and it performs the functions normally associated with the "house" in cards: it shuffles, deals, and keeps score. In addition, the administrator controls a graphic "card table" which displays the players' plays, number of tricks in the current deal, and score for the game (excluding the current deal). The administrator interacts with the players through a message passing protocol; each player object must be able to respond to a set of messages which inform the player what his hand is, when to pass, what cards were passed to him, when to play, and the results of each trick and each deal. Since the administrator is purely non-knowledge-based and conventional, its workings need not be discussed.

### 3.2 Players

Each player is a unique LISP object. The type of the player (LISP, KEE, or LOOPS), as well as a mapping from the standard Administrator message names to the particular message format of that object's type, is stored in the object. Any number of players of any type may exist in the environment at one time, and any four of these may play in a particular hearts game.

#### 3.2.1 Functionality

Each player must be able to respond to the following message types:

`GiveHand`
: Given a hand (which is a LISP datatype) and a player number (from 1 to 4, used in accessing the players), the player must store this information.

`PassOut`
: This message tells a player it is time to pass, and gives her a pass direction. The message function must return three cards from the player's hand.

`PassIn`
: This message gives the player its three pass cards from another player. The player must integrate these into its hand.

`Play`
: This message tells a player it is time to play a card. It gives the player the partially completed trick (which is another datatype) and expects a legal play from the player's hand as a result.

`Trick`
: This optional message gives the completed trick information to the player. Information available from the trick includes which player led, the cards played, and who won the trick. The score and other information about the trick can be computed with several datatype utility functions.

`Results`
: This optional message gives the result of the entire deal; this is basically the score of each player.

Of course, in actual players the message functions do much more than the bare minimum: they must have methods for computing the "best" play or pass, for storing the results of tricks and deals, and any other auxiliary processing desired.

#### 3.2.2 Existing Player Types

There are currently four types of players available.

1. **The Clown** - This is the simplest, dumbest possible player. It will pass three random cards from its hand, and play a random legal card. It is a LISP player, and its basic use is in testing the administrator and other players for basic competence.

2. **The Human Player** - This player implements a graphic interface with a user. The user's hand is displayed, and the user may mouse on the cards to be selected for passing and playing. The player may also request that her legal cards be highlighted. It usually doesn't make sense to have more than one of this type of player on a particular machine. However, up to four human players may play hearts over a network of Dandelions. Imagine the excitement of playing this way! Much better than a few six-packs and wings with the gang.

3. **The Conservative Player** - This is a somewhat more sophisticated LISP player. It has a basic knowledge of the Minimizing strategy, which it uses exclusively (hence the name). Its knowledge is encoded in long strings of `if...elsif...elsif...` statements covering the situations it can handle. As a conservative player, it actually plays pretty well most of the time. This does not demonstrate the efficacy of this sort of player as much as the simplicity of the Minimizing strategy. Surprisingly, in most games a player of this type will perform as well an Expert Player, lending confirmation to the theory that Minimizing is far and away the most important hearts strategy. Since all of the knowledge encoded in this player was translated into KEE rules for the Expert Player, this knowledge will not be discussed here.

4. **The Expert Player** - The actual expert system of this project. Expert players determine their passes and plays based on their own strategies, which are in turn determined by their cards and by their estimate of their opponents' strategies. Thus, the Expert Player (theoretically) performs all of the functions an actual human player does in playing the game. The expert player also has a simple "explanation" facility: it prints out a one line explanatory message for every play it makes.

   When the Expert Player receives a hand, it determines an initial strategy. Its pass is based on this strategy. When the player receives its pass, it determines a new strategy based on this pass, and it also begins to model the opponent who gave the pass. At each play, the player uses its current strategy to determine which card to play. At each trick, the player updates the opponent models based on the trick results and reviews its own strategy in light of the updated opponent models and the trick. This process is repeated until the hand is over. Currently no useful knowledge is kept between deals, so there is no overall game strategies.

   A more detailed discussion of the Expert Player can be found in the next section.

Each computer player is capable of operating in closed-hand or open-hand mode; in open-hand mode a window displaying the player's hand and any messages it may wish to display is put on the screen for each player.

## 4 The Expert Player

### 4.1 Knowledge Base Structure

A KEE knowledge base called *expert* contains all of the information necessary to create and use Expert Players. This information consists of classes of objects for players, rules for use by Expert Players, and subsidiary classes of objects for representing other knowledge useful to the Expert Players. The actual player objects and the rules will be discussed separately.

#### 4.1.1 The Expert Players Themselves

A complete Expert Player is a composite object consisting of one main unit, the Expert Player unit; and four auxiliary objects, the History and the Opponent Models. All of these units are created at once, and they are tied together through pointers in slots.

1. An **Expert Player** unit is a member of the class *expert.players*. An OwnSlot in *expert.players*, called *Create*, is a method which creates a particular expert player, whose name is chosen from a list of possible expert names. The Expert Player inherits methods from the *expert.player* class which handle the Administrator interface. In addition, the Expert Player inherits slots which contain information relating to some of the game history, the current strategy, the player's "personality", and other related information.

2. A **History** unit - This unit is a member of the *histories* class. Its main responsibility is to keep track of the cards played in the current deal. It remembers all of the cards played in each suit, which card in each suit is the highest and lowest card left to play, and, through a multitude of methods, is able to supply information about the "equivalence classes" of cards. In any card game played like hearts (such as bridge), certain cards become "equivalent" to each other because cards in between them have either been played or are in the player's hand. This is crucial information in deciding which card to play to achieve the optimum psychological effect, and in deciding which cards are really winners and losers.

3. Three **Opponent Model** units - These units are members of the *opponent.models* class. The most important function of a hearts opponent model is to determine the strategy of the opponent; in particular, to decide if that opponent is trying to shoot the moon. The opponent models also keep track of the cards played by an opponent, the cards known to be in the opponent's hand, and the suits that the opponent is known to be void in. While much of this information is currently unused, it is essential for playing a truly expert game. As any bridge player knows, knowing the opposition is the only way to guarantee perfect play.

#### 4.1.2 Expert Player Rules

Although new units are created for each new Expert Player, all of these players share one set of rules. These rules are also contained in the *expert* knowledge base. This has the implication that each rule must determine which Expert Player it should use in its evaluation. This is easy using KEE's RuleSystem2, which allows variables in the rules: the first premise of each rule gets the value of the OwnSlot *CurrentPlayer* in the *expert.players* unit and uses this value for accessing all information for the rule. Each player is responsible for putting a pointer to itself in the *CurrentPlayer* slot before it invokes a rule class.

We use backward chaining exclusively in the invocation of the rule classes. This makes sense; choosing a strategy or a card to play or pass is an inherently goal-oriented process. Thus each of the rules within a class which accomplishes the purpose of that rule class has a conclusion with identical form: e.g., rules which determine the card to be played have a conclusion `(THE PlayCard OF ?Self IS ?Card)`, where `?Self` is the *CurrentPlayer* described above and `?Card` is determined by the rule.

An important question to consider when using backward chaining is the order of the rule firings. The default order procedure used in KEE is to test next the rule with the fewest premises; generally, the most general rule. This is inappropriate for our case, where each rule has a pretty much arbitrary number of premises. In hearts, certain situations have priority over others in determining which card to play; for example, when a player is Minimizing and can dump a card, it is usually more appropriate to dump the Maggie if one has it then a winning card in some other suit. Thus we use a weighting scheme to determine rule firing order. Each rule has a slot *WEIGHT*; the rules are tested in descending order of *WEIGHT*.

The rules are subdivided into rule classes according to their purpose. We have identified three major rule classes, and each of these are subdivided into several smaller classes. This division of labor has three advantages:

1. **The individual rules are smaller** - Since each rule class is only invoked in the situation where it is appropriate, the rules do not have to explicitly check that this situation exists. For example, the rules for leading when the strategy is Minimizing do not have to check in their premises that the strategy is Minimizing and that no cards have been played yet in this trick (or that they won the last trick).

2. **The system runs faster** - The backward chaining unifier must attempt to match the desired conclusion with the conclusion of every rule in the rule base. The larger the rule base, the longer this process takes. Also, if certain rules have identical conclusions, but are situationally different, the rule interpreter (which is already quite slow) must spend extra time evaluating the premises which determine this.

3. **Debugging is easier** - Editing a rule class consisting of almost one hundred rules, some of which are rather long and involved, is not our idea of a Good Time. It is much easier to examine and think about a much smaller set which are all functionally related. Since the rule classes are situationally differentiated, when an error occurs it is easy to determine which rule class has bombed.

The three major rule classes, their function and sub-classes are described below:

1. **Passout Rules** - These rule classes are responsible for determining the three pass cards of the player. Each successfully invoked rule may choose from one to three cards to pass, depending on how many have been chosen previously by other rules. There is a Passout rule class for each strategy except Eclipsing, which cannot be a strategy until a player guesses that an opponent is shooting, which cannot happen until after the pass.

   a. **Minimizing Passout** - These rules pass the highest cards, an unsupported Maggie or high spades[^2], and other possible point-taking cards.

   b. **Shooting Passout** - If a player's hand looks good for shooting, it might try the opposite of the Minimizing pass - it might pass any cards it thinks *won't* take any tricks. Low hearts are particular favorites for a shooting pass, since a heart trick, if lost, would ruin the shoot.

2. **Play Rules** - These rule classes determine which card is to be played. In addition to dividing the rule classes by strategy, each strategy rule class is further divided into three other classes: dump, play, and lead. The strategies for these three situations are very different, and rarely overlap. When they do overlap, the rule sharing mechanism conserves space. There are thus nine distinct play rule classes, and you will thank us for not describing each in gory detail.

3. **Evaluation Rules** - These rule classes determine "higher level" information about the game - that information pertaining to the strategies of the game players. There are two subclasses of the Evaluation rules: Strategy Determination rules and Opponent Modeling rules.

   a. **Strategy Determination** occurs when the hand is first received, after the player receives his pass, and after every trick. Initially, the hand is evaluated for shooting power: high cards and few losers, especially in hearts. After the pass, the hand is re-evaluated for shooting strength. If the hand is not deemed strong enough to shoot, the strategy is initially set to Minimizing. At every trick, the player checks if one its opponents is probably shooting; if so, the player turns to the Eclipsing strategy, with the shooting opponent marked as the Shooter. The player also checks if he can still theoretically shoot the moon, if that is his strategy; if he can definitely shoot the moon from that point, if his strategy is Minimizing; or if Eclipsing has succeeded against a shooting player, if he is Eclipsing. Otherwise, the current strategy is continued.

   b. **Opponent Modeling** is done after receiving the pass (when it is only done on the opponent who passed the cards) and after every trick to all opponents. Opponent Modeling rules are somewhat different from other rules in the system. An intuitive model of computing an opponent's strategy is to gather evidence from trick to trick that the player is (for example) shooting. These rules utilize the KEE Certainty Factor package, which is an implementation of EMYCIN-type certainty factors, in order to build up evidence for each possible strategy of that opponent. When the certainty reaches a particular threshold, the player Strategy Determination rules will utilize this information in changing strategies.

      Since the opponent modeling rules must be invoked three times at every trick (once for each opponent), they are the major time sink of the system, and most humans spend most of their time in deciding plays, and no noticeable time in "opponent modeling" or "strategy evaluation". This is undoubtedly due to the parallel processing available in a human situation - humans can do the evaluation while other players are thinking.

About fifteen percent of the playing rules in our system are useful in more than one situational context. For example, a rule which says to play the lowest card in the hand is a common default for many strategies. These rules may be *shared* by multiple rule classes. This provides some space saving; the tradeoff is that the WEIGHTs for the other rules in rule classes using shared rules must be worked around the WEIGHTs of the shared rules.

#### 4.1.3 Other Represented Knowledge

Aside from the rules and the actual player knowledge, some other knowledge is stored of the knowledge base. This information is permanent, unlike the ephemeral Player units.

1. **Strategies** - Each strategy has its own unit which is a member of the *strategies* class. A strategy unit contains a method which will invoke the proper rule classes for passing, leading, dumping, and following suit for that strategy.

2. **Personalities** - Many times in the rules certain arbitrary thresholds are assigned for various decisions. All of these are slots in the *personalities* class. Each member of this class has a unique set of values for these thresholds, and a player may use any of these members as its own personality. A player's personality may decide how readily it decides to shoot, or how sensitive it is to shooting behavior on the part of the opponents - all actual human player traits.

### 4.2 Functionality

At this point the reader will probably be thinking, "All this sounds nifty, but how does it hang together? What happens inside one of these 'Expert Players' during a game of hearts?" To illustrate the functioning of an Expert Player, we will examine parts of two games. The complete game records can be found in Appendix III; relevant portions will be reproduced here.

To start any game of hearts, a user invokes the `LHearts` procedure; usually through the HEARTS system icon. This procedure is passed a "configuration" of players which tells what type of player to put in each game position. This procedure knows how to create players of each type; we enter each scenario assuming that the Expert Player has been created and put in a game situation.

#### 4.2.1 Example 1 - Shooting the Moon

> **[Figure 1 — PDF p.8: *Dostoevsky's dealt hand* — the hand dealt to Dostoevsky for Example 1.]**

```
Dostoevsky's dealt hand

Clubs:      3 J Q K
Diamonds:   2 J Q K A
Hearts:     J A
Spades:     Q (The Maggie) A

Figure 1: The hand dealt to Dostoevsky (for Example 1)
```

In this example we will focus on Dostoevsky, an Expert Player who will shoot the moon against three other Expert Players. Only the passing and one trick will be examined as most of the tricks shared the same pattern in this particular game.

1. **GiveHand** - Dostoevsky's GiveHand method is called by the Administrator, informing him that the hand is beginning. Dostoevsky's hand (see Figure 1) is stored in the *Hand* slot of the player unit and initializes many other slots in his various units. No reasoning is done.

2. **PassOut** - The Administrator calls Dostoevsky's PassOut method, indicating that Dostoevsky should pass three cards, in this case to his left. The gears now begin turning inside Dostoevsky's "mind".

   a. Dostoevsky first puts a pointer to himself in *expert.players* for use by the rules.

   b. Then he invokes the *initial.evaluation* rules to determine a strategy for use in passing. There are only two *initial.evaluation* rules: *shoot.test* and *default.strategy*. Of these, *shoot.test* has the higher WEIGHT, so it is tried first[^3].

      The first four clauses of the premise initialize variables to be used in the rule. Note that the second clause, `(EQUAL ?Spades (Hand.CardsInSuit ?Hand 'S))`, performs a common function in our rules: it calls a LISP utility function to determine purely deterministic information, rather than invoking yet another rule which would determine the spades in Dostoevsky's hand and put this information in some slot.

      The fifth clause of the rule makes sure that the hand has enough strength in spades for shooting. A shooting player has to be able to take the Maggie; too many low spades or not enough high ones can ruin this. `CardList.HighSpades?` succeeds if the list of cards passed to it has any higher than the jack, and the second part of the OR tests if there less than some number (determined in the personality) of spades. In this example the variable `?Spades` has been set to `(QS AS)`, POMaxLowSpades of Dostoevsky's personality is 2, and so both halves of the clause succeed (although only the first is evaluated).

> **[Figure 2 — PDF p.9: Rule `shoot.test` in *initial.evaluation*.]**

```
Rule shoot.test -- WEIGHT is 100

(IF (AND (THE CurrentPlayer OF expert.players IS ?Self)
         (THE Hand OF ?Self IS ?Hand)
         (EQUAL ?Spades (Hand.CardsInSuit ?Hand 'S))
         (THE Personality OF ?Self IS ?Personality)
         (OR (CardList.HighSpades? ?Spades)
             (LEQ (FLENGTH ?Spades)
                  (THE POMaxLowSpades OF ?Personality)))
         (THE history OF ?Self IS ?Hist)
         (LEQ (FLENGTH (UNITMSG ?Hist 'NonWinners 'H))
              (THE POMaxLoserHearts OF ?Personality))
         (GEQ (CardList.BridgePoints (Hand.FaceCards ?Hand))
              (THE POMinShootPoints OF ?Personality)))
    THEN (THE Strategy OF ?Self IS ?Shooting))

Figure 2: Rule shoot.test in initial.evaluation
```

      The sixth clause ensures that there aren't too many hearts losers in the player's hand. The method `NonWinners` is in Dostoevsky's History, and it returns all the cards in the player's hand not equivalent to the winner of that suit (in this case the ace of hearts). In Dostoevsky's hand, the `NonWinners` in hearts is `(JH)`, the jack. Since there is only one of these, and the POMaxLoserHearts is 3, the clause succeeds.

      The last premise clause makes sure there is a good high card count in the hand as a whole. The utility function `CardList.BridgePoints` returns the point card of the hand's face cards using the Goren counting system for bridge hands (4 points for ace, 3 for king, etc.). In this case the hand has 31 points - far more than the POMinShootPoints of 15. Thus the premise as a whole has succeeded, and Shooting is asserted as Dostoevsky's strategy.

   c. Next, after some internal bookkeeping, Dostoevsky calls the PassOut method of his strategy, Shooting. This method merely invokes the rule class for shooting passes, called *shooting.passout*, repeatedly until three cards have been chosen. This rule class may be found on page 19 of Appendix II. The following events occur in this method in our example:

      i. In this first invocation of the rule class, the first rule tried, *pass.all.loser.h*, succeeds because the player has non-winner hearts and can pass them all. The jack of hearts is added to the passcards list.

      ii. In the second and third invocations, the first two rules, *pass.all.loser.h* and *pass.loser.h*, both fail because the only heart left in Dostoevsky's hand, the ace, is a winner. However, the third rule, *pass.lowest.non.s*, succeeds because Dostoevsky has a non-winner in clubs or diamonds in both cases. The two of diamonds and the three of clubs are passed, one in each invocation.

      iii. After the third invocation there are three cards in the *PassCards* slot, so the Shooting passout method returns those three cards.

   d. Dostoevsky's PassOut method now returns the three cards chosen by the Shooting passout method.

3. **PassIn** - Dostoevsky's PassIn method is invoked by the Administrator after all players have passed out[^4], and it is passed the three pass cards from the opponent on Dostoevsky's right. Dostoevsky adds the three cards to his hand, puts a pointer to himself in *CurrentPlayer*, and a pointer to his right opponent model in the *CurrentOpponent* slot in his main unit. Then he invokes the *opponent.passin.evaluation* rule class (found on page 3 of Appendix II), asking for *all* of the possible results to be found, rather than just the first as with the passing and playing rules. The difference is due to the use of the certainty factor paradigm in opponent modeling, in which all matched situations can add evidence of shooting; the first found incident is no different from the others. This also implies that the WEIGHT slot is irrelevent to opponent modeling rules.

   In our example game, the opponent has passed Dostoevsky the 9 and 8 of clubs and the 8 of diamonds. Going through the *opponent.passin.evaluation* rule class, we can see that the following rules succeeded:

   - *ope.min.is.normal* - This rule is the "default" rule. It asserts, in any situation, that the opponent has a high *a priori* chance of Minimizing. This falls in with the theory that Minimizing is the only crucial strategy for successful hearts playing.

   - *ope.low.pass* - This rule succeeds if the Goren point value of the pass received is less than or equal to (LEQ) a personality-derived threshold. In this case, the threshold is 0 and the point value of the pass is also 0. The rule asserts that the opponent has a good chance of shooting. As it turns out, the opponent is minimizing; he just has a very low hand (all of the high cards are in Dostoevsky's hand).

   After doing the opponent modeling, Dostoevsky must re-evaluate his own strategy to see if Shooting is still a viable strategy. The rule class for this is called *passin.evaluation*[^5]; it is invoked normally. Like the *initial.evaluation*, this rule class has only two rules: one to test if shooting is (still) possible, and another to set the strategy to Minimizing if shooting is not feasible. In this case shooting is still quite feasible; the strategy is unchanged and the PassIn method returns.

4. **Play** - In this particular game, Dostoevsky has such a strong hand that only one rule is needed for 10 of the 13 tricks - the rule that tells the shooting player to lead a winner (*slead.lowest.winner.except.QS*, page 15 of Appendix II). This rule is fourth in the weighting scheme; the following rules failed before this one succeeded:

   - *one.choice* - This is a rule shared by every rule class. It says that if there is just one legal card, play it. In all but the last trick, this rule fails for Dostoevsky.

   - *slead.hearts* - This rule leads a heart winner if the player has already won the Maggie and if he can win all the unplayed hearts. Since this is never the case for Dostoevsky, this rule always fails.

   - *slead.non.op.void.loser* - This rule tries to lead any losers that all opponents are known to have cards in. Playing losers when shooting is useful only when an opponent will not dump a point card on the trick; this rule checks for that. This rule probably should have fired early in the game, but as we look now we realize that one of the functions used in the rule was undefined at the time of the game[^6]. When a function is undefined, the rule interpreter assumes the premise was meant as an "unstructured fact" which another rule should conclude. The backward chainer found no rules that deduced `(CardList.EliminateSuits (UNITMSG ?Hist 'NonWinners NIL ?Legals) ?WinnerSuits))`, so this rule failed. As it turns out, this is probably just as well for Dostoevsky, since he made it quite handily without the rule.

   The rule that does succeed leads the lowest winner (not the Maggie) in the player's hand. The "lowest" winner is an attempt to stop anyone from noticing that the card is a winner; if Dostoevsky leads a 10, but has the jack through ace of that suit, it is harder to suspect him of shooting than if he lead the ace, despite the fact that the two cards are technically "equivalent".

5. **Trick** - The Trick message is sent to Dostoevsky after each trick is completed, and the completed trick is sent along as an argument. First, Dostoevsky stores away the trick and calls on its History unit to update its information on winners, losers, and cards played. Then opponent modeling is called for each opponent. In our case, the opponent modeling is irrelevant; it is done anyway in case it turns out that Dostoevsky can't shoot, reverts to Minimizing, and then discovers that someone else *can* shoot. The opponent modeling uses the *opponent.trick.evaluation.rules* rule class. In Dostoevsky's case, no shooting behaviour is detected in the other players. However, every other player in the game did notice Dostoevsky's shooting behaviour and changed strategies appropriately - to no avail, as it turned out.

#### 4.2.2 Example 2 - An interesting game

The game reproduced in the following pages demonstrates the basic competence of the Expert Player in many areas, and also certain intricacies of the debugging. The configuration of the game has two conservative players, Eisenhower and ElmerFudd; and two Expert Players, Kant and MarcelProust.

As the game opens (page A), we see that the two expert players have been dealt shooting-quality hands, and both decide to try to shoot. Unfortunately for Kant, Marcel's shooting pass sends him two losing hearts (the 2 and 3) and so he decides that Minimizing would be best after all. Marcel receives a typically high pass from Elmer, so he continues his shooting strategy. The situation at this point may be seen on Page D; note that the players "discuss" their moves in the little window above each of their hand-display windows. At this point, Kant has begun to suspect that Marcel might be shooting, since a pass with low hearts is very "eyebrow-raising".

This suspicion is confirmed after the first play, when Marcel plays a somewhat low card (the 10 of clubs)[^7]. As can be seen on page B, Kant (always a master of pure reason) has shifted to Eclipsing strategy. He leads low from a short suit on the second trick, and when Elmer, now void in clubs, dumps a heart, Marcel pounces on the trick. Then Marcel uses the rule that worked so well for Dostoevsky to lead a winner. Unfortunately for Marcel, Kant is now trying to save all his winners in order to stop Marcel's shoot. Marcel thus has no more good winners to lead on the third trick, so he leads a low spade, hoping to draw out the winners in that suit. Kant unavoidably takes this trick and pulls his smartest move of the game. He leads a winner in a suit that someone other than the shooter is void in, knowing that this other player (Elmer) will dump a heart on the trick, thus stopping the shooter. Of course, this move works, Marcel's shoot is foiled, and Marcel switches strategies to Minimizing.

Now the debugging portion of this game begins. After Marcel is foiled, Kant should switch strategies as well. Unfortunately, he stays in Eclipsing until someone else takes a point. Why is this? The rule that switches from Eclipsing to Minimizing (*eclipse.success*, found on page 2 of Appendix II) appears to be in order: it says that Eclipsing has succeeded if more than one player has points. Perhaps the error is in the procedure which determines how many players have points. An edit of this function (page F) reveals that it counts the number of players with *greater* than one point, rather than the number of players with *greater than or equal to* (GEQ) one point. This is changed, and the rule has since been observed to work.

After both players are Minimizing, the game continues as expected, with Eisenhower getting stuck with the Maggie and 3 points and Kant and Marcel continuing to take some points because of their top-heavy hands. Elmer, whose hand has only 3 Goren points in it, takes no tricks.

The careful reader will note one more anomaly in this game. Apparently, in the last 4 tricks, Kant switches back and forth between Minimizing and Eclipsing. This is due to a bug in KEE Certainty Factors. In the opponent modeling rule which determines that an opponent can't be shooting (*ote.no.shooting*, pages 2 and 3 of Appendix II), the conclusion asserts that the strategy of the opponent must be Minimizing with certainty 1 (absolute sureness). The package is supposed to remove all other possible values when some value is asserted with CF = 1. Unfortunately, it does not do this, and so the opponent is left shooting. Thus, on alternate tricks Kant concludes (from Minimizing) that an opponent is shooting, and on the next trick (from Eclipsing) he concludes that the shooter has been stopped, since more than one player have points. Like other mentioned bugs, this has subsequently been fixed by asserting Shooting with CF = -.99 in the *ote.no.shooting* rule.

---

### Appendix III — Game Records (Example 2)

> **[Page A — PDF p.13: printed game record for Example 2 (`HGAME.OUT;7`), reproduced verbatim below.]**

```
                              EXAMPLE 2
{MITFS1-E40:SLOAN SCHOOL:MASSINSTTECH}<RAMANA RAO>HGAME.OUT;7      5-May-86 18:41:11        Page 1


Players:
1 Kant0056
2 Eisenhower0057
3 ElmerFudd0058
4 MarcelProust0059

Dealt Hands:
                         Kant0056
                         C  (3 Q A)
                         D  (6 7 J K)
                         H  (5 J A)
                         S  (8 9 A)

MarcelProust0059                              Eisenhower0057
C  (4 8 9 J K)                                 C  (2 5 10)
D  (9 Q A)                                     D  (2 3 4 5)
H  (2 3)                                       H  (6 8 10 Q)
S  (4 Q K)                                     S  (5 J)

                         ElmerFudd0058
                         C  (6 7)
                         D  (8 10)
                         H  (4 7 9 K)
                         S  (2 3 6 7 10)

Passes
Pass Direction: Left
From Kant0056 to Eisenhower0057:              (3C 5H JH)
From Eisenhower0057 to ElmerFudd0058:         (QH JS 10C)
From ElmerFudd0058 to MarcelProust0059:       (KH 7C 6C)
From MarcelProust0059 to Kant0056:            (4C 2H 3H)

Tricks:
   1     2     3     4
  AC    2C*   10C   JC
  4C*   3C    QH    KC
  6D    5D    10D   AD*
  8S    5S    7S    4S*
  QC*   5C    9H    9C
  9S*   JH    6S    KS
  7D    4D    8D    9D*
  JD    3D    7H    QD*
  AH    10H   4H    KH*
  3H*   5H    JS    QS
  KD    2D*   10S   8C
  2H*   6H    3S    7C
  AS    8H*   2S    6C

Scores:
                    Game    Total
Kant0056            5       5
Eisenhower0057      18      18
ElmerFudd0058       0       0
MarcelProust0059    3       3


(5 18 0 3)
```

> **[Page B — PDF p.14: printed reasoning trace for Kant0056 (`HREASONS.OUT;2`), reproduced verbatim below.]**

```
{MITFS1-E40:SLOAN SCHOOL:MASSINSTTECH}<RAMANA RAO>HREASONS.OUT;2      5-May-86 18:07:34        Page 2

                         Reasoning for game of player Kant0056

Play  Strategy    Reason
AC    Minimizing  Min - playing high on first trick.
4C    Eclipsing   Eclipsing - leading a card in my shortest suit.
6D    Eclipsing   Eclipsing - playing my lowest card.
8S    Eclipsing   Eclipsing - playing my lowest card.
QC    Eclipsing   Eclipsing - leading a card in my shortest suit.
9S    Eclipsing   Eclipsing - leading a card in my shortest suit.
7D    Eclipsing   Eclipsing - playing my lowest card.
JD    Eclipsing   Eclipsing - playing my lowest card.
AH    Eclipsing   Eclipsing - going to go over the shooter on this trick with points.
3H    Minimizing  Leading a heart. What the hey.
KD    Eclipsing   One choice.
2H    Minimizing  Leading a heart. What the hey.
AS    Eclipsing   One choice.
```

> **[Page C — PDF p.15: printed reasoning trace for MarcelProust0059 (`HREASONS.OUT;2`), reproduced verbatim below.]**

```
{MITFS1-E40:SLOAN SCHOOL:MASSINSTTECH}<RAMANA RAO>HREASONS.OUT;2      5-May-86 18:07:34        Page 3

                         Reasoning for game of player MarcelProust0059

Play  Strategy    Reason
JC    Shooting    Shooting - going a little bit over.
KC    Shooting    Shooting - must take this one.
AD    Shooting    Shooting - leading a non-QS winner.
4S    Shooting    Leading lowest non-QS card.
9C    Shooting    Following lowest card.
KS    Minimizing  Playing last; must win trick; will play high.
9D    Minimizing  Leading lowest non-spade.
QD    Minimizing  Leading lowest non-spade.
KH    Minimizing  Leading lowest non-spade.
QS    Minimizing  Min - dumping the maggie. Heh, heh.
8C    Minimizing  Min - dumping my highest card.
7C    Minimizing  Min - dumping my highest card.
6C    Minimizing  One choice.
```

> **[Figure — PDF p.16 (Page D): "Window Image" screenshot — the Interlisp-D screen partway through Example 2. It shows four "Hearts window" panes: two labeled *Hearts window for "expert"* (MarcelProust0059 and Kant0056) and two labeled *Hearts window for OP* (Eisenhower0057 and ElmerFudd0058), each with Clubs/Diamonds/Hearts/Spades rows of card icons and a small message pane above it in which the players "discuss" their moves (e.g. "My strategy is Shooting", "New strategy is Shooting"). At the lower left is the *Hearts Card Table* showing "Pass Left", "Scores (0 0 0 0)", and the four player positions (Kant0056, Eisenhower0057, ElmerFudd0058, MarcelProust0059). The image is a low-resolution scan and its finer text is not legible.]**

> **[Figure — PDF p.17 (Page E): "Window Image" screenshot — a later moment in Example 2. Same four Hearts windows (expert MarcelProust0059 and Kant0056; OP Eisenhower0057 and ElmerFudd0058) with fewer cards remaining, message panes showing Eclipsing/Shooting discussion, and the *Hearts Card Table* showing "Scores (0 0 0 0)" and "Aces Left". Along the right and bottom edges are KEE tool panes: a rule/method class tree (listing rule names such as *shoot.lead*, *slead.non.s*, *slead.dump*, *slead.non.s.pick*, *dump.hes*, *dump.low*, *dump.w*, *sdump.l*, *sfol.las*, *sfol.dif*, *stump.l*, etc., partly legible) and a KEE.class listing at the bottom left. The scan is low-resolution and much of this text is not legible.]**

> **[Figure — PDF p.18 (Page F): "Window Image" screenshot — an Interlisp-D "Edit of function EP.NumberWithPoints" window showing the *buggy* version of the function, which counts players with strictly greater-than-one point. The visible code reads approximately `(LAMBDA (Self) (for Slot in (... (NoPoints LeftPoints RightPoints AcrossPoints)) count (GREATER (GET.VALUE Self Slot) 1)))` [?? function body partly illegible in scan], date-stamped `30-Apr-86`. This is the function discussed on p.12 as using *greater* rather than GEQ.]**

> **[Figure — PDF p.19 (Page G): "Window Image" screenshot — an Interlisp-D "Edit of function EP.NumberWithPoints" window showing the *fixed* version of the function, which counts players with greater-than-or-equal-to one point. The visible code reads approximately `(LAMBDA (Self) (for Slot in (QUOTE (NoPoints LeftPoints RightPoints AcrossPoints)) count (GEQ (GET.VALUE Self Slot) 1)))` [?? function body partly illegible in scan], date-stamped `30-Apr-86`. This is the corrected function referred to on p.12.]**

[^1]: Hearts Expert: A Real Time Sink

[^2]: A common playing strategy for a non-shooter is to lead spades in hopes that some other player has a singleton Maggie and will thus be forced to play and swallow it. Leading spades with this intention is called "queen hunting".

[^3]: A copy of this rule may be found in Figure 2

[^4]: If a human player has passed out, he is eliminated from the game. We have developed a simple expert system to determine if the human player has passed out: a single rule *too.much.time.elapsed* is used.

[^5]: Page 2 of Appendix II

[^6]: This has subsequently been rectified and the rule has been seen to work.

[^7]: Since the first trick can't have points, Minimizing players usually play high while Shooting players will usually play low.
