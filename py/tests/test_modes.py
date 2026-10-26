"""Tests for the /score and /algo modes: the prefixes, the skill parts and the tools of each mode.
How the chat applies them is in test_chat.py. Run: python -m unittest discover -s py/tests"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.prompt.modes import MODE_TOOLS, split_prefix, tools_for  # noqa: E402
from bach_mcp.prompt.skill import load_skill, skill_for  # noqa: E402

RAW = load_skill(raw=True)
FULL = load_skill()


def tool(name):
    return {"type": "function", "function": {"name": name, "description": "", "parameters": {}}}


class PrefixTests(unittest.TestCase):
    def test_split_prefix(self):
        self.assertEqual(split_prefix("/algo a canon"), ("algo", "a canon"))
        self.assertEqual(split_prefix("  /SCORE\nthree notes"), ("score", "three notes"))
        self.assertEqual(split_prefix("/algo"), ("algo", "/algo"), "only the prefix: the text stays")
        self.assertEqual(split_prefix("a canon /algo"), (None, "a canon /algo"))
        self.assertEqual(split_prefix("/algorithm please"), (None, "/algorithm please"))


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
        self.assertLess(len(algo), 0.7 * len(FULL))
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


class ToolsTests(unittest.TestCase):
    def test_each_mode_gets_only_its_tools(self):
        tools = [tool(n) for n in ("write_score", "read_score", "clear_score", "p2mc", "send_algorithm")]
        names = lambda ts: [t["function"]["name"] for t in ts]  # noqa: E731
        self.assertEqual(names(tools_for(tools, "algo")), ["send_algorithm"])
        self.assertEqual(names(tools_for(tools, "score")), ["write_score", "read_score", "clear_score", "p2mc"])

    def test_every_tool_belongs_to_one_mode(self):
        self.assertFalse(set(MODE_TOOLS["score"]) & set(MODE_TOOLS["algo"]))


if __name__ == "__main__":
    unittest.main()
