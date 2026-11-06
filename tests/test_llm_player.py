#!/usr/bin/env python3
"""Tests for the LLM player's helper (medley/llm_player.py), with no key and no spending: the API
paths run through the real SDKs against tests/mock_llm.py.

    python3 tests/test_llm_player.py
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "medley"), str(ROOT / "tests")]
import llm_player  # noqa: E402
import mock_llm  # noqa: E402

PLAY = {
    "decision": "play", "seat": 3, "deal": 2, "direction": "Left",
    "hand": ["D9", "DK", "S3", "SQ"], "legal": ["D9", "DK"],
    "trick": {"leader": 1, "cards": ["D4", "S5"]},
    "hearts_broken": False, "first_trick": False,
    "history": [{"leader": 4, "cards": ["C2", "C9", "CK", "H5"], "winner": 2}],
    "passed": ["SA", "H9", "D2"], "received": ["S3", "D9", "C7"],
    "scores": [23, 41, 12, 9], "over_score": 100, "plan": "Keep SQ for a void",
}
PASS = {"decision": "pass", "seat": 2, "deal": 1, "direction": "Right",
        "hand": ["C2", "C3", "D4", "S10", "SQ", "HA"], "scores": [0, 0, 0, 0], "over_score": 100}


class DescribeState(unittest.TestCase):
    def test_play_bookkeeping(self):
        s = llm_player.describe_state(PLAY)
        self.assertEqual(s["legal_choices"], ["D9", "DK"])
        self.assertEqual(s["points_taken_this_deal_by_seat"], {"1": 0, "2": 1, "3": 0, "4": 0})
        # Seat 3 led nothing: 4 led clubs and seat 3 (third to play: 4,1,2,3) showed H5.
        self.assertEqual(s["seats_known_void"], {"2": ["D"], "3": ["C"]})
        self.assertEqual(s["current_trick"]["plays"][1], {"seat": 2, "card": "S5"})
        self.assertEqual(s["current_trick"]["seats_still_to_play"], [4])
        self.assertFalse(s["queen_of_spades_played"])
        self.assertEqual(s["you_passed"]["to_seat"], 4)
        self.assertEqual(s["you_passed"]["not_yet_played"], ["SA", "H9", "D2"])
        self.assertEqual(s["game_scores_by_seat"]["2"], 41)

    def test_state_message_is_compact_and_complete(self):
        message = llm_player.state_message(PLAY)
        self.assertNotIn("\n", message)
        self.assertNotIn(": ", message)
        self.assertEqual(json.loads(message), llm_player.describe_state(PLAY))

    def test_unseen_excludes_hand_and_played(self):
        unseen = llm_player.describe_state(PLAY)["cards_you_have_not_seen"]
        everything = [c for cards in unseen.values() for c in cards]
        for c in PLAY["hand"] + PLAY["trick"]["cards"] + PLAY["history"][0]["cards"]:
            self.assertNotIn(c, everything)
        self.assertEqual(len(everything), 52 - 4 - 2 - 4)

    def test_moon_is_counted_from_the_queen(self):
        req = dict(PLAY, history=[{"leader": 1, "cards": ["S2", "SQ", "SK", "S4"], "winner": 3}])
        s = llm_player.describe_state(req)
        self.assertEqual(s["points_taken_this_deal_by_seat"]["3"], 13)
        self.assertTrue(s["queen_of_spades_played"])

    def test_pass_directions_match_the_game(self):
        # H.Deal routes Left as seat -> seat+1, Across as +2, Right as -1.
        for direction, target in (("Left", 3), ("Across", 4), ("Right", 1)):
            s = llm_player.describe_state(dict(PASS, direction=direction))
            self.assertEqual(s["pass_to_seat"], target, direction)


class Validation(unittest.TestCase):
    def test_play(self):
        self.assertIsNone(llm_player.choices_error(PLAY, ["DK"]))
        self.assertIn("not legal", llm_player.choices_error(PLAY, ["SQ"]))

    def test_pass(self):
        self.assertIsNone(llm_player.choices_error(PASS, ["C2", "C3", "D4"]))
        self.assertIn("different", llm_player.choices_error(PASS, ["C2", "C2", "D4"]))
        self.assertIn("not in your hand", llm_player.choices_error(PASS, ["C2", "C3", "D5"]))


class Replies(unittest.TestCase):
    def test_escapes_for_interlisp(self):
        reply = llm_player.ok_reply(["S10"], 'said "go"\nnow', "100% sure — yes", (1, 2, 3.7))
        self.assertEqual(reply, '(OK ((S . 10)) "said %"go%" now" "100%% sure ? yes" (1 2 3))')

    def test_plan_is_capped(self):
        reply = llm_player.ok_reply(["C2"], "x" * 5000, "r")
        self.assertLess(len(reply), llm_player.MAX_PLAN_CHARS + 50)


def run_helper(req, *flags):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(req, f)
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            llm_player.main([*flags, "--timeout", "30", f.name])
    finally:
        os.unlink(f.name)
    return out.getvalue().strip()


class Stub(unittest.TestCase):
    def test_lowest(self):
        self.assertTrue(run_helper(PLAY, "--stub", "lowest").startswith("(OK ((D . 9))"))

    def test_bad_file_still_answers(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            llm_player.main(["/nonexistent/request.json"])
        self.assertTrue(out.getvalue().startswith("(ERROR"))


class ThroughTheSDK(unittest.TestCase):
    """The real SDK and helper code, talking to the mock server."""

    def setUp(self):
        mock_llm.RequestLog.bodies.clear()
        mock_llm.RequestLog.headers.clear()
        self.saved = {k: os.environ.get(k) for k in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def start(self, behaviour):
        self.server = mock_llm.serve(behaviour=behaviour)
        os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{self.server.server_address[1]}"
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

    def test_play_request_and_reply(self):
        self.start("good")
        reply = run_helper(PLAY)
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn('"Mock plan: duck everything."', reply)
        self.assertIn("(100 20 ", reply)
        body = mock_llm.RequestLog.bodies[0]
        self.assertEqual(body["model"], "claude-opus-5-5")
        self.assertEqual(body["thinking"], {"type": "adaptive"})
        self.assertEqual(body["output_config"]["effort"], "medium")
        self.assertEqual(body["output_config"]["format"]["schema"], llm_player.PLAY_SCHEMA)
        self.assertEqual(body["fallbacks"], "default")
        self.assertNotIn("temperature", body)
        headers = {k.lower(): v for k, v in mock_llm.RequestLog.headers[0].items()}
        self.assertIn(llm_player.FALLBACK_BETA, headers.get("anthropic-beta", ""))

    def test_pass_uses_three_card_schema(self):
        self.start("good")
        self.assertTrue(run_helper(PASS).startswith("(OK ((C . 2) (C . 3) (D . 4))"))
        body = mock_llm.RequestLog.bodies[0]
        self.assertEqual(body["output_config"]["format"]["schema"], llm_player.PASS_SCHEMA)

    def test_illegal_answer_is_retried_with_the_turn_replayed(self):
        self.start("illegal_once")
        reply = run_helper(PLAY)
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn("(200 40 ", reply)
        second = mock_llm.RequestLog.bodies[1]["messages"]
        self.assertEqual(len(second), 3)
        self.assertEqual(second[1]["content"][0]["type"], "thinking")
        self.assertIn("not legal", second[2]["content"])

    def test_refusal_becomes_error(self):
        self.start("refuse")
        self.assertIn("declined", run_helper(PLAY))

    def test_bad_key_becomes_error(self):
        self.start("401")
        self.assertIn("rejected the credential", run_helper(PLAY))

    def test_no_server_becomes_error(self):
        self.start("good")
        self.server.shutdown()
        self.server.server_close()
        self.server = None
        reply = run_helper(PLAY)
        self.assertTrue(reply.startswith("(ERROR"), reply)

    def test_no_credential_becomes_error(self):
        self.start("good")
        del os.environ["ANTHROPIC_API_KEY"]
        reply = run_helper(PLAY)
        self.assertTrue(reply.startswith("(ERROR"), reply)

    def test_bearer_token_reaches_a_custom_endpoint(self):
        self.start("good")
        del os.environ["ANTHROPIC_API_KEY"]
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "gateway-token"
        reply = run_helper(PLAY, "--model", "any-model-the-gateway-serves")
        self.assertTrue(reply.startswith("(OK"), reply)
        headers = {k.lower(): v for k, v in mock_llm.RequestLog.headers[0].items()}
        self.assertEqual(headers["authorization"], "Bearer gateway-token")
        self.assertEqual(mock_llm.RequestLog.bodies[0]["model"], "any-model-the-gateway-serves")

    def test_check_counts_either_credential(self):
        self.start("good")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            llm_player.main(["--check"])
        self.assertIn(" T ", out.getvalue())
        del os.environ["ANTHROPIC_API_KEY"]
        os.environ["ANTHROPIC_AUTH_TOKEN"] = "gateway-token"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            llm_player.main(["--check"])
        self.assertIn(" T ", out.getvalue())
        del os.environ["ANTHROPIC_AUTH_TOKEN"]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            llm_player.main(["--check"])
        self.assertIn(" NIL ", out.getvalue())

    def test_model_without_fallbacks_uses_plain_endpoint(self):
        self.start("good")
        reply = run_helper(PLAY, "--model", "claude-haiku-5-5")
        self.assertTrue(reply.startswith("(OK"), reply)
        self.assertNotIn("fallbacks", mock_llm.RequestLog.bodies[0])


@unittest.skipUnless(importlib.util.find_spec("openai"), "the openai package is not installed")
class ThroughTheOpenAISDK(unittest.TestCase):
    """The real openai SDK and helper code, talking to the mock server."""

    VARIABLES = ("OPENAI_BASE_URL", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")

    def setUp(self):
        mock_llm.RequestLog.bodies.clear()
        mock_llm.RequestLog.headers.clear()
        self.saved = {k: os.environ.pop(k, None) for k in self.VARIABLES}
        self.server = None

    def tearDown(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        for k, v in self.saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v

    def start(self, behaviour, key="test-key"):
        self.server = mock_llm.serve(behaviour=behaviour)
        os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{self.server.server_address[1]}/v1"
        if key:
            os.environ["OPENAI_API_KEY"] = key

    def ask(self, req=PLAY):
        return run_helper(req, "--provider", "openai", "--model", "mock-model")

    def test_play_request_and_reply(self):
        self.start("good")
        reply = self.ask()
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn("(100 20 ", reply)
        body = mock_llm.RequestLog.bodies[0]
        self.assertEqual(body["model"], "mock-model")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])
        self.assertEqual(body["response_format"]["json_schema"]["schema"], llm_player.PLAY_SCHEMA)
        self.assertTrue(body["response_format"]["json_schema"]["strict"])
        for field in ("max_tokens", "max_completion_tokens", "reasoning_effort", "temperature"):
            self.assertNotIn(field, body)
        headers = {k.lower(): v for k, v in mock_llm.RequestLog.headers[0].items()}
        self.assertEqual(headers["authorization"], "Bearer test-key")

    def test_pass_uses_three_card_schema(self):
        self.start("good")
        self.assertTrue(self.ask(PASS).startswith("(OK ((C . 2) (C . 3) (D . 4))"))
        schema = mock_llm.RequestLog.bodies[0]["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema, llm_player.PASS_SCHEMA)

    def test_illegal_answer_is_retried(self):
        self.start("illegal_once")
        reply = self.ask()
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn("(200 40 ", reply)
        second = mock_llm.RequestLog.bodies[1]["messages"]
        self.assertEqual([m["role"] for m in second], ["system", "user", "assistant", "user"])
        self.assertIn("not legal", second[3]["content"])

    def test_server_without_structured_output(self):
        self.start("no_schema")
        reply = self.ask()
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn("response_format", mock_llm.RequestLog.bodies[0])
        self.assertNotIn("response_format", mock_llm.RequestLog.bodies[1])
        self.assertIn("JSON object", mock_llm.RequestLog.bodies[1]["messages"][0]["content"])

    def test_json_wrapped_in_reasoning_and_a_fence_with_no_usage(self):
        self.start("prose")
        reply = self.ask()
        self.assertTrue(reply.startswith("(OK ((D . 9))"), reply)
        self.assertIn("(0 0 ", reply)

    def test_no_json_at_all_becomes_error_after_a_retry(self):
        self.start("garbage")
        self.assertIn("unusable answer", self.ask())
        self.assertEqual(len(mock_llm.RequestLog.bodies), 2)

    def test_refusal_becomes_error(self):
        self.start("refuse")
        self.assertIn("declined", self.ask())

    def test_bad_key_becomes_error(self):
        self.start("401")
        self.assertIn("rejected the credential", self.ask())

    def test_local_server_needs_no_key(self):
        self.start("good", key=None)
        self.assertTrue(self.ask().startswith("(OK"))

    def test_no_key_and_no_server_becomes_error(self):
        reply = self.ask()
        self.assertTrue(reply.startswith("(ERROR"), reply)
        self.assertIn("OPENAI_API_KEY", reply)

    def test_missing_package_becomes_error(self):
        self.start("good")
        with mock.patch.dict(sys.modules, {"openai": None}):
            self.assertIn("pip install openai", self.ask())

    def test_check_looks_at_this_provider(self):
        os.environ["ANTHROPIC_API_KEY"] = "not-for-openai"
        def check():
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                llm_player.main(["--provider", "openai", "--model", "mock-model", "--check"])
            return out.getvalue()
        self.assertIn(" NIL ", check())
        os.environ["OPENAI_API_KEY"] = "a-key"
        self.assertIn(" T ", check())


class ReadAnswer(unittest.TestCase):
    def test_lower_case_card_is_accepted(self):
        cards, _plan, _remark, problem = llm_player.read_answer(PLAY, '{"plan": "p", "remark": "r", "card": "dk"}')
        self.assertEqual(cards, ["DK"])
        self.assertIsNone(problem)

    def test_a_card_that_is_not_text_is_a_problem(self):
        self.assertIsNotNone(llm_player.read_answer(PLAY, '{"card": ["DK"]}')[3])
        self.assertIsNotNone(llm_player.read_answer(PASS, '{"card1": 2, "card2": 3, "card3": 4}')[3])


if __name__ == "__main__":
    unittest.main()
