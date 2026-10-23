"""Tests of compose.py, kept with it in deprecated/. Not part of the suite (py/tests)."""

import unittest

from bach_mcp.compose import euclid, run_program, scale
from bach_mcp.translate import ScoreError


class ComposeTests(unittest.TestCase):
    """compose.py is not exposed to the model; it still thinks in note names and beats."""

    def test_helpers(self):
        self.assertEqual(scale("C4", "major", 8), [60, 62, 64, 65, 67, 69, 71, 72])
        self.assertEqual(euclid(3, 8), [1, 0, 0, 1, 0, 0, 1, 0])

    def test_program_builds_voices(self):
        raw = run_program(
            "voice(2, 'Bass')\n"
            "for p in scale('D4', 'dorian', 4): note(p, 0.5)\n"
            "rest(1, voice=2)\nnote('D2', 2, voice=2)\n", bpm=100)
        self.assertEqual(sum(len(v["notes"]) for v in raw["voices"]), 5)
        self.assertEqual(raw["voices"][1]["name"], "Bass")
        self.assertEqual(raw["voices"][1]["notes"][0]["t"], 1)
        self.assertEqual(raw["voices"][0]["notes"][3]["t"], 1.5)

    def test_seed_is_reproducible(self):
        code = "for i in range(8): note(rnd.choice(scale('C4', 'pentatonic', 5)), 0.25)"
        self.assertEqual(run_program(code, seed=3), run_program(code, seed=3))

    def test_restrictions_and_errors(self):
        for bad in ("import os", "note.__globals__", "open('x')", "while True: pass", "x = 1"):
            with self.assertRaises(ScoreError, msg=bad):
                run_program(bad)
        with self.assertRaises(ScoreError) as ctx:
            run_program("note('C4')\nnote(undefined_name)")
        self.assertIn("line 2", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
