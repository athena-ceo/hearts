(* "A short game against the real API: this costs real money, a few cents on the default model.
    Not part of tests/run-all.sh.  Run with:
    ANTHROPIC_API_KEY=... tools/medley-headless --timeout 900 tests/llm-real-game.lisp
    LP_MODEL chooses another model, and LP_PROVIDER=openai the other kind of server:
    LP_PROVIDER=openai LP_MODEL=... OPENAI_API_KEY=... tools/medley-headless --timeout 900 tests/llm-real-game.lisp
    The model's reasoning is in out/llm-real-game.jsonl, and the table in the screenshot.")
(LOAD "{DSK}/hearts/medley/HEARTS")
(LOAD "{DSK}/hearts/dist/LLMPLAYER")
(HT.AUTOPLACE)
(SETQ LP.Provider (OR (UNIX-GETENV "LP_PROVIDER") "anthropic"))
(SETQ LP.Model (OR (UNIX-GETENV "LP_MODEL") "claude-haiku-5-5"))
(SETQ LP.Effort "low")
(SETQ LT.Log "/hearts/out/llm-real-game.jsonl")
(NLSETQ (DELFILE (CONCAT "{UNIX}" LT.Log)))
(SETQ LP.LogFile LT.Log)
(SETQ Game.OverScore 10)
(HT.CHECK "credential is set" (CADDDR (LP.Check)) T)
(LP.ResetStats)
(SETQ H.LastGame NIL)
(Hearts (for X in (QUOTE (LP CP CLOWN CP)) collect (H.MakePlayer X NIL)) NIL NIL)
(HT.CHECK "game finished" (AND (fetch Winners of H.LastGame) T))
(LP.Stats)
(HT.CHECK "the model was asked" (IGREATERP LP.Decisions 5))
(HT.CHECK "it never fell back" LP.Fallbacks 0)
(HT.CHECK "tokens were spent" (IGREATERP LP.InputTokens 0))
(SETQ LP.LogFile NIL)
(HT.CHECK "requests hold only what the seat may know" (LP.ParseReply (LP.ReadProcessLine (CONCAT "python3 /hearts/tests/check_llm_log.py " LT.Log))) T)
(HT.SNAP "llm-real-game")
