# What I Learned — Harley Davis

*Reflective report on the 1986 HEARTS project (MIT 6.871), by Harley Davis. Transcribed from `original/hearts-harley-report.pdf` by Claude Code (Anthropic coding agent). Wording is verbatim; only the layout is reformatted as Markdown.*

## 1 The Problem

### 1.1 Initial Selection

Hearts is a relatively simple card game (compared to bridge, at least) commonly played by groups of friends who want to get together and have a good time without exerting themselves too much while retaining the competitive feeling. It does have some intricacies, and a serious hearts player can devote much time to brainwork while playing. The game also involves some low-level psychological skill in keeping other players unsure about one's intentions through careful card-playing.

Both Ramana and I have been playing hearts for many years, and we consider ourselves skilled at the game - as much "expert" as anyone we know. In fact, we believe we have mastered the game long ago, and that there are few, if any, frontiers left in the actual playing of the game. It is just this level of ease with the game that leads us to believe that it is a prime candidate for an expert system - it is, in a way, the "last frontier" of hearts for us. It is also a project which has had enough inherent interest to keep our excitement level up; it has inspired us to put together a major-league hearts playing system.

### 1.2 Criteria Evaluation

A formal evaluation of the criteria given in lecture for good problem selection:

- **Traditional technology does not work** - There are two possible "traditional technologies": human brains and conventional programming.

    1. **Human brains:** Human minds work perfectly adequately for this task, and it is not foreseen that this program will in any way replace them. This is a more research-y, "real" AI type cognitive modeling program rather than an application-oriented, "corporate" AI project.

    2. **Conventional Programming:** The Conservative Player of our project is a conventional program, and it plays an adequate game of hearts. In addition, I have played with a MacIntosh version of hearts which plays a pretty good game. Our program could easily be converted into a conventional program; formally, our rule prioritizing scheme is merely converting a long `if...elseif...elseif` sequence into modular rules. Conventional programming could handle our task, and, as I will explain later, it may even be preferable in some ways to the KEE rule-oriented approach.

    The project therefore fails on this count.

- **Narrow domain of application** - The program plays hearts, and nothing else. It does not overflow too much into human psychology, unless one starts taking into account all sorts of formally irrelevant things like "Well, Joe has had too much to drink tonight; I guess it'll be pretty easy for me to shoot the moon." I claim success in this criteria.

- **There are recognized experts** - Well, they might not be nationally renowned, but certain people do win more than others. Success.

- **The experts are provably better than amateurs** - Yes; barring the exception that beginners tend to be more conservative and thus might win a few games that way. Experts are certainly more *sophisticated* than amateurs. Success.

- **The task is primarily cognitive** - The task is completely cognitive. Success.

- **Task takes a few minutes to a few days** - A typical hand takes about fifteen - thirty minutes; the computer program performs in close-to-human time, and it could be speeded up. Success.

- **Task is combinatoric** - At least near the beginning of the hand, when most of the opponent information is unknown, this is true. In any case, the full-scale solution space search is an uninteresting way of solving the problem. Qualified success.

- **Task involves chains of reasoning** - Theoretically, the chains of reasoning can get quite involved. In the development process we found many levels of strategies, sub-strategies, and intermediate conclusions. In the actual implementation, the chain of reasoning is generally limited to three or four levels: the opponents' strategies -> the player's strategy -> a few intermediate conclusions -> the play or pass cards. Qualified success.

- **Skill is taught routinely to neophytes** - Yes, it is. Actually, most neophytes get more pleasure out of figuring it out for themselves. Success.

- **Specialists agree on the knowledge** - As indicated by our "expert-debriefing" sessions, discussed in the next section, the experts tend to agree on the best plays in most situations. Disagreements are usually limited to the best of two close cards. There is certainly a universal agreement on the three major strategies; these fall out of the rules of the game. Success.

- **Right stage of knowledge formalization** - Books such as *Scarne On Cards* and *Hoyle's Rules of Cards* contain strategy information about hearts. Players are usually able to articulate meaningful reasons for their plays. These are signs that hearts is a well-understood and stateable problem. Success.

- **Data and case studies available** - Obviously; our Administrator generates case studies for us. Success.

- **Incremental progress is possible** - The proof is in the pudding. We developed our three computer players in series; the Expert Player was first taught to do Minimizing, then Shooting, then Opponent Modeling, then Eclipsing. Success.

- **Not time critical** - Not unless any human players will fall asleep or leave while waiting for the computer to play. No serious consequences; if the human leaves it's probably to her advantage anyway as card games are a waste of time. Success.

- **Freedom to fail** - Yes. Certainly more so than SDI. Success.

- **Resulting system would have high payoff** - In some ways, this precondition is contradictory to the others, especially the last few. Most of the really high-payoff programs must be absolutely reliable and speedy. Our program, which need not be reliable and speedy, has almost no payoff. We could try to sell it, but there probably aren't more than a few hundred Xerox Lisp Machines in the world. Failure.[^1]

So the hearts program wins on 14 out of 16 criteria. It is a reasonable expert system project. We ignore the fact that the two criteria it fails on are the two most important...

## 2 Knowledge Engineering

### 2.1 Knowledge Acquisition

Since both of us in the team were decent hearts players before the project began, most of the knowledge came from within our own skulls. However, in order to gain more insight into the problem, an understanding of the problems of "real" knowledge engineers, and different perspectives on the playing of the game, we also had several knowledge engineering sessions with two sets of experts: my partner's roommates, all avid hearts players; and a friend of mine who is an excellent player. We used Ramana's roommates after constructing the Administrator and the Conservative Player but before the major work on the Expert Player had begun. My friend was utilized after most of the Expert Player was finished in order to test it on an unbiased yet expert source.

#### 2.1.1 The Roommates

We decided that the best way to utilize the experts would be to get together in game-like situation and play, having each player explain his moves along the way. We would sit and take notes and suggest ideas to the players.

A problem we encountered initially was resistance on the part of the roommates to comment aloud on their plays, wishing to keep their strategies a secret from the other players. This problem was overcome with liberal amounts of alcoholic tongue lubricant, and soon all of the experts were gladly discussing the plays.

We played several "open-hand" games in which all of the experts would discuss the proper play for each player. This discussion led to very few major disagreements; generally, after a short period all of the experts would agree that one play was best or that several plays were too close to call. An effect of playing "open-hand" was that the experts could discuss optimal moves, given complete knowledge of the other players' hands. We tried to reduce the effects of this knowledge by interrupting an expert who was using this "illegal" knowledge.

There was one important consequence of having all of this knowledge: the heightened sense of "legal" and "illegal" knowledge led to many discussions involving the intricacies of keeping track of the history of a hand and how opponent modeling should proceed. Questions raised included: What can be deduced about an opponent's hand from the cards passed or played? How can this knowledge be put to use in determining a play? How often do human players take full advantage of this information? How often *should* human players take full advantage of this knowledge?

The answers to these and similar questions were intriguing. As it turns out, most humans do not keep track of most of the opponent information that they could. Many people remember important information such as the winners left in particular suits, but few remember all cards. The amount of information kept is also dependent on the strategy used by the human. Minimizing generally involves keeping track of the least information; shooting requires substantially more memory. Information is least useful near the beginning of a hand, when less is available anyway. Near the end, however, keeping track of all pertinent information can lead to situations where a player will know where every card is, and this knowledge can then be used to engage in what I call "tight reasoning" to figure out the optimal play. Most human players do not keep track of all the information, and they are thus not able to utilize tight reasoning. Rather, they continue to use heuristic judgments up to the very end.

Another "discovery" of this session was that people tend to overestimate their chances for succeeding at certain tactics. Players enjoy "shooting on a shoestring"; trying for the moon with the weakest support. In actual games, experienced players often end up with more points than beginners because they are overly bold in their own playing and overly suspicious of the opponents' playing.

We came away from the evening with our minds buzzing - not only from the copious amounts of Coors, but also with new ideas for the Expert Player. We hoped we would be able to give it a competitive edge over people by keeping track of all opponent information, using good rules consistently and without the irrational optimism that people have, and by engaging in the tight reasoning whenever possible. Unfortunately, we did not have time to write a tight reasoning module; more will be discussed later about the potential for such a module.

#### 2.1.2 The Friend

After the Expert Player had all of its basic functionality (including all three strategies and opponent modeling), we brought in my friend Adam to play against the Expert and to comment on its performance.

While this session did not generate nearly the amount of new ideas and thoughts that the roommate beer bash did, Adam pointed out several flaws with the Expert. In two games against the Expert, he handily shot the moon. In both cases at least one of the experts concluded that he was shooting; however, they failed to make the proper moves which would stop him. At this time, however, they were able to stop each other in a fair number of cases. Their failure to stop Adam indicated to us that the Expert Players were too optimized for themselves; they were not versatile in dealing with players whose strategy was too different from their own. Their performance degradation was not graceful, especially in the shooting case.

In the Minimizing case, where no players were shooting, the Expert Players more than held their own, indicating again that Minimizing is not an overly complicated process and that we had successfully implemented most of its intricacies.

The basic result of this session was the generation of many rules to handle previously unthought-of situations. It did not seem to necessitate a change in overall structure; merely enhancements to the individual modules.

### 2.2 Knowledge Formulation

This includes the actual formation and implementation of the rules and the system as a whole. As might be expected, the rule paradigm has both good and bad aspects; on the whole, I found more negative aspects than positive. This is in keeping with my previous experience with rule-based systems.

One early decision that we made had quite an impact on the rules. The rule paradigm seemed appropriate only for heuristic decision making: any "arbitrary" calls or non-deterministic decisions. For example, deciding whether to lead, follow suit, or dump is purely deterministic; it is more appropriate in a procedural context than a rule context. Similarly, extracting history information or data structure information is also deterministic - utility functions and methods were used for these cases. On the other hand, deciding which card out of many choices is the best to play, or which strategy another player is taking, is non-deterministic, heuristic information that we placed in rules.

This decision had the consequence that our chains of reasoning were shorter than they might have been. Much of the information that might have been determined through chains of information-gathering rules were eliminated in favor of direct procedure calls or message passing. This both made the existing rule classes easier to edit and debug and made the system as a whole run that much faster.

The decision also had the consequence that many rules were harder to debug. This is because of the previously-mentioned KEE RuleSystem2 "feature" which treats procedure calls to undefined LISP functions as "unstructured facts" which some other rule should derive. I would prefer the system to check if, indeed, some other rule derives these statements and to report, if desired, any completely underivable premises.

As stated, our rules are formally equivalent to `if...elseif...elseif...` type statements, with the order of the conditionals determined by the WEIGHT slots of the rule units. However, when editing rule classes these weights are not explicitly mentioned, nor are the rules automatically ordered in any printouts according to the weights. This has the negative consequence that it is difficult to determine within a certain rule which other rules will have already failed, and thus what conditional possibilities may be ignored. In the editing, there would be practically no difference between editing our rule classes and editing a giant `if` statement, except for the ordering.

The usefulness of rules compared to normal conditionals is that rules allow non-predetermined chains of reasoning to take place automatically. In our program, there is a level of explicit control structure between reasoning levels anyway. The usefulness of the rule paradigm is thus limited.

The rules themselves are often redundant. Variables defined in rules are only quantified over the extent of that rule's processing; they may not even be passed to rules called during the evaluation of premises (except through limited conclusion-premise unification). This means that variables used by multiple rules must be recomputed and rebound during every new rule evaluation. This is inefficient, and could be overcome within LISP procedures where variables have arbitrary scope.

As with any interpreted system, rule evaluation is slow. Extremely slow. S-l-o-w. Expert Players often took over fifteen seconds per move (including opponent modeling and playing) while the Conservative Players consistently played in under .5 seconds. This made debugging often a tedious process, with every hand between Expert Players taking more than 10 minutes. While the tracing facilities of the KEE RuleSystem often proved useful, they were probably not worth the extra factor of at least ten in the slowness of the process. I suspect that procedures would have been easier to debug, and they certainly would have made playing against the Experts a bearable process.

Rules do not allow internal control structure or CLISP calls.[^2] Any complicated processing had to be done through kludgey procedure calls. For a good example, see rule `elead.non.shooter.void`, the rule that allowed Kant to stop Marcel in the example game.[^3] This rule collects a list of suits that at least one opponent with hearts is known to be void in. Instead of proceeding in the obvious way and going through every opponent systematically, in an iterative statement, and gathering the void suits, the rule must call a message in the player unit which performs this function (`HeartyOpponentVoidSuits`). This message is used only in this rule. Other places where this would have been a desirable feature used different kludges to get around the problem (for example, the three rules for determining if one should go into Eclipsing strategy, pages 1 and 2 of Appendix II).

This summarizes my major complaints against the rule paradigm. Rules did provide a modular way to chunk informational units, and KEE's trace facilities are excellent (although slow). However, I think that this particular application of rules would better have been expressed through the much more versatile mechanism of procedures. There is no substitute for flexibility in expression.

## 3 The Future of HEARTS

Here I consider possible changes and enhancements to the HEARTS system Expert Player that would make it a really expert player, instead of the mere decent amateur it is now.

### 3.1 Enhancements to the present knowledge base

While the system handles most common hearts situations, it messes up at certain infrequent but crucial points. In particular, the Eclipsing rules are far from complete; they miss most opportunities to stop a shooter except the most blatantly obvious. Updating the knowledge base in this way would merely involve playing game after game, examining situations where the player does something stupid, and writing new rules and fixing old rules until it works.

A problem with unchecked growth of the individual rule classes has already cropped up: it is very difficult to determine the WEIGHTs of new rules as they are added into the rule class. This suggests that a useful purpose of the *personality* structure might be to list the WEIGHTs of certain key rules to reflect different possible priority schemes. Humans themselves have different priorities for certain situations; one person might dump a high card where another would dump a heart.

This leads to the next possible modification of the knowledge base...

### 3.2 More Rule Classes

Currently the rule classes are divided according to situational differences. However, there could be further subdivisions of the rule classes along other lines.

We could extend our chains of reasoning to include more complicated decision-making criteria. There are many phenomena and sub-strategies that humans take into account in making decisions that the Expert Player ignores. For example, people often want to win particular tricks to set up for some play, or to lead some card that they want to get rid of. This often happens in the early game, when a player will have a singleton high diamond, and she wants to win a trick as soon as possible to lead the diamond while everybody still has one. Currently, the Expert Player handles this phenomenon by leading such singletons when it has the lead, but it will not try to take a trick with the intention of leading this singleton on the next trick.

These and similar phenomena could be handled through more functional and goal oriented rule classes which would check, for example, if the player wants to take this trick and why. The invocation of these "rule packets" would be through conclusions using this information in the current rule classes. While the current KEE RuleSystem has no mechanism for using different rule classes for different premise evaluations, I am sure I could come up with some fix, as has been done for other KEE flaws.

### 3.3 Conversion to an all-procedure system

The major advantages of this, as stated above, would be vastly increased playing speed, more explicit statement of rule priorities, and greatly increased economy and flexibility of expression in the premises. What would this change involve?

The primary work would be in translating the current rules into conditional expressions. Since the premises of the rules are already expressed as AND/OR trees, and since there are KEE functions which translate WFFs into LISP-executable procedures, much of this work could be done automatically.

Once the rules were translated in their current form, they would have to be optimized. Variables bound in multiple rules (such as `?Self`, which would actually be completely unnecessary) would be eliminated after their first setting. Expressions which were done clumsily in KEE would be redone efficiently in LISP. More importantly, new types of premises which were too difficult to attempt in rules would have to be discovered and utilized.

If the reasoning chain were extended as suggested in the last section, those premises which invoked the functional rule classes would have to be identified and converted to procedure calls, where the procedures called would perform the decision formerly associated with the functional rule packets.

The opponent modeling rules present a slightly different case. In this case, the rules are equivalent not to an `if...elseif...elseif` situation, but rather an [if...if...if] situation, where each rule would be a separate conditional which was always tested.

The conversion to procedures is not overly complicated, and the benefits would be great. If I continue to work on this program, I will do this. Conventional programming (perhaps plus object-oriented programming) is still an excellent paradigm for the large majority of cases - at least until more efficient and developed tools appear on the market.

### 3.4 Use of more information

While the previous enhancement suggestions might increase the ability of the Expert Player to a near human level of competence, something extra must be added to give the program an edge to compensate for the basic human superiority in problem insight.

This would have to be the storing and using of more detailed opponent information. There exists a well-defined algorithm for determining the maximum amount of opponent hand information from the cards played.[^4] It basically involves propagation of constraints as expressed in the known voids of opponents, the cards already played, and the cards in the Expert Player's hand. No human is likely to be able to figure out all this information.

Once the maximum amount of information is determined, tight reasoning, or a complete search of the problem space, can be invoked to decide the optimal play, the play that will best achieve the goal of the current strategy. This search might involve mini-maxing on possible plays, or it might be some R* like procedure.

A crucial issue with the use of this search is the decision between using the normal heuristic rules to determine a play and using the tight reasoning. I suspect a heuristic rule which evaluated the amount of information currently available and the current importance of using more detailed reasoning might do the trick.

## 4 Conclusion

Building the HEARTS system taught me several things. Because I have built expert systems in KEE before, it did not teach me much about the technology that I did not previously know. However, I did learn the following:

- **Rules** - While I had always had a certain distaste for rules, thinking they were clumsy, slow, and inexpressive, I never formalized this dislike into words which could be used against the Management at my job. They often judge an expert system's quality based on the number of rules in the system. I will now be able to present more persuasive arguments against this.

- **Hearts** - While at first I believed that I pretty much knew everything about the game there is to know, I learned that I was wrong. There are certain intricacies and situations which I had glossed over in my previous playing, but that I am much more aware of now. In particular, the observations on the opponent knowledge may help my game in the future.

- **LISP** - Ramana taught me many things about the InterLisp-D environment and certain LISP techniques that I had never known.

This was a worthwhile and engaging project for me; it fulfilled a desire for this expert system that I have had since beginning my expert systems work.

[^1]: BUT... Imagine this scenario: I have a wealthy friend who pretentiously thinks he is a superb hearts player. I bet him $10,000 that my computer can beat him. He laughs, thinking no mere computer can foil his brilliant playing. He loses, I win $10,000, and the program has high payoff.

[^2]: CLISP is InterLisp's convenient shorthand for certain operations which are clumsily expressible in normal LISP notation.

[^3]: Page 10, Appendix II.

[^4]: I wrote this out one night while watching the Expert Player lose to the Conservative Player through basic incompetence.
