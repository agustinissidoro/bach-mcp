"""The local chat: the conversation engine (modes, docs, the tool loop) and its web app."""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from bach_mcp.bridge.max import OfflineBridge  # noqa: E402
from bach_mcp.chat.engine import Conversation  # noqa: E402
from bach_mcp.prompt.docs import DocLibrary  # noqa: E402
from bach_mcp.prompt.skill import load_skill, skill_for  # noqa: E402
from bach_mcp.tools import session  # noqa: E402
from bach_mcp.tools.inprocess import LocalTools  # noqa: E402
from bach_mcp.tools.registry import create_tools  # noqa: E402
from fakemodel import FakeClient, chunk, text_reply, tool_reply  # noqa: E402

RAW = load_skill(raw=True)


def offline_tools(folder):
    return LocalTools(create_tools(OfflineBridge(), log_calls=False))


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.tools = offline_tools(self.folder)

    def chat(self, *replies, docs=False, rounds=8):
        self.client = FakeClient(*replies)
        return Conversation(self.client, self.tools, RAW, DocLibrary() if docs else None, rounds)

    def kinds(self, events):
        return [e["type"] for e in events]

    def tool_names(self, request):
        return [t["function"]["name"] for t in request["tools"]]


class ModeTests(EngineTest):
    def test_score_mode_by_default(self):
        conversation = self.chat(text_reply("Here."))
        list(conversation.send("three notes"))
        request = self.client.requests[0]
        self.assertEqual(request["messages"][0], {"role": "system", "content": skill_for(RAW, "score")})
        self.assertIn("write_score", self.tool_names(request))
        self.assertNotIn("send_algorithm", self.tool_names(request))

    def test_a_prefix_sets_the_mode_until_the_other_prefix(self):
        conversation = self.chat(text_reply("A canon."), text_reply("Denser."), text_reply("Notes."))
        events = list(conversation.send("/algo a canon"))
        self.assertEqual(events[0], {"type": "mode", "mode": "algo"})
        list(conversation.send("denser"))
        list(conversation.send("/score three notes"))
        first, second, third = self.client.requests
        self.assertEqual(self.tool_names(first), ["send_algorithm"])
        self.assertEqual(first["messages"][0]["content"], skill_for(RAW, "algo"))
        self.assertEqual(first["messages"][1], {"role": "user", "content": "a canon"})
        self.assertEqual(self.tool_names(second), ["send_algorithm"])
        self.assertIn("write_score", self.tool_names(third))

    def test_only_a_prefix_switches_without_asking_the_model(self):
        conversation = self.chat()
        self.assertEqual(list(conversation.send("/algo")), [{"type": "mode", "mode": "algo"}, {"type": "done", "finish": "stop"}])
        self.assertEqual((conversation.mode, self.client.requests), ("algo", []))

    def test_the_conversation_only_grows_between_requests(self):
        # The model server reuses what it has read only if the earlier messages do not change.
        conversation = self.chat(text_reply("One."), text_reply("Two."))
        list(conversation.send("/algo a canon"))
        list(conversation.send("denser"))
        first, second = self.client.requests
        self.assertEqual(second["messages"][:len(first["messages"])], first["messages"])
        self.assertEqual(second["tools"], first["tools"])

    def test_a_new_chat_starts_from_scratch(self):
        conversation = self.chat(text_reply("One."))
        list(conversation.send("/algo a canon"))
        before = session.conversation()
        conversation.new()
        self.assertEqual((conversation.mode, conversation.history), ("score", []))
        self.assertEqual(session.conversation(), before + 1, "the tools forget the last read_score")


class DocsTests(EngineTest):
    def test_docs_are_added_once_at_the_first_mention(self):
        conversation = self.chat(text_reply("A duet."), text_reply("Again."), docs=True)
        events = list(conversation.send("a duet for cello and alto flute"))
        self.assertEqual(events[0]["type"], "docs")
        self.assertIn("strings/cello", events[0]["added"])
        self.assertIn("woodwinds/alto-flute", events[0]["added"])
        self.assertIn("# Cello", self.client.requests[0]["messages"][1]["content"])
        events = list(conversation.send("now only the cello"))
        self.assertNotIn("docs", self.kinds(events))


class ToolLoopTests(EngineTest):
    def test_a_tool_runs_and_its_answer_goes_back_to_the_model(self):
        conversation = self.chat(tool_reply("p2mc", {"pitches": ["C4", "E4"]}, text="The pitches first."),
                                 text_reply("Written."))
        events = list(conversation.send("a major third"))
        self.assertEqual([k for k in self.kinds(events) if k not in ("text", "calling", "stage")],
                         ["round", "tool_call", "tool_result", "round", "done"])
        result = next(e for e in events if e["type"] == "tool_result")
        self.assertEqual(json.loads(result["result"]), [6000, 6400])
        second = self.client.requests[1]["messages"]
        self.assertEqual(second[2]["tool_calls"][0]["function"]["name"], "p2mc")
        self.assertEqual((second[3]["role"], second[3]["tool_call_id"], json.loads(second[3]["content"])),
                         ("tool", "call_1", [6000, 6400]))
        self.assertEqual(events[-1], {"type": "done", "finish": "stop"})

    def test_the_same_call_twice_in_a_turn_is_not_run_again(self):
        call = {"pitches": ["C4"]}
        conversation = self.chat(tool_reply("p2mc", call), tool_reply("p2mc", call, call_id="call_2"), text_reply("ok"))
        results = [e["result"] for e in conversation.send("C") if e["type"] == "tool_result"]
        self.assertEqual(results[0], "[6000]")
        self.assertIn("already made this exact call", results[1])

    def test_cut_off_arguments_are_not_run(self):
        broken = tool_reply("p2mc", '{"pitches": ["C4"', call_id="c1")
        conversation = self.chat(broken, text_reply("ok"))
        result = next(e for e in conversation.send("C") if e["type"] == "tool_result")
        self.assertTrue(result["result"].startswith("ERROR: the arguments are not valid JSON"))

    def test_a_reply_that_looped_is_asked_again_once(self):
        looped = [chunk({"tool_calls": [{"index": 0, "id": "c", "function": {"name": "write_score", "arguments": '{"sc'}}]}),
                  chunk(finish="length")]
        conversation = self.chat(looped, text_reply("Fine now."))
        events = list(conversation.send("a long piece"))
        self.assertIn("retry", self.kinds(events))
        self.assertEqual(events[-1], {"type": "done", "finish": "stop"})
        conversation = self.chat(looped, looped)
        events = list(conversation.send("a long piece"))
        self.assertEqual(self.kinds(events).count("retry"), 1)
        self.assertEqual(events[-1], {"type": "done", "finish": "length"})

    def test_tool_rounds_are_limited(self):
        conversation = self.chat(*[tool_reply("p2mc", {"pitches": [f"C{i}"]}, call_id=f"c{i}") for i in range(4)], rounds=2)
        events = list(conversation.send("go"))
        self.assertEqual(self.kinds(events).count("round"), 3, "two rounds of tools, then one request to answer")
        self.assertEqual(events[-1], {"type": "done", "finish": "rounds"})

    def test_after_the_last_round_of_tools_the_model_answers(self):
        conversation = self.chat(*[tool_reply("p2mc", {"pitches": [f"C{i}"]}, call_id=f"c{i}") for i in range(2)],
                                 text_reply("Done."), rounds=2)
        events = list(conversation.send("go"))
        self.assertEqual(events[-1], {"type": "done", "finish": "stop"}, "it reads the last round's results")

    def test_a_model_error_is_an_event(self):
        conversation = self.chat()  # no reply scripted: the client raises
        events = list(conversation.send("hello"))
        self.assertEqual(events[-1]["type"], "error")


class KindTests(EngineTest):
    def test_an_instance_type_fixes_the_mode_and_says_what_it_takes(self):
        self.client = FakeClient(text_reply("A canon."), text_reply("Notes."))
        conversation = Conversation(self.client, self.tools, RAW, None, 8, kind="transformer")
        events = list(conversation.send("/score a canon"))
        self.assertNotIn("mode", [e["type"] for e in events], "no prefix switches an instance's mode")
        request = self.client.requests[0]
        self.assertEqual(request["messages"][1]["content"], "/score a canon")
        self.assertTrue(request["messages"][0]["content"].startswith(skill_for(RAW, "algo", kind="transformer").rstrip()))
        self.assertIn("You are writing for a transformer", request["messages"][0]["content"])
        self.assertEqual(self.tool_names(request), ["send_algorithm"])
        writer = Conversation(self.client, self.tools, RAW, None, 8, kind="writer")
        list(writer.send("three notes"))
        self.assertIn("write_score", self.tool_names(self.client.requests[1]))


if __name__ == "__main__":
    unittest.main()


class OldCodeTests(unittest.TestCase):
    """Algorithm files a later send_algorithm replaced reach the model as a placeholder."""

    @staticmethod
    def call(n, code):
        return {"role": "assistant", "content": "", "tool_calls": [{"id": f"c{n}", "type": "function", "function": {
            "name": "send_algorithm", "arguments": json.dumps({"code": code, "one_line_description": f"v{n}"})}}]}

    @staticmethod
    def result(n, ok):
        return {"role": "tool", "tool_call_id": f"c{n}", "content": "OK. Algorithm saved" if ok else "ERROR in x.js"}

    @staticmethod
    def codes(history):
        return [json.loads(c["function"]["arguments"])["code"] for m in history for c in m.get("tool_calls") or []]

    def test_only_the_last_and_the_last_loaded_stay(self):
        from bach_mcp.chat.engine import OLD_CODE, without_replaced
        history = [{"role": "user", "content": "a canon"}, self.call(1, "one"), self.result(1, True),
                   {"role": "user", "content": "slower"}, self.call(2, "two"), self.result(2, True),
                   {"role": "user", "content": "denser"}, self.call(3, "three"), self.result(3, False)]
        sent = without_replaced(history)
        self.assertEqual(self.codes(sent), [OLD_CODE, "two", "three"], "two is what Max has loaded")
        self.assertEqual(self.codes(history), ["one", "two", "three"], "the history itself keeps every file")
        self.assertEqual(json.loads(sent[1]["tool_calls"][0]["function"]["arguments"])["one_line_description"], "v1")
        history += [self.call(4, "four"), self.result(4, True)]
        self.assertEqual(self.codes(without_replaced(history)), [OLD_CODE, OLD_CODE, OLD_CODE, "four"])
        self.assertEqual(without_replaced(history)[:4], without_replaced(history[:4] + history[4:])[:4],
                         "a pure function of the history")
        one = history[:3]
        self.assertIs(without_replaced(one), one, "a single version is left alone")


class OldScoreTests(unittest.TestCase):
    """Scores a later write_score replaced, and read_score answers read again, reach the model as a placeholder."""

    @staticmethod
    def call(n, name, **arguments):
        return {"role": "assistant", "content": "", "tool_calls": [{"id": f"c{n}", "type": "function", "function": {
            "name": name, "arguments": json.dumps(arguments)}}]}

    @staticmethod
    def result(n, text):
        return {"role": "tool", "tool_call_id": f"c{n}", "content": text}

    @staticmethod
    def scores(history):
        return [json.loads(c["function"]["arguments"]).get("score") for m in history for c in m.get("tool_calls") or []
                if c["function"]["name"] == "write_score"]

    def test_scores_before_the_last_that_replaced_the_roll_go(self):
        from bach_mcp.chat.engine import OLD_SCORE, without_replaced
        history = [self.call(1, "write_score", score="one"), self.result(1, "OK. Score written.\n..."),
                   self.call(2, "write_score", score="two", add=True), self.result(2, "OK. Added to the score.\n..."),
                   self.call(3, "write_score", score="three"), self.result(3, "OK. Score written.\n..."),
                   self.call(4, "write_score", score="four", add=True), self.result(4, "OK. Added to the score.\n..."),
                   self.call(5, "write_score", score="five"), self.result(5, "ERROR: not JSON. Nothing was written.")]
        self.assertEqual(self.scores(without_replaced(history)), [OLD_SCORE, OLD_SCORE, "three", "four", "five"],
                         "three and four are what the roll holds; five failed, the model may fix it")
        self.assertEqual(self.scores(history), ["one", "two", "three", "four", "five"])
        cleared = history + [self.call(6, "clear_score"), self.result(6, "Score cleared.")]
        self.assertEqual(self.scores(without_replaced(cleared)), [OLD_SCORE] * 5)
        self.assertEqual(self.scores(without_replaced(history[:4])), ["one", "two"], "chords added stay with their score")
        alone = history[:2]
        self.assertIs(without_replaced(alone), alone, "one score is left alone")

    def test_a_read_goes_when_the_same_part_is_read_again(self):
        from bach_mcp.chat.engine import OLD_READ, without_replaced
        history = [self.call(1, "read_score"), self.result(1, "the whole score A"),
                   self.call(2, "read_score", from_ms=8000), self.result(2, "from 8000, A"),
                   self.call(3, "read_score", voice=0), self.result(3, "Unchanged since your previous read_score."),
                   self.call(4, "read_score"), self.result(4, "the whole score B")]
        sent = [m["content"] for m in without_replaced(history) if m["role"] == "tool"]
        self.assertEqual(sent, [OLD_READ, "from 8000, A", "Unchanged since your previous read_score.", "the whole score B"],
                         "another part of the score stays; the same part read again replaces the first answer")
        self.assertEqual(without_replaced(history[:6]), history[:6], "an Unchanged answer keeps the one it points to")
