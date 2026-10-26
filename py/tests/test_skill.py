"""The skill's score part: its examples are valid compressed scores, and its worked example adds up.
Run: python -m unittest discover -s py/tests"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

SKILL = os.path.join(os.path.dirname(__file__), "..", "bach_mcp", "prompt", "BACH_SKILL.md")


class SkillTests(unittest.TestCase):
    def setUp(self):
        with open(SKILL, encoding="utf-8") as handle:
            self.text = handle.read()

    def chords(self, block):
        data = json.loads(block)
        return [data] if isinstance(data, list) and data and not isinstance(data[0], list) and not isinstance(data[0], dict) \
            else [c for v in data["voices"] for c in v["chords"]]

    def test_every_example_in_the_skill_is_a_valid_score(self):
        from bach_mcp.music.compress import compress, expand
        from bach_mcp.tools.score_tools import check_short
        blocks = re.findall(r"```json\n(.*?)```", self.text, re.S)
        self.assertGreaterEqual(len(blocks), 5)
        for block in blocks:
            data = json.loads(block)
            if "voices" not in data:  # the bare chord that introduces the format
                data = {"voices": [{"chords": [data]}]}
            self.assertIsNone(check_short(data), block)
            self.assertEqual(compress(expand(data))["voices"], data["voices"], block)

    def test_the_worked_example_follows_its_own_table(self):
        last = json.loads(re.findall(r"```json\n(.*?)```", self.text, re.S)[-1])
        chords = last["voices"][0]["chords"]  # [onset, [pitch, dur, vel], ...]
        self.assertEqual([c[0] for c in chords], [n * 250 for n in range(9)])
        self.assertEqual([c[1][0] for c in chords], [6200, 6500, 6900, 6700, 7100, 6400, 7300, 6600, 6900])

    def test_the_worked_example_shows_what_the_pitch_tools_answer(self):
        from bach_mcp.tools.pitch_tools import call_pitch_tool
        calls = re.findall(r"^(p2mc|transpose)\((.*?)\)\s+→ (\[[^\]]*\])", self.text, re.M)
        self.assertEqual(len(calls), 3)
        for name, args, shown in calls:
            call = json.loads(f"[{args}]")
            arguments = {"pitches": call[0]} if name == "p2mc" else {"pitches": call[0], "cents": call[1]}
            self.assertEqual(call_pitch_tool(name, arguments), shown)

    def test_the_skill_teaches_one_form(self):
        known = {"dynamics", "articulations", "annotation", "lyrics", "notehead", "gliss"}
        for block in re.findall(r"```json\n(.*?)```", self.text, re.S):
            for c in self.chords(block):
                self.assertIsInstance(c[0], (int, float), c)
                for note in c[1:]:
                    self.assertEqual(len([x for x in note if not isinstance(x, dict)]), 3, note)
                    for extras in (x for x in note if isinstance(x, dict)):
                        self.assertLessEqual(set(extras), known, note)

    def test_the_score_part_writes_pitches_in_midicents(self):
        from bach_mcp.prompt.skill import skill_for
        score_part = skill_for(self.text, "score")
        self.assertNotIn("Pitch table", score_part)
        for block in re.findall(r"```json\n(.*?)```", score_part, re.S):
            for c in self.chords(block):
                for note in c[1:]:
                    self.assertIsInstance(note[0], (int, float), note)
                    self.assertGreaterEqual(note[0], 1200, note)

    def test_the_skill_never_teaches_other_units(self):
        for block in re.findall(r"```json\n(.*?)```", self.text, re.S):
            self.assertNotRegex(block, r'"(t|beat|bpm|rest)"')
            self.assertNotRegex(block, r'"pitch": ("|\d{1,3}[,}\s])')



if __name__ == "__main__":
    unittest.main()
