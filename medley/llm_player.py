#!/usr/bin/env python3
"""Helper for the HEARTS LLM player (medley/llmplayer.lisp): decide one move with an LLM.

Medley writes what the player's seat knows to a JSON file and runs this once per decision:

    python3 llm_player.py [--provider P] [--model M] [--effort E] [--timeout SECS] [--log FILE] REQUEST.json

--provider is anthropic (the Messages API, through the anthropic package) or openai (Chat Completions
on OpenAI or any compatible server, through the openai package).

The answer is a single line on stdout, an S-expression Interlisp can READ:

    (OK ((D . 9)) "plan for later moves" "remark for the Thoughts window" (IN OUT MS))
    (ERROR "what went wrong")

It always answers with one of those, so the game never waits on a failure; the Lisp side still
checks the card itself and falls back to a safe one on ERROR.

    --stub POLICY     answer without the API (see stub_reply); used by the headless tests
    --check           report whether Python, the SDK and a credential are usable
"""
import argparse
import json
import os
import re
import signal
import sys
import time

SUITS = "CDHS"
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
DECK = [s + r for s in SUITS for r in RANKS]
PASS_OFFSET = {"Left": 1, "Across": 2, "Right": 3}
MAX_PLAN_CHARS = 400

# Models that accept the server-side refusal fallback (others reject the parameter).
FALLBACK_MODELS = {"claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"

SYSTEM_PROMPT = """You are playing four-player Hearts, and you are trying to finish the game with \
the lowest score. You play one seat; the others may be programs or people. There are no partners \
or teams: every player is on their own. These are the exact rules of this game:

- Seats are numbered 1-4 and play proceeds 1, 2, 3, 4, 1. Each player holds 13 cards.
- Before each deal's play, players may pass 3 cards. Left passes to the next seat, Across to the \
seat two along, Right to the previous seat. Every fourth deal there is no pass.
- The holder of the 2 of clubs leads it to the first trick. Each later trick is led by the winner \
of the one before.
- You must follow the led suit if you can. The highest card of the led suit wins; there are no \
trumps. Aces are high.
- On the first trick, a player who cannot follow may not play a heart or the queen of spades \
unless they hold nothing else.
- Hearts may not be led until a heart has been played on an earlier trick, unless the leader holds \
only hearts. Playing the queen of spades does NOT break hearts.
- Each heart taken scores 1 point and the queen of spades scores 13.
- Shooting the moon: a player who takes all 26 points in a deal scores -26 for that deal. The \
other players' scores for that deal are unaffected.
- After a deal, if any total exceeds the over_score, the game ends and the lowest total wins.

Cards are written suit then rank: C, D, H or S followed by 2-10, J, Q, K or A, so S10 is the ten \
of spades and HQ is the queen of hearts.

Each message gives you everything your seat knows: your hand, your legal choices, the trick so \
far, every completed trick this deal, the cards you have not seen, which seats have shown a void, \
the scores, and the plan you left yourself last time. Think about what the others are likely to \
hold, about whether anyone (you included) could shoot the moon, and about the game score as well \
as this deal.

Answer with:
- plan: your current strategy for this deal, in under 40 words. You see it again on your next \
decision, so note anything worth remembering.
- remark: one short sentence on why you chose this move, shown to the people watching.
- the card or cards you choose, which must come from the choices you were given."""

_CARD_ENUM = {"type": "string", "enum": DECK}


def _schema(card_fields):
    props = {"plan": {"type": "string"}, "remark": {"type": "string"}}
    props.update({name: _CARD_ENUM for name in card_fields})
    return {"type": "object", "properties": props,
            "required": list(props), "additionalProperties": False}


# Fixed schemas on purpose: a new schema costs a compile on first use, so restricting the enum to
# each decision's legal cards would pay that again and again. choices_error checks legality instead.
PLAY_SCHEMA = _schema(["card"])
PASS_SCHEMA = _schema(["card1", "card2", "card3"])


# --- what the model is told ------------------------------------------------------------------

def card_points(card):
    return 13 if card == "SQ" else 1 if card[0] == "H" else 0


def next_seat(seat, by=1):
    return (seat - 1 + by) % 4 + 1


def seats_from(leader, count):
    return [next_seat(leader, i) for i in range(count)]


def describe_state(req):
    """The request plus what follows from it, so the model needn't re-derive the bookkeeping.
    Uses only the request, which holds only what this seat has seen."""
    seat = req["seat"]
    trick = req.get("trick") or {"leader": seat, "cards": []}
    history = req.get("history") or []
    state = {
        "decision": req["decision"],
        "your_seat": seat,
        "deal_number": req.get("deal"),
        "your_hand": req["hand"],
        "game_scores_by_seat": {str(i + 1): s for i, s in enumerate(req.get("scores") or [0, 0, 0, 0])},
        "over_score": req.get("over_score", 100),
        "your_plan_so_far": req.get("plan") or "(none yet)",
    }

    pass_to = None
    if req.get("direction"):
        pass_to = next_seat(seat, PASS_OFFSET[req["direction"]])
    if req["decision"] == "pass":
        state["pass_direction"] = req.get("direction")
        state["pass_to_seat"] = pass_to
        state["instruction"] = "Choose exactly 3 different cards from your_hand to pass."
        return state

    played = [c for t in history for c in t["cards"]] + list(trick["cards"])
    points = {i: 0 for i in range(1, 5)}
    voids = {i: set() for i in range(1, 5)}
    completed = []
    for t in history:
        order = seats_from(t["leader"], len(t["cards"]))
        led = t["cards"][0][0]
        for who, card in zip(order, t["cards"]):
            if card[0] != led:
                voids[who].add(led)
        points[t["winner"]] += sum(card_points(c) for c in t["cards"])
        completed.append({"plays": [{"seat": w, "card": c} for w, c in zip(order, t["cards"])],
                          "winner": t["winner"]})

    order = seats_from(trick["leader"], 4)
    now = len(trick["cards"])
    for who, card in zip(order, trick["cards"]):
        if card[0] != trick["cards"][0][0]:
            voids[who].add(trick["cards"][0][0])
    seen = set(played) | set(req["hand"])
    unseen = [c for c in DECK if c not in seen]
    passed = req.get("passed") or []

    state.update({
        "legal_choices": req["legal"],
        "current_trick": {"plays": [{"seat": w, "card": c} for w, c in zip(order, trick["cards"])],
                          "seats_still_to_play": [s for s in order[now:] if s != seat]},
        "hearts_broken": bool(req.get("hearts_broken")),
        "first_trick": bool(req.get("first_trick")),
        "completed_tricks_this_deal": completed,
        "points_taken_this_deal_by_seat": {str(i): p for i, p in points.items()},
        "queen_of_spades_played": "SQ" in played,
        "cards_you_have_not_seen": {s: [c for c in unseen if c[0] == s] for s in SUITS},
        "seats_known_void": {str(i): sorted(v) for i, v in voids.items() if v},
        "instruction": "Choose one card from legal_choices.",
    })
    if passed:
        state["you_passed"] = {"to_seat": pass_to, "cards": passed,
                               "not_yet_played": [c for c in passed if c not in played]}
    if req.get("received"):
        state["you_received_in_the_pass"] = req["received"]
    return state


def choices_error(req, cards):
    """Why these cards are not an acceptable answer, or None if they are."""
    if req["decision"] == "pass":
        if len(set(cards)) != 3:
            return f"You must pass 3 different cards, but chose {cards}."
        bad = [c for c in cards if c not in req["hand"]]
        return f"{bad} are not in your hand {req['hand']}." if bad else None
    if len(cards) != 1 or cards[0] not in req["legal"]:
        return f"{cards} is not legal here. The legal choices are {req['legal']}."
    return None


def state_message(req):
    # Compact: this is sent for every decision, and indentation would only cost tokens.
    return json.dumps(describe_state(req), separators=(",", ":"))


# --- the reply Lisp reads --------------------------------------------------------------------

def lisp_string(text):
    """One-line, ASCII, Interlisp-escaped ('%' is the escape character there)."""
    text = " ".join(str(text).split()).encode("ascii", "replace").decode("ascii")
    return '"' + text.replace("%", "%%").replace('"', '%"') + '"'


def lisp_card(card):
    return f"({card[0]} . {card[1:]})"


def ok_reply(cards, plan, remark, usage=(0, 0, 0)):
    cards_text = " ".join(lisp_card(c) for c in cards)
    usage_text = " ".join(str(int(n)) for n in usage)
    return (f"(OK ({cards_text}) {lisp_string(str(plan)[:MAX_PLAN_CHARS])} "
            f"{lisp_string(remark)} ({usage_text}))")


def error_reply(message):
    return f"(ERROR {lisp_string(message)})"


# --- Claude, and servers speaking its API ------------------------------------------------------------------------------

class HelperError(Exception):
    pass


def card_fields(decision):
    return ["card1", "card2", "card3"] if decision == "pass" else ["card"]


def request_params(req, args, messages):
    params = {
        "model": args.model,
        "max_tokens": 16000,
        "system": SYSTEM_PROMPT,
        "thinking": {"type": "adaptive"},
        "output_config": {
            "effort": args.effort,
            "format": {"type": "json_schema",
                       "schema": PASS_SCHEMA if req["decision"] == "pass" else PLAY_SCHEMA},
        },
        "messages": messages,
    }
    if args.model in FALLBACK_MODELS:
        # Through extra_body because older SDKs (0.102 here) lack the keyword.
        params["betas"] = [FALLBACK_BETA]
        params["extra_body"] = {"fallbacks": "default"}
    return params


def ask_claude(req, args, client):
    """Return (cards, plan, remark, input_tokens, output_tokens).  One retry on an unusable answer."""
    messages = [{"role": "user", "content": state_message(req)}]
    input_tokens = output_tokens = 0
    problem = None
    for _attempt in range(2):
        params = request_params(req, args, messages)
        # betas needs the beta endpoint; without it, the plain one.
        create = client.beta.messages.create if "betas" in params else client.messages.create
        response = create(**params)
        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        if response.stop_reason == "refusal":
            raise HelperError("the model declined this request")
        if response.stop_reason == "max_tokens":
            raise HelperError("the model ran out of tokens before answering")
        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise HelperError(f"no answer text (stop_reason {response.stop_reason})")
        answer = json.loads(text)
        cards = [answer[f] for f in card_fields(req["decision"])]
        problem = choices_error(req, cards)
        if not problem:
            return cards, answer["plan"], answer["remark"], input_tokens, output_tokens
        # Replay the assistant turn unchanged (thinking blocks must not be edited).
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": problem + " Answer again."})
    raise HelperError(f"unusable answer after a retry: {problem}")


def run_claude(req, args):
    try:
        import anthropic
    except ImportError:
        return error_reply("the anthropic package is not installed (pip install anthropic)")
    started = time.monotonic()
    try:
        # Attempts share the budget, so the helper answers before Lisp's own deadline.
        client = anthropic.Anthropic(timeout=args.timeout / 3, max_retries=2)
        cards, plan, remark, in_toks, out_toks = ask_claude(req, args, client)
    except HelperError as e:
        return error_reply(e)
    except anthropic.AuthenticationError:
        return error_reply("the API rejected the credential (check ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN)")
    except anthropic.APIStatusError as e:
        return error_reply(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError as e:
        return error_reply(f"could not reach the API: {e}")
    except (anthropic.AnthropicError, TypeError, KeyError, json.JSONDecodeError) as e:
        # TypeError is how SDK 0.x reports having no credential at all.
        return error_reply(f"{type(e).__name__}: {e}")
    elapsed_ms = (time.monotonic() - started) * 1000
    return ok_reply(cards, plan, remark, (in_toks, out_toks, elapsed_ms))


# --- OpenAI and compatible servers -----------------------------------------------------------

def openai_system_prompt(decision):
    # Servers vary in honouring response_format, so the prompt asks for the same shape too.
    keys = ", ".join(["plan", "remark"] + card_fields(decision))
    return (f"{SYSTEM_PROMPT}\n\nReply with only a JSON object with the keys {keys}. Each card is a "
            "string such as \"S10\".")


def openai_response_format(decision):
    return {"type": "json_schema",
            "json_schema": {"name": f"hearts_{decision}", "strict": True,
                            "schema": PASS_SCHEMA if decision == "pass" else PLAY_SCHEMA}}


def read_answer(req, text):
    """Return (cards, plan, remark, problem) from text that may wrap the JSON in reasoning or a code
    fence, as servers without structured output do."""
    text = re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    try:
        answer = json.loads(text[start:end + 1]) if start >= 0 else None
    except json.JSONDecodeError:
        answer = None
    fields = card_fields(req["decision"])
    if not isinstance(answer, dict) or not all(isinstance(answer.get(f), str) for f in fields):
        return None, None, None, f"That was not a JSON object with the keys {fields}."
    cards = [answer[f].strip().upper() for f in fields]
    return cards, answer.get("plan", ""), answer.get("remark", ""), choices_error(req, cards)


def ask_openai(req, args, client, bad_request_error):
    """Return (cards, plan, remark, input_tokens, output_tokens).  One retry on an unusable answer."""
    messages = [{"role": "system", "content": openai_system_prompt(req["decision"])},
                {"role": "user", "content": state_message(req)}]
    # No token limit and no reasoning effort: servers and models differ on which of those they
    # accept, and reject the rest.
    options = {"response_format": openai_response_format(req["decision"])}
    input_tokens = output_tokens = 0
    problem = None
    for _attempt in range(2):
        try:
            response = client.chat.completions.create(model=args.model, messages=messages, **options)
        except bad_request_error:
            if not options:
                raise
            # Probably no structured output here; the prompt asks for JSON anyway.
            options = {}
            response = client.chat.completions.create(model=args.model, messages=messages)
        if response.usage:
            input_tokens += response.usage.prompt_tokens or 0
            output_tokens += response.usage.completion_tokens or 0
        if not response.choices:
            raise HelperError("the server returned no answer")
        choice = response.choices[0]
        if getattr(choice.message, "refusal", None) or choice.finish_reason == "content_filter":
            raise HelperError("the model declined this request")
        if choice.finish_reason == "length":
            raise HelperError("the model ran out of tokens before answering")
        cards, plan, remark, problem = read_answer(req, choice.message.content)
        if not problem:
            return cards, plan, remark, input_tokens, output_tokens
        messages.append({"role": "assistant", "content": choice.message.content or ""})
        messages.append({"role": "user", "content": problem + " Answer again."})
    raise HelperError(f"unusable answer after a retry: {problem}")


def run_openai(req, args):
    try:
        import openai
    except ImportError:
        return error_reply("the openai package is not installed (pip install openai)")
    started = time.monotonic()
    # A local server may need no key, but the SDK insists on one.
    api_key = os.environ.get("OPENAI_API_KEY") or (
        "not-needed" if os.environ.get("OPENAI_BASE_URL") else None)
    try:
        client = openai.OpenAI(api_key=api_key, timeout=args.timeout / 3, max_retries=2)
        cards, plan, remark, in_toks, out_toks = ask_openai(req, args, client, openai.BadRequestError)
    except HelperError as e:
        return error_reply(e)
    except openai.AuthenticationError:
        return error_reply("the server rejected the credential (check OPENAI_API_KEY)")
    except openai.APIStatusError as e:
        return error_reply(f"API error {e.status_code}: {e.message}")
    except openai.APIConnectionError as e:
        return error_reply(f"could not reach the server: {e}")
    except openai.OpenAIError as e:
        return error_reply(f"{type(e).__name__}: {e}")
    elapsed_ms = (time.monotonic() - started) * 1000
    return ok_reply(cards, plan, remark, (in_toks, out_toks, elapsed_ms))


# --- no API: tests and diagnostics -----------------------------------------------------------

def stub_reply(req, policy):
    """Stand-in for the model.  'lowest' plays the first legal card; the others misbehave in the
    ways the Lisp side must survive."""
    if policy == "error":
        return error_reply("stub error")
    if policy == "garbage":
        return "this is {not an S-expression"
    if policy == "die":
        sys.exit(3)
    if policy == "hang":
        time.sleep(100000)
    if policy == "slow":
        time.sleep(3)
    plan = f"stub plan after {len(req.get('history') or [])} tricks; 100% \"quoted\" text"
    if req["decision"] == "pass":
        cards = req["hand"][:2] + req["hand"][:1] if policy == "illegal" else req["hand"][:3]
    elif policy == "illegal":
        outside = [c for c in DECK if c not in req["legal"]]
        cards = outside[:1]
    else:
        cards = req["legal"][:1]
    return ok_reply(cards, plan, f"Stub ({policy}) chooses {' '.join(cards)}.", (0, 0, 0))


def check_reply(args):
    try:
        if args.provider == "openai":
            import openai as sdk_module
            # A server of your own may need no key.
            has_credential = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_BASE_URL")
        else:
            import anthropic as sdk_module
            has_credential = (os.environ.get("ANTHROPIC_API_KEY")
                              or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
        sdk = sdk_module.__version__
    except ImportError:
        sdk, has_credential = None, None
    return (f"(CHECK {lisp_string(sys.version.split()[0])} {lisp_string(sdk or 'not installed')} "
            f"{'T' if has_credential else 'NIL'} {lisp_string(args.model)})")


def log_decision(path, req, reply, seconds):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": time.time(), "seconds": round(seconds, 3),
                            "request": req, "reply": reply}) + "\n")


def parse_args(argv):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("request", nargs="?", help="JSON file describing the decision")
    p.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    p.add_argument("--model", default="claude-opus-5-5")
    p.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--timeout", type=float, default=300.0, help="seconds to answer within")
    p.add_argument("--log", help="append each decision to this JSONL file")
    p.add_argument("--stub", metavar="POLICY", help="answer without the API (see stub_reply)")
    p.add_argument("--check", action="store_true", help="report what is available and exit")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        print(check_reply(args), flush=True)
        return 0
    if not args.request:
        print(error_reply("no request file given"), flush=True)
        return 0
    # A helper Lisp has given up on must not outlive the game.
    if hasattr(signal, "alarm"):
        signal.alarm(int(args.timeout) + 60)
    started = time.monotonic()
    req = {}
    try:
        with open(args.request, encoding="utf-8") as f:
            req = json.load(f)
        ask = run_openai if args.provider == "openai" else run_claude
        reply = stub_reply(req, args.stub) if args.stub else ask(req, args)
    except (OSError, ValueError, KeyError) as e:
        reply = error_reply(f"bad request: {type(e).__name__}: {e}")
    if args.log:
        log_decision(args.log, req, reply, time.monotonic() - started)
    print(reply, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
