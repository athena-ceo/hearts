#!/usr/bin/env python3
"""A local stand-in for POST /v1/messages and /v1/chat/completions, so the LLM player's real SDK
paths can be tested with no key and no spending.  It reads the state the helper sent and answers
like the model would.

    python3 tests/mock_llm.py PORT [BEHAVIOUR]

Behaviours: good (first legal card), illegal_once (illegal, then good on the retry), refuse, 401.
For Chat Completions also: no_schema (rejects response_format), prose (reasoning and a code fence
around the JSON, and no usage), garbage (never any JSON).
Every request body is appended to RequestLog.bodies when used from Python.
"""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class RequestLog:
    bodies = []
    headers = []


def answer_for(state, illegal=False):
    answer = {"plan": "Mock plan: duck everything.", "remark": "The mock takes the first choice."}
    if state["decision"] == "pass":
        hand = state["your_hand"]
        answer.update(card1=hand[0], card2=hand[1], card3=hand[0] if illegal else hand[2])
    else:
        legal = state["legal_choices"]
        outside = [c for c in ("C2", "C3", "D2", "D3") if c not in legal]
        answer["card"] = outside[0] if illegal else legal[0]
    return answer


def make_handler(behaviour):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["content-length"])))
            RequestLog.bodies.append(body)
            RequestLog.headers.append(dict(self.headers))
            if behaviour == "401":
                self.reply(401, {"type": "error", "error": {"type": "authentication_error",
                                                            "message": "invalid x-api-key"}})
                return
            if self.path.endswith("/chat/completions"):
                self.chat_completion(body)
                return
            first_turn = len(body["messages"]) == 1
            state = json.loads(body["messages"][0]["content"])
            stop_reason = "refusal" if behaviour == "refuse" else "end_turn"
            content = [{"type": "thinking", "thinking": "", "signature": "mock"}]
            if behaviour != "refuse":
                answer = answer_for(state, illegal=behaviour == "illegal_once" and first_turn)
                content.append({"type": "text", "text": json.dumps(answer)})
            self.reply(200, {"id": "msg_mock", "type": "message", "role": "assistant",
                             "model": body["model"], "content": content,
                             "stop_reason": stop_reason, "stop_sequence": None,
                             "usage": {"input_tokens": 100, "output_tokens": 20}})

        def chat_completion(self, body):
            if behaviour == "no_schema" and "response_format" in body:
                self.reply(400, {"error": {"message": "response_format is not supported"}})
                return
            first_turn = len(body["messages"]) == 2
            state = json.loads(body["messages"][1]["content"])
            answer = json.dumps(answer_for(state, illegal=behaviour == "illegal_once" and first_turn))
            if behaviour == "prose":
                answer = f"<think>Which {{card}} though?</think>Here you go:\n```json\n{answer}\n```"
            elif behaviour == "garbage":
                answer = "I would rather not say."
            message = {"role": "assistant", "content": answer, "refusal": None}
            if behaviour == "refuse":
                message.update(content=None, refusal="I can't help with that.")
            reply = {"id": "chatcmpl-mock", "object": "chat.completion", "created": 0,
                     "model": body["model"],
                     "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]}
            if behaviour != "prose":
                reply["usage"] = {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
            self.reply(200, reply)

        def reply(self, status, payload):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass
    return Handler


def serve(port=0, behaviour="good"):
    """Start in a background thread; returns the server (server.server_address[1] is the port)."""
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(behaviour))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])),
                        make_handler(sys.argv[2] if len(sys.argv) > 2 else "good")).serve_forever()
