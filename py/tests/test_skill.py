"""The skill's score part: its examples are valid scores in the one syntax, and its worked example adds up.
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

    def scores(self, text=None):
        """Every JSON example as a score; the bare chord that introduces the format, in a score of its own."""
        out = []
        for block in re.findall(r"```json\n(.*?)```", text or self.text, re.S):
            data = json.loads(block)
            out.append(data if "voices" in data else {"voices": [{"chords": [data]}]})
        return out

    def notes(self, text=None):
        return [n for score in self.scores(text) for v in score["voices"] for c in v["chords"] for n in c["notes"]]

    def test_every_example_in_the_skill_is_a_valid_score(self):
        from bach_mcp.music.reader import lean
        from bach_mcp.tools.score_tools import check_score, complete
        scores = self.scores()
        self.assertGreaterEqual(len(scores), 5)
        for score in scores:
            self.assertIsNone(check_score(score), score)
            self.assertEqual(lean(complete(score)), score, "an example is written as read_score would show it")

    def test_the_worked_example_follows_its_own_table(self):
        chords = self.scores()[-1]["voices"][0]["chords"]
        self.assertEqual([c["onset"] for c in chords], [n * 250 for n in range(9)])
        self.assertEqual([c["notes"][0]["pitch"] for c in chords], [6200, 6500, 6900, 6700, 7100, 6400, 7300, 6600, 6900])

    def test_the_worked_example_shows_what_the_pitch_tools_answer(self):
        from bach_mcp.tools.pitch_tools import call_pitch_tool
        calls = re.findall(r"^(p2mc|transpose)\((.*?)\)\s+→ (\[[^\]]*\])", self.text, re.M)
        self.assertEqual(len(calls), 3)
        for name, args, shown in calls:
            call = json.loads(f"[{args}]")
            arguments = {"pitches": call[0]} if name == "p2mc" else {"pitches": call[0], "cents": call[1]}
            self.assertEqual(call_pitch_tool(name, arguments), shown)

    def test_the_skill_teaches_one_form(self):
        marks = {"20", "21", "22", "23", "24"}
        for note in self.notes():
            self.assertLessEqual(set(note), {"pitch", "dur", "vel", "slots", "breakpoints"}, note)
            self.assertLessEqual(set(note.get("slots", {})), marks, note)
            if "breakpoints" in note:
                self.assertEqual((note["breakpoints"][0], note["breakpoints"][-1][0]), ([0, 0, 0], 1), note)

    def test_the_score_part_writes_pitches_in_midicents(self):
        from bach_mcp.prompt.skill import skill_for
        score_part = skill_for(self.text, "score")
        self.assertNotIn("Pitch table", score_part)
        notes = self.notes(score_part)
        self.assertTrue(notes)
        for note in notes:
            self.assertIsInstance(note["pitch"], (int, float), note)
            self.assertGreaterEqual(note["pitch"], 1200, note)

    def test_the_skill_never_teaches_other_units(self):
        for block in re.findall(r"```json\n(.*?)```", self.text, re.S):
            self.assertNotRegex(block, r'"(t|beat|bpm|rest)"')
            self.assertNotRegex(block, r'"pitch": ("|\d{1,3}[,}\s])')



if __name__ == "__main__":
    unittest.main()
