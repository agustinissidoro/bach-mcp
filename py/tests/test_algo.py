"""Tests for the algorithm layer: pitch names in Max and Python, send_algorithm, and the
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

from bach_mcp.tools import algo_tools  # noqa: E402
from bach_mcp.bridge.protocol import words as split  # noqa: E402
from bach_mcp.tools.algo_tools import check_algorithm, register_algo_tools  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402
from bach_mcp.tools.session import Target, serve_targets  # noqa: E402
from bach_mcp.music.pitch import cents_to_name, name_to_cents  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
UNITS_JS = os.path.join(REPO, "max", "bach-mcp", "javascript", "algorithmic_core_library", "bachmcp.lib.units.js")
SKILL = os.path.join(REPO, "py", "bach_mcp", "prompt", "BACH_SKILL.md")
EXAMPLES = os.path.join(REPO, "max", "bach-mcp", "algorithms", "examples")
NODE = shutil.which(os.getenv("BACH_NODE") or "node")

needs_node = unittest.skipUnless(NODE, "Node.js is not installed")


@needs_node
class PitchNameTests(unittest.TestCase):
    """The library's pitch names (bachmcp.lib.units.js, in Max) are the pitch tools' (music/pitch.py)."""

    def test_same_names_both_ways(self):
        cents = list(range(1200, 12701, 7)) + [6050, 6049, 5950, 5951, 6012.5, 6933]
        names = ["Db4", "F#5", "E4-14", "C4+50", "Bb3", "F##4", "Gbb4", "A4+12.5", "H4", "db4"]
        program = """
          const U = require(process.argv[1]);
          const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
          process.stdout.write(JSON.stringify([input.cents.map(U.centsToName), input.names.map(U.nameToCents)]));
        """
        done = subprocess.run([NODE, "-e", program, UNITS_JS], input=json.dumps({"cents": cents, "names": names}),
                              capture_output=True, text=True, check=True)
        js_names, js_cents = json.loads(done.stdout)
        self.assertEqual(js_names, [cents_to_name(c) for c in cents])
        self.assertEqual(js_cents, [name_to_cents(n) for n in names])


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class FakeBridge:
    """Stands in for Max: an instance answers a load the way the patch does (algo_loaded /
    algo_error), and the server patch writes buffer.json when asked (server write_buffer)."""

    def __init__(self, rolls="", answer="loaded", roll=None):
        self.sent = []
        self.queue = []
        self.rolls = rolls
        self.answer = answer
        self.roll = roll

    def send(self, message):
        self.sent.append(message)
        name, command, *args = split(message)
        if name == "server" and command == "write_buffer" and self.roll is not None:
            from bach_mcp.bridge import buffer
            with open(buffer.BUFFER_FILE, "w", encoding="utf-8") as f:
                f.write(self.roll)
            self.queue.append("server buffer_done")
        if self.answer and command == "load_algo":
            reply = {"loaded": f"{name} algo_loaded {args[0]} 12 1",
                     "error": f'{name} algo_error "something went wrong"'}[self.answer]
            self.queue += ["other algo_loaded other.js 1 1", f"{name} algo_done 1 1", reply]
        return True

    def flush(self):
        self.queue.clear()

    def receive(self, timeout_seconds=0.0):
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


class PlaygroundTest(unittest.TestCase):
    """The tools serve one instance of a playground, as the hub would have them."""

    def setUp(self):
        self.folder = prepare(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.target = Target("turn", "generator", self.folder)
        serve_targets(lambda: self.target)
        self.addCleanup(serve_targets, None)
        from bach_mcp.bridge import buffer
        saved, buffer.BUFFER_FILE = buffer.BUFFER_FILE, os.path.join(self.folder, "buffer.json")
        self.addCleanup(setattr, buffer, "BUFFER_FILE", saved)
        timeout, algo_tools._CHECK_TIMEOUT_SECONDS = algo_tools._CHECK_TIMEOUT_SECONDS, 3.0
        self.addCleanup(setattr, algo_tools, "_CHECK_TIMEOUT_SECONDS", timeout)

    def tool(self, bridge):
        mcp = FakeMCP()
        register_algo_tools(mcp, bridge, NODE)
        return mcp.tools["send_algorithm"]


@needs_node
class SendAlgorithmTests(PlaygroundTest):
    def setUp(self):
        super().setUp()
        self.bridge = FakeBridge(self.target.scores)
        self.send = self.tool(self.bridge)
        self.history = os.path.join(self.folder, "algorithms", ".history")

    def test_a_good_file_is_saved_loaded_and_described(self):
        reply = self.send(code=GOOD)
        path = os.path.join(self.folder, "algorithms", "turn.js")
        self.assertTrue(reply.startswith("OK. Algorithm saved as algorithms/turn.js and sent to Max (turn)"), reply)
        self.assertIn("times: slider 2..40 = 8", reply)
        self.assertIn("step: slider 50..400 mc = 200", reply)
        self.assertIn("Checked in 5 runs", reply)
        self.assertIn("voice 1 (Flute): 8 notes", reply)
        self.assertEqual(self.bridge.sent, ["turn load_algo turn.js"])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), GOOD)

    def test_replacing_keeps_the_previous_version(self):
        self.send(code=GOOD)
        self.send(code=GOOD.replace("value: 8", "value: 9"))
        self.assertEqual(len([h for h in os.listdir(self.history) if h.startswith("turn-")]), 1)
        self.send(code=GOOD.replace("value: 8", "value: 9"))
        self.assertEqual(len([h for h in os.listdir(self.history) if h.startswith("turn-")]), 1,
                         "an unchanged file is not kept twice")

    def test_errors_load_nothing_and_say_where(self):
        cases = [
            (GOOD.replace("const s = score();", "const s = score(;"), "ERROR in turn.js line 7: syntax error"),
            (GOOD.replace("6000 +", "missing +"), "missing is not defined"),
            (GOOD.replace("range: [2, 40]", "range: [2, 40000]"),
             "more than 20000 notes (40000) (with times = 40000 (its maximum))"),
            (GOOD.replace('type: "slider", range: [50, 400]', 'type: "slider"'), '"range" must be [low, high]'),
            ("const params = {}; function generate() { while (true) {} }", "did not finish"),
        ]
        for code, expected in cases:
            reply = self.send(code=code)
            self.assertTrue(reply.startswith("ERROR"), reply)
            self.assertIn(expected, reply)
            self.assertIn("Nothing was loaded", reply)
        self.assertEqual(self.bridge.sent, [])
        self.assertFalse(os.path.exists(os.path.join(self.folder, "algorithms", "turn.js")))
        self.assertEqual(os.listdir(self.history), [], "no draft is left behind")

    def test_empty_code(self):
        self.assertIn("code is empty", self.send(code="  "))

    def test_the_instance_type_decides_what_is_taken(self):
        self.assertIn("turn is a generator: it makes music from nothing. Write function produce(p)",
                      self.send(code=TRANSFORMER))
        self.target = Target("turn", "writer", self.folder)
        self.assertIn("turn is a writer: it takes notes (write_score)", self.send(code=GOOD))
        self.target = Target("turn", "selector", self.folder)
        self.assertIn("turn is a selector: it picks notes of the score in its roll", self.send(code=GOOD))
        self.target = Target("turn", "transformer", self.folder)
        self.assertIn("turn is a transformer: it changes the score in its roll", self.send(code=GOOD))
        self.assertEqual(self.bridge.sent, [])

    def test_the_load_waits_for_no_answer(self):
        self.bridge.answer = None
        self.assertIn('and sent to Max (turn)', self.send(code=GOOD))

TRANSFORMER = """// move every note
const params = { shift: { type: "slider", range: [-1200, 1200], value: 100, unit: "mc" } };
function transform(source, p) {
  const out = copy(source);
  eachNote(out, (n) => { n.pitch += p.shift; });
  return out;
}
"""
ROLL = json.dumps({"header": {"clefs": ["G"]}, "voices": [{"chords": [
    {"onset": 0, "notes": [{"pitch": 6000, "dur": 500, "vel": 100, "flag": 0}], "flag": 0},
    {"onset": 1000, "notes": [{"pitch": 6200, "dur": 500, "vel": 100, "flag": 0}], "flag": 0}], "flag": 0}]})


@needs_node
class TransformerTests(PlaygroundTest):
    def setUp(self):
        super().setUp()
        self.target = Target("shift", "transformer", self.folder)

    def send(self, bridge, code=TRANSFORMER):
        return self.tool(bridge)(code=code)

    def test_checked_on_the_score_in_the_roll(self):
        bridge = FakeBridge(self.target.scores, roll=ROLL)
        reply = self.send(bridge)
        self.assertIn("Transformer, checked on the score in the roll (2 notes)", reply)
        self.assertIn("pitch 6100-6300", reply)
        self.assertEqual(bridge.sent, ["server write_buffer", "shift load_algo shift.js"])
        self.assertEqual(os.listdir(os.path.join(self.folder, "algorithms", ".history")), [], "no draft is left")

    def test_checked_on_the_built_in_score_without_a_roll(self):
        from bach_mcp.bridge.buffer import ServerBuffer
        original = ServerBuffer.fetch
        ServerBuffer.fetch = lambda self, timeout_seconds=5.0: original(self, 0.1)
        self.addCleanup(setattr, ServerBuffer, "fetch", original)
        reply = self.send(FakeBridge(self.target.scores, roll=None))
        self.assertIn("checked on a built-in test score: the roll is empty or Max did not hand it over (14 notes)", reply)

    def test_a_transformer_that_fails_on_the_source(self):
        reply = self.send(FakeBridge(self.target.scores, roll=ROLL),
                          TRANSFORMER.replace("n.pitch += p.shift", "n.pitch = n.missing.x"))
        self.assertTrue(reply.startswith("ERROR in shift.js line 5: error in transform"), reply)


SELECTOR = """// the notes above a floor
const params = { floor: { type: "slider", range: [1200, 12700], value: 6100, unit: "mc" } };
function select(source, p) {
  const out = [];
  eachNote(source, (n) => { if (n.pitch > p.floor) out.push(n); });
  return out;
}
"""


@needs_node
class SelectorTests(PlaygroundTest):
    def setUp(self):
        super().setUp()
        self.target = Target("picker", "selector", self.folder)

    def test_checked_on_the_score_in_the_roll(self):
        bridge = FakeBridge(self.target.scores, roll=ROLL)
        reply = self.tool(bridge)(code=SELECTOR)
        self.assertIn("Selector, checked on the score in the roll (2 notes)", reply)
        self.assertIn("it picks 1 notes ([voice chord note]): [1 2 1]", reply)
        self.assertEqual(bridge.sent, ["server write_buffer", "picker load_algo picker.js"])

    def test_a_selector_must_select(self):
        reply = self.tool(FakeBridge(self.target.scores, roll=ROLL))(code=TRANSFORMER)
        self.assertIn("picker is a selector: it picks notes", reply)


@needs_node
class LibraryTests(unittest.TestCase):
    def test_example_algorithms_pass_the_check(self):
        folder = EXAMPLES
        files = sorted(f for f in os.listdir(folder) if f.endswith(".js"))
        self.assertGreaterEqual(len(files), 2)
        for name in files:
            result = check_algorithm(os.path.join(folder, name), node=NODE)
            self.assertTrue(result.get("ok"), f"{name}: {result}")
            normalize_score(result["score"])

    def test_the_skill_examples_are_the_example_algorithms(self):
        with open(SKILL, encoding="utf-8") as f:
            blocks = re.findall(r"```js\n(.*?)```", f.read(), re.S)
        self.assertEqual(len(blocks), 3)
        for block, name in zip(blocks, ("drift.js", "transpose-phrases.js", "answer-phrases.js")):
            with open(os.path.join(EXAMPLES, name), encoding="utf-8") as f:
                self.assertEqual(f.read(), block, name)

    def test_the_skill_names_every_library_function(self):
        program = "process.stdout.write(JSON.stringify(require(process.argv[1]).LIBRARY))"
        index = os.path.join(REPO, "max", "bach-mcp", "javascript", "algorithmic_core_library", "bachmcp.lib.index.js")
        names = json.loads(subprocess.run([NODE, "-e", program, index], capture_output=True, text=True, check=True).stdout)
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
