"""The skill built from a playground's files (prompt/skills.py): profiles, extra skills, markers.
Run: python -m unittest discover -s py/tests"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.prompt.skill import SKILL_PATH, closed, load_skill, read_skill, skill_for  # noqa: E402
from bach_mcp.prompt.skills import COMPILED, SkillError, build, compile_skill, read_compiled  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402


class SkillsTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        self.pg = prepare(os.path.join(folder, "pg"))

    def skill(self, name, text):
        with open(os.path.join(self.pg, "skills", name + ".md"), "w", encoding="utf-8") as f:
            f.write(text)

    def profile(self, name, data):
        with open(os.path.join(self.pg, "skills", "profiles", name + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f)

    def test_core_alone_is_the_built_in_skill(self):
        self.profile("default", {"skills": ["core-algorithmic"]})
        compiled = build(self.pg, "default")
        self.assertEqual([name for name, _ in compiled.used], ["core-algorithmic"])
        self.assertEqual(compiled.warnings, [])
        for mode in (None, "score", "algo"):
            for verbose in (True, False):
                self.assertEqual(skill_for(compiled.text, mode, verbose), load_skill(mode, verbose=verbose))

    def test_profile_then_skills_each_once(self):
        self.skill("electronic", "Think in sound objects.")
        self.skill("analysis", "Analyse first.")
        self.profile("electro", {"skills": ["core-algorithmic", "electronic.md"]})
        compiled = compile_skill(self.pg, "electro.json", ["analysis", "electronic"])
        self.assertEqual([name for name, _ in compiled.used], ["core-algorithmic", "electronic", "analysis"])
        self.assertEqual(compiled.warnings, ["skill electronic is chosen twice: used once"])
        self.assertLess(compiled.text.index("sound objects"), compiled.text.index("Analyse first"))

    def test_skills_alone_and_no_core(self):
        self.skill("analysis", "Analyse first.")
        compiled = compile_skill(self.pg, "", ["analysis"])
        self.assertIn("no core skill", compiled.warnings[0])
        self.assertEqual(skill_for(compiled.text).strip(), "Analyse first.")

    def test_nothing_or_missing_files_are_errors(self):
        with self.assertRaisesRegex(SkillError, "no skills chosen"):
            compile_skill(self.pg)
        with self.assertRaisesRegex(SkillError, "no profile nope"):
            compile_skill(self.pg, "nope")
        with self.assertRaisesRegex(SkillError, "no skill nope"):
            compile_skill(self.pg, "", ["core-algorithmic", "nope"])
        with self.assertRaisesRegex(SkillError, "not a name"):
            compile_skill(self.pg, "", ["../core-algorithmic"])
        self.profile("bad", ["core-algorithmic"])
        with self.assertRaisesRegex(SkillError, "expected"):
            compile_skill(self.pg, "bad")

    def test_a_marker_never_runs_into_the_next_file(self):
        self.skill("a", "For all.\n<!-- score -->\nScore only.\n<!-- verbose -->\nTalk a lot.")
        self.skill("b", "Also for all.")
        text = compile_skill(self.pg, "", ["a", "b"]).text
        self.assertIn("Also for all.", skill_for(text, "algo", verbose=False))
        self.assertNotIn("Score only.", skill_for(text, "algo"))
        self.assertNotIn("Talk a lot.", skill_for(text, "score", verbose=False))

    def test_markers_open_and_close(self):
        text = ("All.\n<!-- score -->\nScore.\n<!-- /score -->\nAll again.\n"
                "<!-- algo -->\nAlgo.\n<!-- transformer selector -->\nReads a score.\n"
                "<!-- /transformer selector -->\nAlgo again.\n<!-- /algo -->\nEnd.\n<!-- /score -->\n")
        self.assertEqual(skill_for(text, instance_type="score"), "All.\nScore.\nAll again.\nEnd.\n")
        self.assertEqual(skill_for(text, instance_type="generator"), "All.\nAll again.\nAlgo.\nAlgo again.\nEnd.\n")
        self.assertEqual(skill_for(text, instance_type="selector"),
                         "All.\nAll again.\nAlgo.\nReads a score.\nAlgo again.\nEnd.\n")

    def test_the_older_style_still_reads(self):
        text = "All.\n<!-- algo -->\nAlgo.\n<!-- score -->\nScore.\n<!-- both -->\nAll again.\n"
        self.assertEqual(skill_for(text, "algo"), "All.\nAlgo.\nAll again.\n")
        self.assertEqual(skill_for(text, "score"), "All.\nScore.\nAll again.\n")

    def test_what_a_file_leaves_open_is_closed_at_its_end(self):
        self.assertEqual(closed("A\n<!-- algo -->\nB\n<!-- transformer -->\nC\n<!-- verbose -->\nD\n"),
                         "A\n<!-- algo -->\nB\n<!-- transformer -->\nC\n<!-- verbose -->\nD\n"
                         "<!-- /verbose -->\n<!-- /transformer -->\n<!-- /algo -->\n")
        self.assertEqual(closed("A\n<!-- score -->\nB\n<!-- /score -->\n"), "A\n<!-- score -->\nB\n<!-- /score -->\n")

    def test_the_shipped_skill_closes_what_it_opens(self):
        self.assertEqual(closed(read_skill(SKILL_PATH)), read_skill(SKILL_PATH))
        self.assertNotIn("<!-- both -->", read_skill(SKILL_PATH))

    def test_compiled_file_has_a_header_the_model_never_reads(self):
        self.skill("analysis", "Analyse first.")
        build(self.pg, "", ["core-algorithmic", "analysis"])
        with open(os.path.join(self.pg, COMPILED), encoding="utf-8") as f:
            written = f.read()
        self.assertTrue(written.startswith("<!-- compiled"))
        self.assertIn("analysis", written.split("-->")[0])
        self.assertFalse(read_compiled(self.pg).startswith("<!-- compiled"))
        self.assertTrue(skill_for(read_compiled(self.pg)).startswith(skill_for(read_skill(SKILL_PATH)).strip()))


if __name__ == "__main__":
    unittest.main()
