"""The hub: the line protocol from Max, the page and the terminal; the playground, the map of
instances, the active instance and one conversation per instance; and the web app around it.
Run: python -m unittest discover -s py/tests"""

import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
import unittest.mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from bach_mcp.bridge.protocol import line, words  # noqa: E402
from bach_mcp.chat.engine import Conversation  # noqa: E402
from bach_mcp.chat.hub import Hub  # noqa: E402
from bach_mcp.config import Config  # noqa: E402
from bach_mcp.prompt.docs import DocLibrary  # noqa: E402
from bach_mcp.prompt.skill import SKILL_PATH, load_skill  # noqa: E402
from bach_mcp.tools.instance_tools import register_instance_tools  # noqa: E402
from bach_mcp.bridge.max import OfflineBridge  # noqa: E402
from bach_mcp.tools.registry import create_tools, threaded  # noqa: E402
from bach_mcp.tools.session import NoTarget, calling_directly, direct, target  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402
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

    def make(self, instance_type):
        self.client = HeldClient(self.go, *self.replies)
        docs = DocLibrary() if getattr(self, "with_docs", False) else None
        return Conversation(self.client, self.tools, RAW, docs, 8, instance_type)

    def heard(self, web_only=None):
        """What the pages heard, without the stage reports (stages() has them)."""
        return [m.text for m in self.clients if (web_only is None or m.web_only == web_only)
                and not m.text.startswith("server prompt ")]

    def stages(self, name):
        """What Max was told about name's prompt: server prompt <name> <what...>, without the times."""
        out = []
        for text in self.bridge.sent:
            said = words(text)
            if said[:3] == ["server", "prompt", name] and said[3] != "skills_size":  # a size, not a stage
                out.append(" ".join(said[3:5] if said[3] == "done" else said[3:]))
        return out

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
        self.bridge.from_max("add_instance_names_map notes1 score")
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
        self.assertEqual(self.heard(), ["clear_instance_names_map", "add_instance_names_map scales1 transformer",
                                        "scales1 history []"])
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
            'server warning "odd: unknown type mixer (one of generator, transformer, selector, score, synth, fx, buffer)"',
            'server warning "set_active_instance: no instance nobody in the map"',
            'server warning "add_instance_names_map needs a name and a type"'])
        self.assertNotIn("odd", self.hub.instances)

    def test_an_instance_cannot_be_named_like_a_command(self):
        self.setup_patch()
        self.bridge.from_max("add_instance_names_map server generator")
        self.bridge.from_max("set_active_instance instances score")
        self.bridge.from_max("instances scales1 generator bach score")
        self.assertEqual([t for t in self.bridge.sent if "cannot be named" in t], [
            'server warning "an instance cannot be named server: rename it"',
            'server warning "an instance cannot be named instances: rename it"',
            'server warning "an instance cannot be named bach: rename it"'])
        self.assertEqual(self.hub.instances, {"scales1": "generator"})

    def test_the_playground_is_made_and_echoed(self):
        self.bridge.from_max(f"set_playground {line('Macintosh HD:' + self.playground)}")
        self.assertEqual(self.hub.playground, self.playground)
        self.assertEqual(sorted(os.listdir(self.playground)), ["algorithms", "gen", "processes", "prompts", "scores", "skills"])
        self.assertEqual(sorted(os.listdir(os.path.join(self.playground, "skills"))), ["core-algorithmic.md", "core-electronic.md", "profiles", "quantizer.md"])
        self.assertEqual(self.heard(), [line("set_playground", self.playground)])
        with open(os.path.join(self.folder, "file"), "w") as f:
            f.write("")
        self.hub.handle(f"set_playground {line(os.path.join(self.folder, 'file'))}", "web")
        self.assertIn("is a file, not a folder", self.bridge.sent[-1])

    def test_core_skill_and_profile_are_made_once_and_then_the_users(self):
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        core = os.path.join(self.playground, "skills", "core-algorithmic.md")
        profile = os.path.join(self.playground, "skills", "profiles", "minimal-algorithmic-composer.json")
        with open(core, encoding="utf-8") as f, open(SKILL_PATH, encoding="utf-8") as shipped:
            self.assertEqual(f.read(), shipped.read())
        with open(profile, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"skills": ["core-algorithmic"]})
        for path in (core, profile):
            with open(path, "w", encoding="utf-8") as f:
                f.write("mine")
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        for path in (core, profile):
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "mine")

    def test_the_profile_made_with_the_playground_is_the_built_in_skill(self):
        self.setup_patch()
        self.bridge.from_max("set_profile minimal-algorithmic-composer")
        self.assertEqual(self.bridge.sent[-2], "server skills core-algorithmic")
        self.assertEqual(self.ask("scales1").system_prompt(), Conversation(
            None, self.tools, load_skill(raw=True), None, 8, "generator").system_prompt())

    def write_skill(self, name, text):
        with open(os.path.join(self.playground, "skills", name + ".md"), "w", encoding="utf-8") as f:
            f.write(text)

    def test_set_profile_and_set_skills_build_the_skill(self):
        self.setup_patch()
        with open(os.path.join(self.playground, "skills", "profiles", "electro.json"), "w") as f:
            json.dump({"skills": ["core-algorithmic"]}, f)
        self.write_skill("analysis", "ANALYSE FIRST.")
        self.bridge.from_max("set_profile electro")
        self.bridge.from_max("set_skills analysis")
        said = [words(t) for t in self.bridge.sent]
        self.assertEqual(said[-2], ["server", "skills", "core-algorithmic", "analysis"])
        self.assertEqual(said[-1][:3], ["server", "skills", "length"])
        self.assertGreater(int(said[-1][3]), 1000)
        self.bridge.sent.clear()
        self.bridge.from_max("get_skills")
        self.assertEqual([words(t)[:3] for t in self.bridge.sent],
                         [["server", "skills", "core-algorithmic"], ["server", "skills", "length"]])
        self.assertIn("set_profile electro", self.heard())
        self.assertTrue(os.path.exists(os.path.join(self.playground, "skills", ".compiled.md")))
        self.assertEqual(self.hub.snapshot()[2:4], ["set_profile electro", "set_skills analysis"])

        self.replies = [text_reply("Done.")]
        self.bridge.from_max("scales1 prompt hello")
        self.answered("scales1")
        conversation = self.hub._conversations["scales1"]
        self.assertIn("ANALYSE FIRST.", conversation.system_prompt())

        # an edited skill reaches the next conversation, not the one going on
        self.write_skill("analysis", "LISTEN FIRST.")
        self.assertIn("ANALYSE FIRST.", conversation.system_prompt())
        self.bridge.from_max("scales1 new")
        self.clients.clear()
        self.replies = [text_reply("Done.")]
        self.bridge.from_max("scales1 prompt hello")
        self.answered("scales1")
        self.assertIn("LISTEN FIRST.", self.hub._conversations["scales1"].system_prompt())

    def test_skill_problems_are_warnings(self):
        self.bridge.from_max("set_skills core-algorithmic")
        self.assertIn("no playground yet", self.bridge.sent[-3])
        self.assertEqual(self.bridge.sent[-2:], ["server skills", "server skills length 0"])
        self.setup_patch()  # the playground comes: the skill is built
        self.bridge.from_max("set_profile nope")
        self.assertIn("no profile nope", self.bridge.sent[-3])
        self.assertEqual(self.bridge.sent[-2], "server skills core-algorithmic")  # the last one built
        self.bridge.from_max("set_skills core-algorithmic")  # the profile is still chosen, and still missing
        self.assertIn("no profile nope", self.bridge.sent[-3])
        self.bridge.from_max("set_profile")
        self.assertEqual(self.bridge.sent[-2], "server skills core-algorithmic")
        self.write_skill("gone", "GONE SKILL")
        self.bridge.from_max("set_skills core-algorithmic gone")
        os.remove(os.path.join(self.playground, "skills", "gone.md"))
        self.replies = [text_reply("Done.")]
        self.bridge.from_max("scales1 prompt hello")
        self.answered("scales1")
        self.assertTrue(any("keep the last skill built" in t for t in self.bridge.sent))
        self.assertIn("GONE SKILL", self.hub._conversations["scales1"].skill)
        self.bridge.from_max("set_skills")
        self.assertIn("no profile and no skills", self.bridge.sent[-3])
        self.assertEqual(self.bridge.sent[-2:], ["server skills", "server skills length 0"])

    def ask(self, name):
        self.clients.clear()
        self.replies = [text_reply("Done.")]
        if name in self.hub._conversations:  # a conversation going on: its own client answers
            self.hub._conversations[name].client.replies.append(text_reply("Done."))
        self.bridge.from_max(f"{name} prompt hello")
        self.answered(name)
        return self.hub._conversations[name]

    def saved_rows(self, name):
        with open(os.path.join(self.playground, "prompts", name + ".jsonl"), encoding="utf-8") as f:
            return [json.loads(row) for row in f]

    def test_an_instance_overrides_the_shared_skills(self):
        self.setup_patch()
        self.write_skill("analysis", "ANALYSE FIRST.")
        self.bridge.from_max("set_skills core-algorithmic")
        self.bridge.from_max("scales1 set_skills analysis")
        self.assertEqual(self.bridge.sent[-2:][0], "scales1 skills analysis")
        self.assertIn("scales1 set_skills analysis", self.heard())
        self.assertIn("ANALYSE FIRST.", self.ask("scales1").system_prompt())
        self.assertNotIn("## Method", self.hub._conversations["scales1"].system_prompt())  # no core: replaced
        self.assertNotIn("ANALYSE FIRST.", self.ask("notes1").system_prompt())
        compiled = os.path.join(self.playground, "skills", ".compiled", "scales1.md")
        self.assertTrue(os.path.exists(compiled))
        self.assertIn("scales1 set_skills analysis", self.hub.snapshot())

        self.bridge.from_max("scales1 get_skills")
        self.assertEqual(words(self.bridge.sent[-2]), ["scales1", "skills", "analysis"])
        self.bridge.from_max("scales1 set_skills")  # nothing of its own: back to the shared skills
        self.assertEqual(words(self.bridge.sent[-2]), ["scales1", "skills", "core-algorithmic"])
        self.assertFalse(os.path.exists(os.path.dirname(compiled)))

    def test_a_changed_skill_starts_a_clean_conversation(self):
        self.setup_patch()
        self.write_skill("analysis", "ANALYSE FIRST.")
        self.write_skill("listen", "LISTEN FIRST.")
        self.bridge.from_max("set_skills core-algorithmic")
        self.ask("scales1")
        self.ask("notes1")
        self.bridge.from_max("scales1 set_skills core-algorithmic")  # the same as it reads: nothing changes
        self.ask("scales1")
        self.assertEqual(len(self.saved_rows("scales1")), 4)
        self.assertNotIn("scales1 new", self.bridge.sent)

        self.bridge.from_max("scales1 set_skills core-algorithmic analysis")
        conversation = self.ask("scales1")
        self.assertIn("scales1 new", self.bridge.sent)
        self.assertEqual(len(conversation.history), 2)
        self.assertEqual(len(self.saved_rows("scales1")), 2)
        self.assertIn("ANALYSE FIRST.", conversation.system_prompt())
        self.assertEqual(sorted(os.listdir(os.path.join(self.playground, "prompts"))), ["notes1.jsonl", "scales1.jsonl"])

        # the shared skills change: only who reads them starts again
        self.bridge.sent.clear()
        self.bridge.from_max("set_skills core-algorithmic listen")
        self.assertIn("LISTEN FIRST.", self.ask("notes1").system_prompt())
        self.assertIn("notes1 new", self.bridge.sent)
        self.assertEqual(len(self.ask("scales1").history), 4)
        self.assertNotIn("scales1 new", self.bridge.sent)

    def test_remove_forgets_the_instance_and_sets_its_conversation_aside(self):
        self.setup_patch()
        self.write_skill("analysis", "ANALYSE FIRST.")
        self.bridge.from_max("set_skills core-algorithmic")
        self.bridge.from_max("scales1 set_skills analysis")
        self.ask("scales1")
        self.bridge.from_max("scales1 remove")
        self.assertNotIn("scales1", self.hub._conversations)
        self.assertNotIn("scales1", self.hub.own)
        self.assertNotIn("scales1 remove", self.bridge.sent)  # Max sent it: only the pages hear it
        self.assertIn("scales1 remove", self.heard())
        self.assertIn("scales1 history []", self.heard())
        self.assertNotIn("scales1 set_skills analysis", self.hub.snapshot())
        prompts = os.path.join(self.playground, "prompts")
        self.assertFalse(os.path.exists(os.path.join(prompts, "scales1.jsonl")))
        self.assertTrue([f for f in os.listdir(prompts) if f.startswith("scales1-")])  # kept beside it
        self.assertTrue(os.path.exists(os.path.join(self.playground, "skills", ".compiled", "scales1.md")))
        self.bridge.from_max("scales1 get_skills")
        self.assertEqual(words(self.bridge.sent[-2]), ["scales1", "skills", "core-algorithmic"])  # the shared ones
        conversation = self.ask("scales1")  # prompted again: a new conversation, nothing remembered
        self.assertEqual(len(conversation.history), 2)
        self.assertEqual(conversation.session, "")
        self.assertNotIn("ANALYSE FIRST.", conversation.system_prompt())

    def test_remove_stops_what_is_waiting(self):
        self.setup_patch()
        self.go.clear()  # the model holds its answer
        self.replies = [text_reply("One."), text_reply("Two.")]
        self.bridge.from_max("notes1 prompt first")
        self.bridge.from_max("scales1 prompt second")
        self.bridge.from_max("scales1 remove")
        self.assertIn("scales1 stopped", self.heard())
        self.go.set()
        self.answered("notes1")
        self.assertNotIn("scales1", self.hub._conversations)

    def test_remove_while_answered_saves_nothing(self):
        self.setup_patch()
        self.go.clear()  # the model holds its answer
        self.replies = [text_reply("One."), text_reply("Two.")]
        self.bridge.from_max("scales1 prompt first")
        deadline = time.time() + 3
        while "scales1 thinking" not in self.heard() and time.time() < deadline:
            time.sleep(0.01)
        self.bridge.from_max("scales1 remove")
        self.go.set()
        deadline = time.time() + 3
        while "scales1 stopped" not in self.heard() and time.time() < deadline:
            time.sleep(0.01)
        while self.hub._answering and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(os.listdir(os.path.join(self.playground, "prompts")) if os.path.isdir(
            os.path.join(self.playground, "prompts")) else [], [])
        self.assertEqual(len(self.ask("scales1").history), 2)  # the next prompt: a new conversation

    def test_lines_that_are_not_the_hubs_stay_with_the_bridge(self):
        self.setup_patch()
        self.assertFalse(self.bridge.from_max("scales1 algo_loaded scales1.js 12 3"))
        self.assertFalse(self.bridge.from_max("notes1 roll_written notes1.txt"))
        self.assertFalse(self.hub.handle("", "web"))

    def test_the_tools_serve_the_active_instance(self):
        with self.assertRaisesRegex(NoTarget, "no playground"):
            target()
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        with self.assertRaisesRegex(NoTarget, "no instance is active"):
            target()
        self.bridge.from_max("add_instance_names_map notes1 score")
        self.assertEqual(target().name, "notes1", "the first instance is the active one")
        self.bridge.from_max("add_instance_names_map scales1 generator")
        self.assertEqual(target().name, "notes1", "a later one does not take over")
        self.hub.handle("set_active_instance scales1", "web")
        t = target()
        self.assertEqual((t.name, t.type, t.algorithm_file), ("scales1", "generator",
                                                            os.path.join(self.playground, "algorithms", "scales1.js")))


class ActiveInstanceTests(HubTest):
    """Max says which instance is active, with its type; Claude asks for the map and chooses."""

    def setUp(self):
        super().setUp()
        self.answer = None  # what Max answers to server get_instances
        send = self.bridge.send

        def send_and_answer(text):
            send(text)
            if text == "server get_instances" and self.answer is not None:
                self.bridge.from_max(self.answer)
            return True

        self.bridge.send = send_and_answer
        app = FastMCP("t")
        register_instance_tools(app)
        self.tools = {t.name: t for t in app._tool_manager.list_tools()}

    def call(self, tool, **arguments):
        return self.tools[tool].fn(**arguments)

    def test_max_sends_the_name_and_the_type(self):
        self.setup_patch()
        self.bridge.from_max("set_active_instance chords1 selector")
        self.assertEqual((self.hub.active, self.hub.instances["chords1"]), ("chords1", "selector"))
        self.assertEqual(self.heard(), ["add_instance_names_map chords1 selector", "chords1 history []",
                                        "set_active_instance chords1"])
        self.assertEqual(self.bridge.sent, [], "Max is not told what it said")
        self.bridge.from_max("set_active_instance notes1 score")
        self.assertEqual(self.heard()[-1], "set_active_instance notes1", "known: only the active one changes")
        self.bridge.from_max("set_active_instance x mixer")
        self.assertIn("unknown type mixer", self.bridge.sent[-1])
        self.assertEqual(self.hub.active, "notes1")

    def test_a_map_sent_again_keeps_the_active_instance(self):
        self.setup_patch()
        self.bridge.from_max("set_active_instance notes1 score")
        self.bridge.from_max("clear_instance_names_map")
        self.bridge.from_max("add_instance_names_map scales1 generator")
        self.bridge.from_max("add_instance_names_map notes1 score")
        self.assertEqual(target().name, "notes1")

    def test_the_answer_to_get_instances_replaces_the_map(self):
        self.setup_patch()
        self.bridge.from_max("set_active_instance notes1")
        self.clients.clear()
        self.assertTrue(self.bridge.from_max("instances scales1 generator chords1 selector"))
        self.assertEqual(self.hub.instances, {"scales1": "generator", "chords1": "selector"})
        self.assertEqual(self.hub.active, "scales1", "the active one went: the first takes its place")
        self.assertEqual(self.heard(), ["clear_instance_names_map", "add_instance_names_map scales1 generator",
                                        "add_instance_names_map chords1 selector", "scales1 history []",
                                        "chords1 history []", "set_active_instance scales1"])
        self.bridge.from_max("instances")
        self.assertEqual((self.hub.instances, self.hub.active), ({}, ""))

    def test_get_instances_asks_max(self):
        self.setup_patch()
        self.answer = "instances scales1 generator notes1 score chords1 selector"
        self.assertEqual(self.call("get_instances"),
                         "active: scales1 (generator)\nscales1 generator\nnotes1 score\nchords1 selector")
        self.assertEqual(self.bridge.sent, ["server get_instances"])

    def test_get_instances_without_an_answer_gives_the_last_map(self):
        self.setup_patch()
        with unittest.mock.patch("bach_mcp.chat.hub.INSTANCES_WAIT", 0.05):
            text = self.call("get_instances")
        self.assertTrue(text.startswith("active: scales1 (generator)\nscales1 generator\nnotes1 score"))
        self.assertIn("Max did not answer", text)

    def test_set_active_instance_tells_max_and_the_products_follow(self):
        self.setup_patch()
        self.assertEqual(self.call("set_active_instance", name="notes1"), "active: notes1 (score)")
        self.assertEqual(self.bridge.sent, ["set_active_instance notes1"])
        self.assertEqual(target().name, "notes1")

    def test_set_active_instance_asks_max_for_a_name_it_does_not_know(self):
        self.setup_patch()
        self.answer = "instances scales1 generator notes1 score fresh1 transformer"
        self.assertEqual(self.call("set_active_instance", name="fresh1"), "active: fresh1 (transformer)")
        self.answer = "instances scales1 generator"
        text = self.call("set_active_instance", name="nobody")
        self.assertTrue(text.startswith("ERROR: no instance nobody in the patch"))
        self.assertIn("scales1 generator", text)
        self.assertEqual(target().name, "scales1")


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
        self.assertEqual(self.stages("notes1"), ["received", "starting", "sent", "writing", "done 7"],
                         "each stage once, as it happens")
        size = [t for t in self.bridge.sent if t.startswith("server prompt notes1 skills_size ")]
        self.assertEqual(len(size), 1, "the skill's size, once for each prompt")
        self.assertGreater(int(size[0].split()[-1]), 0)
        sent = [t for t in self.bridge.sent if not t.startswith("server prompt ")]
        self.assertEqual([t.split()[1] for t in sent[:2]], ["answer", "done"],
                         "Max gets no echo of its own prompt, no pieces, and no thinking: the stages say it")
        self.assertEqual(sent[2:4], ['server answer notes1 "Three notes for you."', "server answer tokens 7"])
        self.assertTrue(sent[4].startswith("server answer time "))
        self.assertEqual(len(sent), 5)
        self.assertIn("notes1 thinking", self.heard(web_only=True), "the page still gets it")
        self.assertIn("You are writing for a score instance", self.client.requests[0]["messages"][0]["content"])

    def test_the_tools_work_for_the_prompted_instance_not_the_active_one(self):
        self.setup_patch()
        self.hub.handle("set_active_instance notes1", "web")
        self.replies = [tool_reply("send_algorithm", {"code": "x"}), text_reply("Done.")]
        self.hub.handle('scales1 prompt "a scale"', "web")
        self.answered("scales1")
        self.assertEqual(self.tools.calls, [("send_algorithm", "scales1")])
        self.assertEqual(self.stages("scales1")[:-1], ["received", "starting", "sent", "calling send_algorithm",
                                                       "running send_algorithm", "sent", "writing"],
                         "the model reads the tool's answer: sent again")
        self.assertTrue(self.stages("scales1")[-1].startswith("done "))
        self.assertIn('scales1 tool send_algorithm "called for scales1"', self.bridge.sent)
        self.assertEqual(target().name, "notes1", "after the turn, the active one again")

    def test_a_claude_written_to_directly_keeps_the_active_instance_during_an_answer(self):
        self.setup_patch()
        self.hub.handle("set_active_instance notes1", "web")
        self.go.clear()  # the model holds its answer: scales1's turn stays open
        self.replies = [text_reply("Done.")]
        self.hub.handle('scales1 prompt "a scale"', "web")
        deadline = time.time() + 3
        while "scales1 thinking" not in self.heard() and time.time() < deadline:
            time.sleep(0.01)
        self.assertEqual(target().name, "scales1", "the Claude Code that answers the prompt: its instance")
        with calling_directly():
            self.assertEqual(target().name, "notes1", "Claude Desktop, meanwhile: the active one")
        self.go.set()
        self.answered("scales1")

    def test_refusals(self):
        self.hub.handle("add_instance_names_map scales1 generator", "web")
        self.hub.handle("scales1 prompt hello", "web")
        self.hub.handle("ghost prompt hello", "web")
        ghost = self.stages("ghost")
        before = self.heard()
        self.setup_patch()
        self.hub.handle("scales1 prompt", "web")
        self.status.set("loading", model="test-model")
        self.hub.handle("scales1 prompt hello", "web")
        errors = [t for t in before + self.heard() if " error " in t]
        self.assertEqual(errors, ['scales1 error "no playground: the patch sends set_playground <folder>"',
                                  'ghost error "no instance ghost in the map"',
                                  'scales1 error "the prompt is empty"',
                                  'scales1 error "the model is not ready (loading)"'])
        self.assertEqual(ghost, ["received", "error no instance ghost in the map"])

    def test_without_a_local_model_prompts_are_refused(self):
        self.hub.close()
        self.status.set("claude")
        hub = self.start(make=False)
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.bridge.from_max("add_instance_names_map notes1 score")
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
        self.bridge.from_max("add_instance_names_map notes1 score")
        hub.handle('notes1 prompt "second"', "web")
        self.answered("notes1")
        sent = [m["content"] for m in self.client.requests[0]["messages"][1:]]
        self.assertEqual(sent, ["first", "One.", "second"])

    def test_docs_already_sent_are_not_sent_again_after_a_restart(self):
        self.with_docs = True
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "a line for cello"', "web")
        self.answered("notes1")
        first = self.client.requests[0]["messages"][-1]["content"]
        self.assertIn("Reference for this request", first)

        self.hub.close()  # Bach starts again
        self.clients.clear()
        hub = self.start()
        self.replies = [text_reply("Two.")]
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.bridge.from_max("add_instance_names_map notes1 score")
        hub.handle('notes1 prompt "now the cello higher"', "web")
        self.answered("notes1")
        self.assertEqual(self.client.requests[0]["messages"][-1]["content"], "now the cello higher",
                         "the cello's doc is already in the conversation")

    def histories(self):
        """The conversations the pages were sent: {name: [prompts]}, the last one for each."""
        out = {}
        for text in self.heard():
            said = words(text)
            if len(said) == 3 and said[1] == "history":
                out[said[0]] = [m["prompt"] for m in json.loads(said[2]) if m["role"] == "user"]
        return out

    def test_each_map_and_playground_sends_the_saved_conversations_again(self):
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.answered("notes1")
        self.clients.clear()
        self.bridge.from_max("clear_instance_names_map")
        self.bridge.from_max("add_instance_names_map scales1 generator")
        self.bridge.from_max("add_instance_names_map notes1 score")
        self.assertEqual(self.histories(), {"scales1": [], "notes1": ["first"]})

        self.clients.clear()
        other = os.path.join(self.folder, "other")
        self.bridge.from_max(f"set_playground {line(other)}")
        self.assertEqual(self.histories(), {"scales1": [], "notes1": []}, "the other playground has none")
        self.clients.clear()
        self.bridge.from_max(f"set_playground {line(other)}")
        self.assertEqual(self.histories(), {}, "the same playground again: nothing to reload")
        self.bridge.from_max(f"set_playground {line(self.playground)}")
        self.assertEqual(self.histories(), {"scales1": [], "notes1": ["first"]})

        self.clients.clear()
        self.assertTrue(self.bridge.from_max("instances notes1 score"))
        self.assertEqual(self.histories(), {"notes1": ["first"]})

    def test_a_map_leaves_the_answer_being_drawn_alone(self):
        self.setup_patch()
        self.go.clear()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.bridge.from_max("add_instance_names_map notes1 score")
        self.bridge.from_max("add_instance_names_map scales1 generator")
        self.assertEqual(self.histories(), {"scales1": []})
        self.go.set()
        self.answered("notes1")

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

    def test_an_instance_that_changes_type_starts_a_new_conversation(self):
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.answered("notes1")
        self.bridge.from_max("add_instance_names_map notes1 generator")
        files = os.listdir(os.path.join(self.playground, "prompts"))
        self.assertEqual(len(files), 1)
        self.assertTrue(files[0].startswith("notes1-"), "the score instance's conversation is kept aside")
        history = [words(t) for t in self.heard(web_only=True) if t.startswith("notes1 history")]
        self.assertEqual(json.loads(history[-1][2]), [], "the page clears it")
        self.replies = [text_reply("Two.")]
        self.clients.clear()
        self.hub.handle('notes1 prompt "second"', "web")
        self.answered("notes1")
        messages = self.client.requests[0]["messages"]
        self.assertEqual([m["content"] for m in messages[1:]], ["second"])
        self.assertIn("You are writing for a generator", messages[0]["content"])

    def test_the_same_map_again_keeps_the_conversation(self):
        self.setup_patch()
        self.replies = [text_reply("One.")]
        self.hub.handle('notes1 prompt "first"', "web")
        self.answered("notes1")
        self.bridge.from_max("add_instance_names_map notes1 score")
        self.bridge.from_max("instances scales1 generator notes1 score")
        self.assertEqual(os.listdir(os.path.join(self.playground, "prompts")), ["notes1.jsonl"])

    def test_one_answer_at_a_time_and_a_waiting_prompt_can_be_stopped(self):
        self.setup_patch()
        self.go.clear()  # scales1's answer is held
        self.replies = [text_reply("Held.")]
        self.hub.handle('scales1 prompt "first"', "web")
        self.hub.handle('notes1 prompt "wait"', "web")
        self.assertEqual(self.heard()[-1], "notes1 queued")
        self.hub.handle("notes1 stop", "web")
        self.assertEqual(self.heard()[-1], "notes1 stopped")
        self.assertEqual(self.stages("notes1"), ["received", "queued 1", "stopped"])
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


class ToolThreadTests(unittest.TestCase):
    """A tool may wait seconds for Max or Node: it must not hold the server's event loop."""

    def call(self, app, is_direct=False):
        import time as clock

        def slow() -> str:
            clock.sleep(0.3)
            return f"{threading.current_thread() is threading.main_thread()} {direct()}"

        app.add_tool(threaded(slow, direct=is_direct))

        async def both():
            ticks = 0

            async def tick():
                nonlocal ticks
                while True:
                    await asyncio.sleep(0.01)
                    ticks += 1

            ticking = asyncio.ensure_future(tick())
            result = await app.call_tool("slow", {})
            ticking.cancel()
            return ticks, result

        ticks, result = asyncio.run(both())
        blocks = result[0] if isinstance(result, tuple) else result
        return ticks, blocks[0].text

    def test_the_loop_goes_on_while_a_tool_runs(self):
        ticks, said = self.call(create_tools(OfflineBridge(), log_calls=False))
        self.assertGreater(ticks, 10, "the page's stream and other sessions were served meanwhile")
        self.assertEqual(said, "False False", "on a thread of its own; not a direct call")

    def test_the_app_claude_reaches_marks_its_calls_as_direct(self):
        self.assertEqual(self.call(create_tools(OfflineBridge(), log_calls=False, direct=True), True)[1], "False True")
        self.assertFalse(direct(), "only while the tool runs")


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

    def test_serve_has_the_page_beside_the_tools(self):
        """bachmcp.server claude: the page, the hub's two ends and /mcp on one port."""
        from starlette.testclient import TestClient
        from bach_mcp.chat.web import create_app
        self.status.set("claude")
        with TestClient(create_app(self.hub, self.status, FastMCP("bach")), base_url="http://127.0.0.1:8090") as client:
            self.assertIn("<title>Bach</title>", client.get("/").text)
            self.assertEqual(client.get("/api/state").json()["state"], "claude")
            self.assertTrue(client.get("/api/state").json()["ready"])
            self.setup_patch()
            self.assertEqual(client.post("/api/line", content="set_active_instance scales1").json(), {"ok": True})
            mcp = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
                headers={"Accept": "application/json, text/event-stream"})
            self.assertEqual(mcp.status_code, 200)
            self.assertIn('"serverInfo"', mcp.text)

    def test_claude_code_started_by_bach_gets_its_mode_and_no_instructions(self):
        """/mcp carries the skill as instructions and every tool; /mcp/headless/<mode>, for the
        claude -p Bach starts, no instructions and only that mode's tools, as the local model has them."""
        import asyncio
        from starlette.testclient import TestClient
        from bach_mcp import claude
        from bach_mcp.bridge.max import OfflineBridge
        from bach_mcp.chat.web import create_app
        from bach_mcp.config import Config
        from bach_mcp.prompt.modes import MODE_TOOLS
        config = Config()
        headless = claude.headless_apps(config, OfflineBridge())
        app = create_app(self.hub, self.status, claude.mcp_app(config, OfflineBridge()), headless)
        hello = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}
        accept = {"Accept": "application/json, text/event-stream"}

        def tools(path, session):
            listed = client.post(path, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                                 headers={**accept, "mcp-session-id": session})
            return sorted(set(re.findall(r'"name":"(\w+)"', listed.text)) & set(MODE_TOOLS["score"] + MODE_TOOLS["algo"]
                                                                            + ("get_instances", "set_active_instance")))

        with TestClient(app, base_url="http://127.0.0.1:8090") as client:
            full = client.post("/mcp", json=hello, headers=accept)
            self.assertEqual(full.status_code, 200)
            self.assertIn('"instructions"', full.text)
            self.assertEqual(len(tools("/mcp", full.headers["mcp-session-id"])), 16)
            for mode in ("score", "algo"):
                path = f"/mcp/headless/{mode}"
                self.assertEqual(config.headless_mcp_url(mode), "http://127.0.0.1:8090" + path)
                bare = client.post(path, json=hello, headers=accept)
                self.assertEqual(bare.status_code, 200)
                self.assertNotIn('"instructions"', bare.text)
                self.assertEqual(tools(path, bare.headers["mcp-session-id"]), sorted(MODE_TOOLS[mode]), mode)

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
            "add_instance_names_map notes1 score",
            "set_active_instance notes1"])

    def test_the_state_reaches_the_pages(self):
        self.status.set("loading", model="other")
        self.assertEqual(self.heard(web_only=True)[-1], 'state loading other ""')
        self.assertEqual(self.bridge.sent, [], "Max asks for the state itself (bach status)")


if __name__ == "__main__":
    unittest.main()
