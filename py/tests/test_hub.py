"""The hub: the line protocol from Max, the page and the terminal; the playground, the map of
instances, the active instance and one conversation per instance; and the web app around it.
Run: python -m unittest discover -s py/tests"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from bach_mcp.bridge.protocol import line, words  # noqa: E402
from bach_mcp.chat.engine import Conversation  # noqa: E402
from bach_mcp.chat.hub import Hub  # noqa: E402
from bach_mcp.config import Config  # noqa: E402
from bach_mcp.prompt.skill import load_skill  # noqa: E402
from bach_mcp.tools.session import NoTarget, target  # noqa: E402
from bach_mcp.utilities.status import Status  # noqa: E402
from fakemodel import FakeClient, text_reply, tool_reply  # noqa: E402

RAW = load_skill(raw=True)


class FakeBridge:
    """Max: what the hub sends to it, and the hub's hand on the lines it receives."""

    def __init__(self):
        self.sent = []
        self.handler = None

    def send(self, text):
        self.sent.append(text)
        return True

    def say(self, *said):
        return self.send(line(*said))

    def on_line(self, handler):
        self.handler = handler

    def from_max(self, text):
        return self.handler(text)


class FakeTools:
    """The tools, for a conversation: read_score says which instance it was called for."""

    def __init__(self):
        self.calls = []

    def specs(self):
        return [{"type": "function", "function": {"name": n, "description": "", "parameters": {"type": "object"}}}
                for n in ("write_score", "read_score", "clear_score", "send_algorithm")]

    def call(self, name, arguments):
        self.calls.append((name, target().name))
        return f"called for {target().name}"


class HeldClient(FakeClient):
    """A model that starts answering only once `go` is set."""

    def __init__(self, go, *replies):
        super().__init__(*replies)
        self.go = go

    def stream(self, messages, tools, max_tokens=None):
        self.go.wait(3)
        yield from super().stream(messages, tools, max_tokens)


class HubTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.playground = os.path.join(self.folder, "pg")
        self.bridge = FakeBridge()
        self.status = Status(Config(), self.bridge, "run")
        self.status.set("ready", model="test-model")
        self.replies = []
        self.go = threading.Event()
        self.go.set()
        self.tools = FakeTools()
        self.clients = []
        self.hub = self.start()

    def start(self, make=True):
        hub = Hub(self.bridge, self.status, self.make if make else None)
        self.addCleanup(hub.close)
        hub.subscribe(lambda m: self.clients.append(m))
        return hub

    def make(self, kind):
        self.client = HeldClient(self.go, *self.replies)
        return Conversation(self.client, self.tools, RAW, None, 8, kind)

    def heard(self, web_only=None):
        return [m.text for m in self.clients if web_only is None or m.web_only == web_only]

    def answered(self, name, timeout=3.0):
        """Wait until the hub has said `<name> done`."""
        deadline = time.time() + timeout
        while not any(t.startswith(f"{name} done") for t in self.heard()):
            if time.time() > deadline:
                self.fail(f"{name} was never answered; heard {self.heard()}")
            time.sleep(0.01)

    def setup_patch(self):
        """What the patch sends when the server starts: the playground and the map."""
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.bridge.from_max("clear_instance_names_map")
        self.bridge.from_max("add_instance_names_map scales1 generator")
        self.bridge.from_max("add_instance_names_map notes1 writer")
        self.bridge.sent.clear()
        self.clients.clear()


class ProtocolTests(unittest.TestCase):
    def test_lines_and_words(self):
        said = line("scales1", "prompt", 'a "tight" canon, don\'t stop', 3, 2.5)
        self.assertEqual(said, 'scales1 prompt "a \\"tight\\" canon, don\'t stop" 3 2.5')
        self.assertEqual(words(said), ["scales1", "prompt", 'a "tight" canon, don\'t stop', "3", "2.5"])
        self.assertEqual(words('notes1 prompt write "three'), ["notes1", "prompt", "write", "three"], "an open quote ends the line")
        self.assertEqual(words("  a   b "), ["a", "b"])
        self.assertEqual(line(""), '""')


class MapTests(HubTest):
    def test_the_map_from_max_goes_to_the_pages_not_back(self):
        self.setup_patch()
        self.bridge.from_max("clear_instance_names_map")
        self.bridge.from_max("add_instance_names_map scales1 transformer")
        self.assertEqual(self.hub.instances, {"scales1": "transformer"})
        self.assertEqual(self.heard(), ["clear_instance_names_map", "add_instance_names_map scales1 transformer"])
        self.assertEqual(self.bridge.sent, [], "Max is not told what it said")

    def test_the_active_instance_from_the_page_goes_to_max_and_the_pages(self):
        self.setup_patch()
        self.assertTrue(self.hub.handle("set_active_instance notes1", "web"))
        self.assertEqual(self.hub.active, "notes1")
        self.assertEqual(self.bridge.sent, ["set_active_instance notes1"])
        self.assertEqual(self.heard(), ["set_active_instance notes1"])
        self.bridge.from_max("set_active_instance scales1")
        self.assertEqual((self.hub.active, self.bridge.sent[-1], self.heard()[-1]),
                         ("scales1", "set_active_instance notes1", "set_active_instance scales1"))

    def test_mistakes_are_warnings(self):
        self.setup_patch()
        self.bridge.from_max("add_instance_names_map odd mixer")
        self.bridge.from_max("set_active_instance nobody")
        self.bridge.from_max("add_instance_names_map lonely")
        self.assertEqual(self.bridge.sent, [
            'mcp_info warning "odd: unknown type mixer (one of generator, transformer, selector, writer)"',
            'mcp_info warning "set_active_instance: no instance nobody in the map"',
            'mcp_info warning "add_instance_names_map needs a name and a type"'])
        self.assertNotIn("odd", self.hub.instances)

    def test_the_playground_is_made_and_echoed(self):
        self.bridge.from_max(f"set_playground {line('Macintosh HD:' + self.playground)}")
        self.assertEqual(self.hub.playground, self.playground)
        self.assertEqual(sorted(os.listdir(self.playground)), ["algorithms", "prompts", "rolls"])
        self.assertEqual(self.heard(), [line("set_playground", self.playground)])
        with open(os.path.join(self.folder, "file"), "w") as f:
            f.write("")
        self.hub.handle(f"set_playground {line(os.path.join(self.folder, 'file'))}", "web")
        self.assertIn("is a file, not a folder", self.bridge.sent[-1])

    def test_lines_that_are_not_the_hubs_stay_with_the_bridge(self):
        self.setup_patch()
        self.assertFalse(self.bridge.from_max("scales1 algo_loaded scales1.js 12 3"))
        self.assertFalse(self.bridge.from_max("notes1 roll_written notes1.txt"))
        self.assertFalse(self.hub.handle("", "web"))

    def test_the_tools_serve_the_active_instance(self):
        with self.assertRaisesRegex(NoTarget, "no playground"):
            target()
        self.setup_patch()
        with self.assertRaisesRegex(NoTarget, "no instance is active"):
            target()
        self.hub.handle("set_active_instance scales1", "web")
        t = target()
        self.assertEqual((t.name, t.kind, t.algorithm_file), ("scales1", "generator",
                                                            os.path.join(self.playground, "algorithms", "scales1.js")))


class PromptTests(HubTest):
    def test_a_prompt_from_max_is_answered_for_its_instance(self):
        self.setup_patch()
        self.replies = [text_reply("Three notes for you.")]
        self.assertTrue(self.bridge.from_max("notes1 prompt write three notes"))
        self.answered("notes1")
        heard = self.heard()
        self.assertEqual(heard[0], 'notes1 prompt "write three notes"')
        self.assertIn('notes1 delta "Three "', heard)
        self.assertIn('notes1 answer "Three notes for you."', heard)
        self.assertTrue(heard[-1].startswith("notes1 done 7 "))
        self.assertEqual([t.split()[1] for t in self.bridge.sent], ["thinking", "answer", "done"],
                         "Max gets no echo of its own prompt, and no pieces")
        self.assertIn("You are writing for a writer", self.client.requests[0]["messages"][0]["content"])

    def test_the_tools_work_for_the_prompted_instance_not_the_active_one(self):
        self.setup_patch()
        self.hub.handle("set_active_instance notes1", "web")
        self.replies = [tool_reply("send_algorithm", {"code": "x"}), text_reply("Done.")]
        self.hub.handle('scales1 prompt "a scale"', "web")
        self.answered("scales1")
        self.assertEqual(self.tools.calls, [("send_algorithm", "scales1")])
        self.assertIn('scales1 tool send_algorithm "called for scales1"', self.bridge.sent)
        self.assertEqual(target().name, "notes1", "after the turn, the active one again")

    def test_refusals(self):
        self.hub.handle("add_instance_names_map scales1 generator", "web")
        self.hub.handle("scales1 prompt hello", "web")
        self.hub.handle("ghost prompt hello", "web")
        before = self.heard()
        self.setup_patch()
        self.hub.handle("add_instance_names_map picker selector", "web")
        self.hub.handle("picker prompt hello", "web")
        self.hub.handle("scales1 prompt", "web")
        self.status.set("loading", model="test-model")
        self.hub.handle("scales1 prompt hello", "web")
        errors = [t for t in before + self.heard() if " error " in t]
        self.assertEqual(errors, ['scales1 error "no playground: the patch sends set_playground <folder>"',
                                  'ghost error "no instance ghost in the map"',
                                  'picker error "selector instances are not built yet"',
                                  'scales1 error "the prompt is empty"',
                                  'scales1 error "the model is not ready (loading)"'])

    def test_without_a_local_model_prompts_are_refused(self):
        self.hub.close()
        self.status.set("claude")
        hub = self.start(make=False)
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.bridge.from_max("add_instance_names_map notes1 writer")
        hub.handle("notes1 prompt hello", "web")
        self.assertIn('notes1 error "no local model here: this Bach serves Claude through MCP"', self.heard())

    def test_the_conversation_is_kept_in_the_playground_and_read_again(self):
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.answered("notes1")
        path = os.path.join(self.playground, "prompts", "notes1.jsonl")
        with open(path, encoding="utf-8") as f:
            saved = [json.loads(row) for row in f]
        self.assertEqual([(m["role"], m.get("prompt")) for m in saved], [("user", "first"), ("assistant", None)])
        history = [t for t in self.hub.snapshot() if t.startswith("notes1 history")]
        self.assertEqual(json.loads(words(history[0])[2])[0]["prompt"], "first")

        self.hub.close()  # Bach starts again: the conversation goes on
        self.clients.clear()
        hub = self.start()
        self.replies = [text_reply("Two.")]
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.bridge.from_max("add_instance_names_map notes1 writer")
        hub.handle('notes1 prompt "second"', "web")
        self.answered("notes1")
        sent = [m["content"] for m in self.client.requests[0]["messages"][1:]]
        self.assertEqual(sent, ["first", "One.", "second"])

    def test_new_keeps_the_old_conversation_aside(self):
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.answered("notes1")
        self.hub.handle("notes1 new", "web")
        self.assertEqual(self.heard()[-1], "notes1 new")
        files = os.listdir(os.path.join(self.playground, "prompts"))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("notes1-"))
        self.assertEqual([t for t in self.hub.snapshot() if " history " in t], [])

    def test_one_answer_at_a_time_and_a_waiting_prompt_can_be_stopped(self):
        self.setup_patch()
        self.go.clear()  # scales1's answer is held
        self.replies = [text_reply("Held.")]
        self.hub.handle('scales1 prompt "first"', "web")
        self.hub.handle('notes1 prompt "wait"', "web")
        self.assertEqual(self.heard()[-1], "notes1 queued")
        self.hub.handle("notes1 stop", "web")
        self.assertEqual(self.heard()[-1], "notes1 stopped")
        self.go.set()
        self.answered("scales1")
        self.assertFalse(any(t.startswith("notes1 thinking") for t in self.heard()), "a stopped prompt is never answered")

    def test_an_answer_can_be_stopped(self):
        self.setup_patch()
        self.go.clear()
        self.replies = [text_reply("Never shown.")]
        self.hub.handle('scales1 prompt "long"', "web")
        deadline = time.time() + 3
        while "scales1 thinking" not in self.heard() and time.time() < deadline:
            time.sleep(0.01)
        self.hub.handle("scales1 stop", "web")
        self.go.set()
        deadline = time.time() + 3
        while "scales1 stopped" not in self.heard() and time.time() < deadline:
            time.sleep(0.01)
        self.assertIn("scales1 stopped", self.heard())
        self.assertEqual(self.client.cancelled, 1)
        self.assertNotIn('scales1 answer "Never shown."', self.heard())


class WebTests(HubTest):
    def app(self):
        from starlette.testclient import TestClient
        from bach_mcp.chat.web import create_app
        return TestClient(create_app(self.hub, self.status))

    def test_the_page_its_state_and_a_line(self):
        client = self.app()
        self.assertIn("<title>Bach</title>", client.get("/").text)
        self.assertEqual(client.get("/api/state").json()["model"], "test-model")
        self.setup_patch()
        response = client.post("/api/line", content="set_active_instance scales1")
        self.assertEqual(response.json(), {"ok": True})
        self.assertEqual(self.bridge.sent, ["set_active_instance scales1"])
        bad = client.post("/api/line", content="dance now")
        self.assertEqual((bad.status_code, bad.json()["error"]), (400, "unknown command: dance now"))

    def test_an_event_holds_a_line_with_newlines(self):
        from bach_mcp.chat.web import event
        self.assertEqual(event('a answer "one\ntwo"'), b'data: a answer "one\ndata: two"\n\n')

    def test_a_page_first_gets_the_present(self):
        self.setup_patch()
        self.hub.handle("set_active_instance notes1", "web")
        self.assertEqual(self.hub.snapshot(), [
            'state ready test-model ""',
            line("set_playground", self.playground),
            "clear_instance_names_map",
            "add_instance_names_map scales1 generator",
            "add_instance_names_map notes1 writer",
            "set_active_instance notes1"])

    def test_the_state_reaches_the_pages(self):
        self.status.set("loading", model="other")
        self.assertEqual(self.heard(web_only=True)[-1], 'state loading other ""')
        self.assertEqual(self.bridge.sent, [], "Max asks for the state itself (bach status)")


if __name__ == "__main__":
    unittest.main()
