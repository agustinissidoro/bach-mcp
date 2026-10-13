"""Tests for the request translation of the Ollama gateway."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.config import BachConfig  # noqa: E402
from bach_mcp.gateway import build_ollama_request, to_ollama_messages  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
