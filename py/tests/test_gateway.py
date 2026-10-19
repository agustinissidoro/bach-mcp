"""Tests for the gateway: Ollama request translation and the llama-server proxy."""

import json
import os
import socket
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.config import BachConfig  # noqa: E402
from bach_mcp.gateway import build_ollama_request, create_llama_gateway_app, to_ollama_messages  # noqa: E402


def _config(reasoning: str = "auto") -> BachConfig:
    config = BachConfig()
    config.model.backend = "ollama"
    config.model.ollama_model = "some-model"
    config.generation.reasoning = reasoning
    return config


class MessageTests(unittest.TestCase):
    def test_tool_round_trip(self):
        messages = to_ollama_messages([
            {"role": "user", "content": [{"type": "text", "text": "hi"},
                                         {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}]},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "write_score", "arguments": "{\"add\": true}"}}]},
            {"role": "tool", "tool_call_id": "c1", "content": "OK"},
        ])
        self.assertEqual(messages[0], {"role": "user", "content": "hi", "images": ["AAAA"]})
        self.assertEqual(messages[1]["tool_calls"][0]["function"], {"name": "write_score", "arguments": {"add": True}})
        self.assertEqual(messages[2], {"role": "tool", "content": "OK", "tool_name": "write_score"})


class RequestTests(unittest.TestCase):
    def test_options_come_from_config_unless_the_chat_sets_them(self):
        request = build_ollama_request({"messages": [], "temperature": 0.9, "max_tokens": -1}, _config())
        self.assertEqual(request["options"]["num_ctx"], 16384)
        self.assertEqual(request["options"]["temperature"], 0.9)
        self.assertNotIn("num_predict", request["options"])
        self.assertNotIn("think", request)

    def test_thinking_follows_the_chat_switch_and_the_configured_level(self):
        on = {"messages": [], "chat_template_kwargs": {"enable_thinking": True}}
        off = {"messages": [], "chat_template_kwargs": {"enable_thinking": False}}
        self.assertEqual(build_ollama_request(on, _config("low"))["think"], "low")
        self.assertIs(build_ollama_request(on, _config("auto"))["think"], True)
        self.assertIs(build_ollama_request(off, _config("low"))["think"], False)
        self.assertIs(build_ollama_request({"messages": []}, _config("off"))["think"], False)


class LlamaProxyTests(unittest.TestCase):
    """The proxy against a fake llama-server running on a local port."""

    @classmethod
    def setUpClass(cls):
        import uvicorn
        from starlette.applications import Starlette
        from starlette.responses import JSONResponse, StreamingResponse
        from starlette.routing import Route

        cls.received = []

        async def chat(request):
            cls.received.append(await request.json())

            async def sse():
                for word in ("Hel", "lo"):
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': word}}]})}\n\n".encode()
                yield b"data: [DONE]\n\n"
            return StreamingResponse(sse(), media_type="text/event-stream")

        async def props(request):
            return JSONResponse({"model_alias": "bach", "query": request.url.query})

        upstream = Starlette(routes=[Route("/v1/chat/completions", chat, methods=["POST"]), Route("/props", props)])
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        cls.server = uvicorn.Server(uvicorn.Config(upstream, host="127.0.0.1", port=port, log_level="error"))
        threading.Thread(target=cls.server.run, daemon=True).start()
        while not cls.server.started:
            time.sleep(0.01)
        cls.origin = f"http://127.0.0.1:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True

    def client(self, docs=True):
        from starlette.testclient import TestClient
        config = BachConfig()
        config.chat.docs = docs
        return TestClient(create_llama_gateway_app(config, self.origin))

    def test_other_requests_pass_through(self):
        response = self.client().get("/props?a=1")
        self.assertEqual(response.json(), {"model_alias": "bach", "query": "a=1"})

    def test_chat_gets_the_docs_and_streams_back(self):
        body = {"stream": True, "messages": [{"role": "user", "content": "a piece for oboe"}]}
        response = self.client().post("/v1/chat/completions", json=body)
        self.assertIn("Hel", response.text)
        self.assertTrue(response.text.rstrip().endswith("data: [DONE]"))
        sent = self.received[-1]["messages"][0]["content"]
        self.assertTrue(sent.startswith("a piece for oboe\n\nReference for this request"))
        self.assertIn("# Oboe", sent)
        self.assertIn("# Woodwinds", sent)

    def test_docs_off_forwards_the_request_unchanged(self):
        body = {"messages": [{"role": "user", "content": "a piece for oboe"}]}
        self.client(docs=False).post("/v1/chat/completions", json=body)
        self.assertEqual(self.received[-1], body)


if __name__ == "__main__":
    unittest.main()
