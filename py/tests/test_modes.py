"""Tests for the /score and /algo modes: the prefixes, the skill parts, the tools, and what the gateway
sends. Run: python -m unittest discover -s py/tests"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.config import BachConfig  # noqa: E402
from bach_mcp.gateway import ModeSwitch, build_ollama_request  # noqa: E402
from bach_mcp.mcp_app import load_skill  # noqa: E402
from bach_mcp.modes import apply_mode, mode_of, skill_for, split_prefix, tools_for  # noqa: E402
from bach_mcp.translate import normalize_score  # noqa: E402

RAW = load_skill(raw=True)
FULL = load_skill()


def tool(name):
    return {"type": "function", "function": {"name": name, "description": "", "parameters": {}}}


ALL_TOOLS = [tool(n) for n in ("write_score", "read_score", "clear_score", "send_algorithm", "other_server_tool")]


def names(tools):
    return [t["function"]["name"] for t in tools]


def request(*user_messages, system=FULL):
    messages = [{"role": "system", "content": system}]
    for i, text in enumerate(user_messages):
        if i:
            messages.append({"role": "assistant", "content": f"answer {i}"})
        messages.append({"role": "user", "content": text})
    return {"messages": messages, "tools": ALL_TOOLS}


class PrefixTests(unittest.TestCase):
    def test_split_prefix(self):
        self.assertEqual(split_prefix("/algo a canon"), ("algo", "a canon"))
        self.assertEqual(split_prefix("  /SCORE\nthree notes"), ("score", "three notes"))
        self.assertEqual(split_prefix("/algo"), ("algo", "/algo"), "only the prefix: the text stays")
        self.assertEqual(split_prefix("a canon /algo"), (None, "a canon /algo"))
        self.assertEqual(split_prefix("/algorithm please"), (None, "/algorithm please"))

    def test_a_mode_lasts_until_the_other_prefix(self):
        self.assertEqual(mode_of(request("hello")["messages"]), "score")
        self.assertEqual(mode_of(request("/algo a canon", "denser")["messages"]), "algo")
        self.assertEqual(mode_of(request("/algo a canon", "/score three notes", "louder")["messages"]), "score")


class SkillTests(unittest.TestCase):
    def test_each_mode_gets_its_part(self):
        algo, score = skill_for(RAW, "algo"), skill_for(RAW, "score")
        self.assertIn("## Algorithms", algo)
        self.assertIn("## Marks", algo)
        self.assertNotIn("## JSON format", algo)
        self.assertNotIn("write_score", algo)
        self.assertIn("## JSON format", score)
        self.assertNotIn("## Algorithms", score)
        self.assertNotIn("send_algorithm", score)
        for text in (algo, score, FULL):
            self.assertNotIn("<!--", text)
            self.assertNotRegex(text, r"\n\n\n")
        self.assertLess(len(algo), 0.65 * len(FULL))
        self.assertLess(len(score), 0.7 * len(FULL))

    def test_a_skill_without_markers_is_the_same_in_every_mode(self):
        text = "# My own skill\n\nWrite music.\n"
        for mode in ("algo", "score", None):
            self.assertEqual(skill_for(text, mode), text)

    def test_the_algo_pitch_line_agrees_with_the_table(self):
        algo = skill_for(RAW, "algo")
        octaves = dict(re.findall(r"C(\d) (\d{4})", algo))
        self.assertEqual({int(k): int(v) for k, v in octaves.items()}, {o: (o + 1) * 1200 for o in range(1, 8)})
        classes = re.findall(r"([A-G]#?) (\d{1,4})[,.]", algo.split("Add the pitch class:", 1)[1])
        self.assertEqual([int(v) for _, v in classes[:12]], [i * 100 for i in range(12)])

    def test_the_marks_of_algo_mode_are_accepted(self):
        marks = skill_for(RAW, "algo").split("## Marks", 1)[1]

        def values(key):
            line = re.search(rf"- `{key}`:(.*?)(?=\n- |\Z)", marks, re.S).group(1)
            return re.findall(r'"([^"]+)"', line)

        chord = lambda **marks: {"voices": [{"chords": [dict(marks, onset=0, notes=[{"pitch": 6000, "dur": 500}])]}]}  # noqa: E731
        for art in values("art"):
            normalize_score(chord(art=art))
        for dyn in values("dyn"):
            normalize_score(chord(dyn=dyn))
        for head in values("head"):
            normalize_score({"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "head": head}]}]}]})


class ApplyModeTests(unittest.TestCase):
    def test_score_mode_by_default(self):
        body, mode = apply_mode(request("three notes"), FULL, RAW)
        self.assertEqual(mode, "score")
        self.assertEqual(names(body["tools"]), ["write_score", "read_score", "clear_score", "other_server_tool"])
        self.assertEqual(body["messages"][0]["content"], skill_for(RAW, "score"))

    def test_algo_mode_strips_the_prefix_and_keeps_only_its_tool(self):
        body, mode = apply_mode(request("/algo a canon", "denser"), FULL, RAW)
        self.assertEqual(mode, "algo")
        self.assertEqual(names(body["tools"]), ["send_algorithm", "other_server_tool"])
        self.assertEqual(body["messages"][0]["content"], skill_for(RAW, "algo"))
        self.assertEqual([m["content"] for m in body["messages"] if m["role"] == "user"], ["a canon", "denser"])

    def test_a_system_message_edited_by_hand_is_left_alone(self):
        body, _ = apply_mode(request("/algo a canon", system="Be brief."), FULL, RAW)
        self.assertEqual(body["messages"][0]["content"], "Be brief.")

    def test_prefixed_tool_names_and_content_parts(self):
        tools = [tool("bach__write_score"), tool("bach.send_algorithm")]
        self.assertEqual(names(tools_for(tools, "algo")), ["bach.send_algorithm"])
        body = {"messages": [{"role": "user", "content": [{"type": "text", "text": "/algo drones"}]}]}
        moded, mode = apply_mode(body, FULL, RAW)
        self.assertEqual((mode, moded["messages"][0]["content"][0]["text"]), ("algo", "drones"))

    def test_the_conversation_prefix_stays_the_same_between_requests(self):
        # The model server reuses what it has read only if earlier messages do not change.
        first, _ = apply_mode(request("/algo a canon"), FULL, RAW)
        second, _ = apply_mode(request("/algo a canon", "denser"), FULL, RAW)
        self.assertEqual(second["messages"][:len(first["messages"])], first["messages"])
        self.assertEqual(second["tools"], first["tools"])


class GatewayTests(unittest.TestCase):
    def test_the_ollama_request_carries_the_mode(self):
        config = BachConfig()
        config.model.backend = "ollama"
        config.model.ollama_model = "some-model"
        with_mode = ModeSwitch(config)
        payload = build_ollama_request(with_mode(request("/algo a canon")), config)
        self.assertEqual([t["function"]["name"] for t in payload["tools"]], ["send_algorithm", "other_server_tool"])
        self.assertTrue(payload["messages"][0]["content"].startswith("# Bach"))
        self.assertIn("## Algorithms", payload["messages"][0]["content"])
        self.assertEqual(payload["messages"][1]["content"], "a canon")


if __name__ == "__main__":
    unittest.main()
