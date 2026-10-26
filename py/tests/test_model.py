"""The local model: how each backend is started, and how a streamed reply is read."""

import os
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from bach_mcp.config import Config, GenerationConfig  # noqa: E402
from bach_mcp.model.backends import command  # noqa: E402
from bach_mcp.model.client import ModelClient, read_stream  # noqa: E402
from fakemodel import chunk, sse_lines, text_reply, tool_reply  # noqa: E402


def events(chunks):
    out = list(read_stream(sse_lines(chunks)))
    return out[:-1], out[-1][1]


class BackendTests(unittest.TestCase):
    def test_mlx_runs_mlx_lm_in_this_python(self):
        config = Config()
        config.model.model = "mlx-community/some-model-4bit"
        config.model.extra_args = ["--prompt-cache-size", "4"]
        args = command(config, 5555)
        self.assertEqual(args[:5], [sys.executable, "-m", "mlx_lm", "server", "--model"])
        self.assertIn("mlx-community/some-model-4bit", args)
        self.assertEqual(args[args.index("--port") + 1], "5555")
        self.assertEqual(args[args.index("--max-tokens") + 1], str(config.generation.max_tokens))
        self.assertEqual(args[-2:], ["--prompt-cache-size", "4"])

    def test_gguf_runs_llama_server_on_a_file_or_a_repo(self):  # the runtime follows from the name
        config = Config()
        config.model.model = "~/models/qwen.gguf"
        args = command(config, 5555)
        self.assertEqual(args[:3], ["llama-server", "--model", os.path.expanduser("~/models/qwen.gguf")])
        for flag in ("--jinja", "--no-webui"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("--ctx-size") + 1], str(config.model.context_size))
        config.model.model = "user/qwen-GGUF:Q4_K_M"
        self.assertEqual(command(config, 5555)[1:3], ["--hf-repo", "user/qwen-GGUF:Q4_K_M"])


class StreamTests(unittest.TestCase):
    def test_text_and_thinking_arrive_in_pieces(self):
        seen, reply = events(text_reply("three short notes", thinking="a plan"))
        self.assertEqual(seen[0], ("thinking", "a plan"))
        self.assertEqual("".join(v for k, v in seen if k == "text"), "three short notes")
        self.assertEqual((reply.text, reply.thinking, reply.finish), ("three short notes", "a plan", "stop"))
        self.assertEqual(reply.usage["completion_tokens"], 7)

    def test_mlx_names_its_reasoning_differently(self):
        _, reply = events([chunk({"reasoning": "hmm"}), chunk({"content": "ok"}, finish="stop")])
        self.assertEqual((reply.thinking, reply.text), ("hmm", "ok"))

    def test_a_tool_call_is_put_together_from_its_pieces(self):
        seen, reply = events(tool_reply("p2mc", {"pitches": ["C4", "Eb4"]}, text="First the pitches."))
        self.assertEqual(reply.finish, "tool_calls")
        self.assertEqual(len(reply.tool_calls), 1)
        call = reply.tool_calls[0]
        self.assertEqual((call.id, call.name, call.arguments, call.error), ("call_1", "p2mc", {"pitches": ["C4", "Eb4"]}, ""))
        progress = [v for k, v in seen if k == "calling"]
        self.assertEqual(progress[-1]["name"], "p2mc")
        self.assertGreater(progress[-1]["chars"], progress[0]["chars"])

    def test_cut_off_arguments_are_reported_not_guessed(self):
        _, reply = events(tool_reply("write_score", '{"score": {"voices": [', call_id="c9")[:-1] + [chunk(finish="length")])
        self.assertEqual(reply.finish, "length")
        self.assertEqual(reply.tool_calls[0].arguments, {})
        self.assertIn("not valid JSON", reply.tool_calls[0].error)

    def test_a_server_error_is_raised(self):
        with self.assertRaises(RuntimeError) as ctx:
            list(read_stream(['data: {"error": {"message": "model not loaded"}}']))
        self.assertIn("model not loaded", str(ctx.exception))


class RequestTests(unittest.TestCase):
    def test_every_request_carries_the_generation_settings(self):
        g = GenerationConfig(max_tokens=900, temperature=0.5, top_p=0.7, top_k=10, presence_penalty=1.0)
        body = ModelClient("http://x/v1", g).request([{"role": "user", "content": "hi"}], [])
        self.assertEqual({k: body[k] for k in ("max_tokens", "temperature", "top_p", "top_k", "presence_penalty")},
                         {"max_tokens": 900, "temperature": 0.5, "top_p": 0.7, "top_k": 10, "presence_penalty": 1.0})
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertTrue(body["stream"])
        self.assertNotIn("tools", body)
        self.assertNotIn("model", body)

    def test_reasoning_on_and_a_model_name(self):
        body = ModelClient("http://x/v1", GenerationConfig(reasoning="on"), model="bach").request([], [{"t": 1}], max_tokens=50)
        self.assertEqual((body["chat_template_kwargs"], body["model"], body["tools"], body["max_tokens"]),
                         ({"enable_thinking": True}, "bach", [{"t": 1}], 50))


class LiveStreamTests(unittest.TestCase):
    """The client against a real HTTP server: streaming, and Stop."""

    @classmethod
    def setUpClass(cls):
        import uvicorn
        from starlette.applications import Starlette
        from starlette.responses import StreamingResponse
        from starlette.routing import Route
        from bach_mcp.model.backends import free_port

        async def completions(request):
            body = await request.json()
            slow = body["messages"][-1]["content"] == "slow"

            async def stream():
                import asyncio
                for line in sse_lines(text_reply("one two three")):
                    yield (line + "\n\n").encode()
                    if slow:
                        await asyncio.sleep(0.5)
            return StreamingResponse(stream(), media_type="text/event-stream")

        cls.port = free_port()
        cls.server = uvicorn.Server(uvicorn.Config(Starlette(routes=[Route("/v1/chat/completions", completions, methods=["POST"])]),
                                                   port=cls.port, log_level="error"))
        threading.Thread(target=cls.server.run, daemon=True).start()
        while not cls.server.started:
            time.sleep(0.02)

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True

    def test_a_reply_streams_from_the_server(self):
        client = ModelClient(f"http://127.0.0.1:{self.port}/v1", GenerationConfig())
        out = list(client.stream([{"role": "user", "content": "hi"}], []))
        self.assertEqual(out[-1][1].text, "one two three")

    def test_cancel_stops_a_reply_from_another_thread(self):
        client = ModelClient(f"http://127.0.0.1:{self.port}/v1", GenerationConfig())
        threading.Timer(0.3, client.cancel).start()
        started = time.time()
        with self.assertRaises(Exception):
            list(client.stream([{"role": "user", "content": "slow"}], []))
        self.assertLess(time.time() - started, 2.0)


if __name__ == "__main__":
    unittest.main()
