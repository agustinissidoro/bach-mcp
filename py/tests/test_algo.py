"""Tests for the algorithm layer: the JS translator against translate.py, send_algorithm, and the
JavaScript tests of the Max objects (py/tests/js, run with Node). Run: python -m unittest discover -s py/tests"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp import algo_tools  # noqa: E402
from bach_mcp.algo_tools import check_algorithm, register_algo_tools  # noqa: E402
from bach_mcp.translate import ScoreError, llll_to_score, normalize_score, score_messages, summarize  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCORE_JS = os.path.join(REPO, "max", "bach-mcp", "javascript", "bach.mcp.score.js")
SKILL = os.path.join(REPO, "py", "bach_mcp", "BACH_SKILL.md")
NODE = shutil.which(os.getenv("BACH_NODE") or "node")

needs_node = unittest.skipUnless(NODE, "Node.js is not installed")


def run_js_translator(scores, dumps):
    """What bach.mcp.score.js makes of the same scores and dumps."""
    program = """
      const S = require(process.argv[1]);
      const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
      const out = { scores: [], dumps: [] };
      for (const score of input.scores) {
        try {
          const c = S.normalizeScore(score);
          out.scores.push({ replace: S.scoreMessages(c), add: S.scoreMessages(c, true), summary: S.summarize(c) });
        } catch (e) {
          out.scores.push({ error: e.message });
        }
      }
      for (const dump of input.dumps) out.dumps.push(S.llllToScore(dump));
      process.stdout.write(JSON.stringify(out));
    """
    done = subprocess.run([NODE, "-e", program, SCORE_JS], input=json.dumps({"scores": scores, "dumps": dumps}),
                          capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def skill_scores():
    with open(SKILL, encoding="utf-8") as f:
        text = f.read()
    out = []
    for block in re.findall(r"```json\n(.*?)```", text, re.S):
        data = json.loads(block)
        out.append(data if "voices" in data else {"voices": [{"chords": [data]}]})
    return out


EDGE_SCORES = [
    {"voices": [{"name": "Violin 1", "chords": [
        {"onset": 0, "dyn": "p<f>p", "text": "sul pont. (molto)", "notes": [{"pitch": 6933.33, "dur": 1000.5}]},
        {"onset": 500, "art": "stacc, ten", "lyric": "ah", "notes": [{"pitch": "6050", "dur": 250, "vel": 300}]},
        {"t": 2000, "dynamic": "sfz", "notes": [{"cents": 3600, "duration": 4000, "glissando": [[1, -1200], [0.5, 200, 2]]}]},
    ]}, {"name": "Cello", "clef": "bass", "chords": []}],
     "markers": [{"onset": 5000, "name": "B section"}, {"onset": 0, "label": "A"}]},
    {"voices": [{"name": "Piano", "chords": [
        {"onset": 3000, "notes": [{"pitch": 2100, "dur": 10}, {"pitch": 10800, "dur": 20, "head": "x"}]},
        {"onset": 0, "dyn": "ffmp", "notes": [{"pitch": 6012.5, "dur": 10}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 60, "dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "notes": [{"dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "dur": 500, "notes": [{"pitch": 6000, "dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "onset": 3}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "colour": "red", "notes": [{"pitch": 6000, "dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "dyn": "loud!", "notes": [{"pitch": 6000, "dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "art": "foo", "notes": [{"pitch": 6000, "dur": 500}]}]}]},
    {"voices": [{"chords": [{"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "gliss": [[0.5, 100]]}]}]}]},
    {"voices": [{"notes": []}]},
    {"voices": []},
]

DUMPS = [
    ("roll [clefs G F] [voicenames Flute nil] "
     "[ [ 0. [ 6000. 500. 100 [slots [20 mf] [22 staccato accent]] 0 ] 0 ] "
     "[ 500. [ 6400. 250. 90 0 ] [ 7300. 125. 60 0 ] 0 ] 0 ] [ 0 ]"),
    "roll [ [ 0. [ Db5 500. 100 0 ] [ Cq5 500. 100 0 ] [ 6050.5 500. 100 0 ] 0 ] 0 ]",
    ("roll [ [ 0. [ 6000. 500. 100 [ slots [ 20 [ [ auto 0 0. ] f > ] [ [ breakpoint 1 0.306341 ] p < ] "
     "[ [ auto 0 1. ] niente = ] ] ] 0 ] 0 ] 0 ]"),
    ("roll [ markers [ 510. [ marker 1 ] none ] [ 2000. `A1 none ] ] "
     "[ [ 688.571 [ 7600. 1276.57 126 [ breakpoints [ 0. 0. 0. 126 ] [ 0.183787 0. 0. 6 ] "
     "[ 0.679181 -200. 0. 127 ] [ 1. 600. 0.5 60 ] ] 0 ] 0 ] "
     "[ 2000. [ 7100. 1049. 100 [ slots [ 24 molto pont. ] [ notehead diam ] "
     "[ articulations port mart trem3 ] [ 5 68 ] ] [ name pippo ] 2 ] 0 ] "
     "[ 4000. [ 6200. 1000. 100 [ breakpoints [ 0. 0. 0. ] [ 1. -1200. 0. ] ] 0 ] 0 ] 0 ]"),
    "roll [ [ 0. [ 6000. 500. 100 [ slots [ 20 [ auto pp < ] [ auto [ ] = ] ] ] 0 ] 0 ] 0 ]",
]


@needs_node
class TranslatorParityTests(unittest.TestCase):
    """bach.mcp.score.js (Max) must write and read exactly what translate.py does."""

    def test_same_messages_summaries_and_errors(self):
        scores = skill_scores() + EDGE_SCORES
        js = run_js_translator(scores, [])["scores"]
        for score, theirs in zip(scores, js):
            try:
                canonical = normalize_score(score)
            except ScoreError as exc:
                self.assertEqual(theirs.get("error"), str(exc), json.dumps(score))
                continue
            self.assertNotIn("error", theirs, json.dumps(score))
            self.assertEqual(theirs["replace"], score_messages(canonical), json.dumps(score))
            self.assertEqual(theirs["add"], score_messages(canonical, add=True))
            self.assertEqual(theirs["summary"], summarize(canonical))

    def test_same_reading_of_bach_dumps(self):
        js = run_js_translator([], DUMPS)["dumps"]
        for dump, theirs in zip(DUMPS, js):
            self.assertEqual(theirs, llll_to_score(dump), dump)


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class FakeBridge:
    """Stands in for Max: answers a load the way the patch does (loaded / error)."""

    def __init__(self, answer="loaded"):
        self.sent = []
        self.queue = []
        self.answer = answer

    def send_info(self, message):
        self.sent.append(message)
        words = message.split(" ", 3)
        if self.answer and words[0] == "algo" and words[2] == "load":
            name = os.path.basename(words[3].strip('"'))
            reply = {"loaded": f"algo_status loaded {words[1]} {name} 12 1",
                     "error": f"algo_status error {words[1]} something went wrong"}[self.answer]
            self.queue += [{"data": "algo_status done other 1 1"}, {"data": reply}]
        return True

    def flush_incoming(self):
        self.queue.clear()

    def wait_for_incoming(self, timeout_seconds=0.0):
        return self.queue.pop(0) if self.queue else None


GOOD = """// a scale that turns around
const params = {
  times: { type: "slider", range: [2, 40], value: 8 },
  step:  { type: "slider", range: [50, 400], value: 200, unit: "mc" },
};
function generate(p) {
  const s = score();
  const v = s.voice("Flute");
  for (let i = 0; i < p.times; i++) v.note(i * 200, 6000 + fold(i * p.step, 0, 1200), 200);
  return s;
}
"""


@needs_node
class SendAlgorithmTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        os.environ["BACH_ALGO_DIR"] = self.folder
        self.addCleanup(os.environ.pop, "BACH_ALGO_DIR", None)
        timeout, algo_tools._CHECK_TIMEOUT_SECONDS = algo_tools._CHECK_TIMEOUT_SECONDS, 3.0
        self.addCleanup(setattr, algo_tools, "_CHECK_TIMEOUT_SECONDS", timeout)
        self.bridge = FakeBridge()
        mcp = FakeMCP()
        register_algo_tools(mcp, self.bridge)
        self.send = mcp.tools["send_algorithm"]

    def test_a_good_file_is_saved_loaded_and_described(self):
        reply = self.send(name="turn", code=GOOD)
        path = os.path.join(self.folder, "turn.js")
        self.assertTrue(reply.startswith(f'OK. Algorithm "turn" saved as {path} and loaded in Max'), reply)
        self.assertIn("times: slider 2..40 = 8", reply)
        self.assertIn("step: slider 50..400 mc = 200", reply)
        self.assertIn("Checked in 5 runs", reply)
        self.assertIn("voice 1 (Flute) clef G: 8 notes", reply)
        self.assertEqual(self.bridge.sent, [f'algo algo load "{path}"'])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), GOOD)

    def test_replacing_keeps_the_previous_version(self):
        self.send(name="turn", code=GOOD)
        self.send(name="turn", code=GOOD.replace("value: 8", "value: 9"))
        history = os.listdir(os.path.join(self.folder, ".history"))
        self.assertEqual(len([h for h in history if h.startswith("turn-")]), 1)
        self.send(name="turn", code=GOOD.replace("value: 8", "value: 9"))
        history = os.listdir(os.path.join(self.folder, ".history"))
        self.assertEqual(len([h for h in history if h.startswith("turn-")]), 1, "an unchanged file is not kept twice")

    def test_errors_load_nothing_and_say_where(self):
        cases = [
            (GOOD.replace("const s = score();", "const s = score(;"), "ERROR in turn.js line 7: syntax error"),
            (GOOD.replace("6000 +", "missing +"), "missing is not defined"),
            (GOOD.replace("range: [2, 40]", "range: [2, 40000]"),
             "more than 20000 notes (with times = 40000 (its maximum))"),
            (GOOD.replace('type: "slider", range: [50, 400]', 'type: "slider"'), '"range" must be [low, high]'),
            (GOOD.replace("6000 + fold", "60 + fold"), "looks like a MIDI note number"),
            ("const params = {}; function generate() { while (true) {} }", "did not finish"),
        ]
        for code, expected in cases:
            reply = self.send(name="turn", code=code)
            self.assertTrue(reply.startswith("ERROR"), reply)
            self.assertIn(expected, reply)
            self.assertIn("Nothing was loaded", reply)
        self.assertEqual(self.bridge.sent, [])
        self.assertFalse(os.path.exists(os.path.join(self.folder, "turn.js")))
        self.assertEqual(os.listdir(os.path.join(self.folder, ".history")), [], "no draft is left behind")

    def test_bad_names_and_empty_code(self):
        self.assertIn("name must start with a letter", self.send(name="../x", code=GOOD))
        self.assertIn("code is empty", self.send(name="x", code="  "))

    def test_what_max_answers_is_reported(self):
        self.bridge.answer = "error"
        self.assertIn("but Max reported an error: something went wrong", self.send(name="turn", code=GOOD))
        self.bridge.answer = None
        self.assertIn("which did not confirm (is there a bach.mcp.algo named \"strings\"?)",
                      self.send(name="turn", code=GOOD, runner="strings"))


@needs_node
class LibraryTests(unittest.TestCase):
    def test_example_algorithms_pass_the_check(self):
        folder = os.path.join(REPO, "algorithms")
        files = sorted(f for f in os.listdir(folder) if f.endswith(".js"))
        self.assertGreaterEqual(len(files), 2)
        for name in files:
            result = check_algorithm(os.path.join(folder, name))
            self.assertTrue(result.get("ok"), f"{name}: {result}")
            normalize_score(result["score"])

    def test_the_skill_example_is_the_drift_algorithm(self):
        with open(SKILL, encoding="utf-8") as f:
            block = re.findall(r"```js\n(.*?)```", f.read(), re.S)[0]
        with open(os.path.join(REPO, "algorithms", "drift.js"), encoding="utf-8") as f:
            self.assertEqual(f.read(), block)

    def test_the_skill_names_every_library_function(self):
        program = "process.stdout.write(JSON.stringify(require(process.argv[1]).LIBRARY))"
        core = os.path.join(REPO, "max", "bach-mcp", "javascript", "bach.mcp.core.js")
        names = json.loads(subprocess.run([NODE, "-e", program, core], capture_output=True, text=True, check=True).stdout)
        with open(SKILL, encoding="utf-8") as f:
            prose = re.sub(r"```.*?```", "", f.read(), flags=re.S)
        spans = " ".join(re.findall(r"`([^`\n]+)`", prose))
        for name in names:
            if name != "Math":
                self.assertRegex(spans, rf"\b{name}\b", f"the skill does not mention {name}")


@needs_node
class MaxObjectTests(unittest.TestCase):
    def test_javascript_tests(self):
        done = subprocess.run([NODE, "--test", os.path.join(HERE, "js", "*.test.js")],
                              capture_output=True, text=True, cwd=REPO)
        self.assertEqual(done.returncode, 0, done.stdout[-3000:] + done.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
