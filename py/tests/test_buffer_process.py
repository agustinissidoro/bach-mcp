"""Tests for offline audio: send_buffer_process (buffer_process_tools.py), the worker and the hub's runner
(audio_processing/). Run: python -m unittest discover -s py/tests"""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np  # noqa: E402

from bach_mcp.audio_processing.runner import ProcessRunner, value  # noqa: E402
from bach_mcp.bridge.protocol import line, words  # noqa: E402
from bach_mcp.prompt.modes import MODE_TOOLS, TYPE_MODE, split_prefix  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402
from bach_mcp.tools.buffer_process_tools import register_buffer_process_tools, run_check, serve_runner, static_check  # noqa: E402
from bach_mcp.tools.session import Target, serve_targets  # noqa: E402
from bach_mcp.utilities.shmbuffer import NoShmBuffer, ShmBuffer  # noqa: E402

GAIN = """# Changes the level and flips the channels.
import numpy as np
import audio_core as ac

def process(x, sr, p):
    y = x[:, ::-1] * ac.db(p["gain_db"])
    return y
"""
GAIN_PARAMS = {"gain_db": {"type": "slider", "range": [-24, 6], "value": -6, "unit": "dB"}}

SPECTRAL = """# Keeps only the strongest bins of every frame.
import numpy as np
import audio_core as ac

def process(x, sr, p):
    S, f, t = ac.stft(x, sr)
    mag = np.abs(S)
    keep = mag >= np.quantile(mag, 1 - p["keep"], axis=1, keepdims=True)
    return ac.istft(S * keep, sr, len(x))
"""
SPECTRAL_PARAMS = {"keep": {"type": "slider", "range": [0.01, 1], "value": 0.1}}


def shm_name():
    return "t" + uuid.uuid4().hex[:10]


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class FakeBridge:
    def __init__(self):
        self.sent = []

    def flush(self):
        pass

    def send(self, text):
        self.sent.append(text)
        return True


class ModeTests(unittest.TestCase):
    def test_process_has_its_own_mode_and_tool(self):
        self.assertEqual(TYPE_MODE["buffer"], "buffer")
        self.assertEqual(MODE_TOOLS["buffer"], ("send_buffer_process",))
        for mode in ("score", "algo", "gen"):
            self.assertNotIn("send_buffer_process", MODE_TOOLS[mode])
        self.assertEqual(split_prefix("/buffer a reverb"), ("buffer", "a reverb"))

    def test_panel_values(self):
        self.assertEqual(value(["0.5"]), 0.5)
        self.assertEqual(value(["3"]), 3)
        self.assertEqual(value(["up"]), "up")
        self.assertEqual(value(["1", "2.5"]), [1, 2.5])


class StaticTests(unittest.TestCase):
    def refused(self, code, saying, declared=()):
        found = static_check(code, set(declared))
        self.assertFalse(found["ok"], code)
        self.assertIn(saying, found["error"])
        return found

    def test_a_good_file(self):
        found = static_check(GAIN, {"gain_db"})
        self.assertTrue(found["ok"], found)
        self.assertEqual(found["description"], "Changes the level and flips the channels.")

    def test_what_is_refused(self):
        body = "def process(x, sr, p):\n    return x\n"
        self.refused(body, "opens with a # comment")
        self.refused("# x\ndef process(x, sr, p)\n    return x\n", "SyntaxError")
        self.refused("# x\ndef run(x, sr, p):\n    return x\n", "no top-level function process")
        self.refused("# x\ndef process(x, sr):\n    return x\n", "three arguments")
        self.refused("# x\nimport os\n" + body, "import os")
        self.refused("# x\nfrom subprocess import run\n" + body, "import subprocess")
        self.refused("# x\n" + body + "f = open('a')\n", "open is not allowed")
        self.refused("# x\n" + body + "k = ().__class__.__subclasses__()\n", "__subclasses__ is not allowed")
        found = self.refused("# x\ndef process(x, sr, p):\n    return x * p['gain']\n", "p['gain'] is read but not declared")
        self.assertEqual(found["line"], 3)
        self.refused("# x\ndef process(x, sr, q):\n    return x * q.get('mix', 1)\n", "q['mix']")


class CheckTests(unittest.TestCase):
    def check(self, code, params=None):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "x.py")
            with open(path, "w", encoding="utf-8") as f:
                f.write(code)
            declared = os.path.join(folder, "x.json")
            with open(declared, "w", encoding="utf-8") as f:
                json.dump(params or {}, f)
            return run_check(path, declared)

    def test_it_runs_at_values_and_slider_edges(self):
        result = self.check(GAIN, GAIN_PARAMS)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["runs"], 3)
        self.assertEqual((result["frames"], result["channels"], result["sr"]), (96000, 2, 48000.0))

    def test_spectral_and_libraries(self):
        self.assertTrue(self.check(SPECTRAL, SPECTRAL_PARAMS)["ok"])
        board = ("# A plate.\nimport pedalboard\n\ndef process(x, sr, p):\n"
                 "    return pedalboard.Pedalboard([pedalboard.Reverb(room_size=p['size'])])(x.T.copy(), sr).T\n")
        self.assertTrue(self.check(board, {"size": {"type": "slider", "range": [0, 1], "value": 0.5}})["ok"])

    def test_errors_carry_the_line(self):
        result = self.check("# x\nimport numpy as np\n\ndef process(x, sr, p):\n    return np.zeros((10, 2)) / undefined\n")
        self.assertFalse(result["ok"])
        self.assertIn("NameError", result["error"])
        self.assertEqual(result["line"], 5)

    def test_what_is_not_samples(self):
        self.assertIn("None", self.check("# x\ndef process(x, sr, p):\n    pass\n")["error"])
        self.assertIn("transpose", self.check("# x\ndef process(x, sr, p):\n    return x.T\n")["error"])
        result = self.check("# x\nimport numpy as np\ndef process(x, sr, p):\n    return x * np.inf\n")
        self.assertIn("NaN or infinite", result["error"])
        edge = self.check("# x\ndef process(x, sr, p):\n    return x / p['d']\n",
                          {"d": {"type": "slider", "range": [0, 1], "value": 0.5}})
        self.assertFalse(edge["ok"])
        self.assertIn("with d = 0", edge["error"])

    def test_warnings(self):
        result = self.check("# x\ndef process(x, sr, p):\n    return x * 0\n")
        self.assertTrue(result["ok"])
        self.assertIn("silent", result["warnings"][0])

    def test_prints_do_not_break_the_answer(self):
        self.assertTrue(self.check("# x\nprint('hello')\ndef process(x, sr, p):\n    print(x.shape)\n    return x\n")["ok"])


class Memory(unittest.TestCase):
    def memory(self, frames=4800, channels=2, sr=48000.0):
        name = shm_name()
        buf = ShmBuffer.create(name, frames, channels, sr)
        self.addCleanup(buf.unlink)
        return name, buf

    def cleanup_name(self, name):
        def gone():
            try:
                ShmBuffer(name).unlink()
            except NoShmBuffer:
                pass
        self.addCleanup(gone)


class RunnerTests(Memory):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.root = prepare(self.folder)
        self.said = []
        self.done = threading.Event()
        self.runner = ProcessRunner(self.say, lambda: self.root, settle=0.01, timeout=60)
        self.addCleanup(self.runner.close)

    def say(self, *said):
        self.said.append(line(*said))
        if said[1] in ("processed", "process_error", "process_stopped"):
            self.done.set()

    def write(self, name, code, params):
        with open(os.path.join(self.root, "processes", f"{name}.py"), "w", encoding="utf-8") as f:
            f.write(code)
        with open(os.path.join(self.root, "processes", f"{name}.json"), "w", encoding="utf-8") as f:
            json.dump({"description": "x", "params": params}, f)

    def wait(self):
        self.assertTrue(self.done.wait(30), self.said)
        self.done.clear()
        return self.said[-1]

    def test_source_to_target(self):
        source, buf = self.memory()
        buf.array[:, 0] = 0.5
        buf.array[:, 1] = 0.25
        target = shm_name()
        self.cleanup_name(target)
        self.write("amp", GAIN, GAIN_PARAMS)
        self.runner.set_source("amp", source)
        self.runner.set_target("amp", target)
        self.runner.run("amp")
        last = self.wait()
        self.assertEqual(words(last)[:2], ["amp", "processed"], self.said)
        self.assertEqual(words(last)[3:], ["4800", "2", "48000.0"])
        out = ShmBuffer(target)
        np.testing.assert_allclose(out.array[0], [0.25 * 10 ** (-6 / 20), 0.5 * 10 ** (-6 / 20)], rtol=1e-5)
        self.assertIn("amp processing", self.said)

        self.runner.set_param("amp", "gain_db", ["0"])  # a panel change runs it again
        self.wait()
        np.testing.assert_allclose(ShmBuffer(target).array[0], [0.25, 0.5], rtol=1e-6)

    def test_a_changed_length_resizes_the_target(self):
        source, buf = self.memory(frames=1000, channels=1)
        target, small = self.memory(frames=10, channels=1)
        self.write("x", "# x\nimport numpy as np\ndef process(x, sr, p):\n    return np.ones((3000, 2)) * 0.1, 22050\n", {})
        self.runner.set_source("x", source)
        self.runner.set_target("x", target)
        self.runner.run("x")
        self.assertIn("processed", self.wait())
        out = ShmBuffer(target)
        self.assertEqual((out.frames, out.channels, out.sr), (3000, 2, 22050.0))

    def test_errors_and_missing_things(self):
        self.runner.run("none")
        self.assertIn("no processes/none.py yet", self.wait())
        source, _ = self.memory()
        target = shm_name()
        self.cleanup_name(target)
        self.write("bad", "# x\ndef process(x, sr, p):\n    return 1 / 0\n", {})
        self.runner.set_source("bad", source)
        self.runner.set_target("bad", target)
        self.runner.run("bad")
        self.assertIn("process_error \"line 3: ZeroDivisionError", self.wait())
        self.write("bad", "# x\ndef process(x, sr, p):\n    return x\n", {})  # edited: the worker loads it again
        os.utime(os.path.join(self.root, "processes", "bad.py"), (time.time() + 5, time.time() + 5))
        self.runner.run("bad")
        self.assertIn("processed", self.wait())

    def test_no_source_gives_no_frames(self):
        target = shm_name()
        self.cleanup_name(target)
        self.write("gen", "# x\nimport numpy as np\ndef process(x, sr, p):\n    return np.full((len(x) + 100, 1), 0.1)\n", {})
        self.runner.set_source("gen", shm_name())
        self.runner.set_target("gen", target)
        self.runner.run("gen")
        self.assertIn("processed", self.wait())
        self.assertTrue(any("got 0 frames" in s for s in self.said), self.said)

    def test_stop_ends_a_run(self):
        source, _ = self.memory()
        self.write("slow", "# x\nimport time\ndef process(x, sr, p):\n    time.sleep(30)\n    return x\n", {})
        self.runner.set_source("slow", source)
        self.runner.run("slow")
        deadline = time.time() + 10
        while "slow processing" not in self.said and time.time() < deadline:
            time.sleep(0.01)
        time.sleep(0.3)
        self.runner.stop("slow")
        self.assertEqual(self.wait(), "slow process_stopped")


class ToolTests(Memory):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.root = prepare(self.folder)
        self.mcp, self.bridge = FakeMCP(), FakeBridge()
        register_buffer_process_tools(self.mcp, self.bridge)
        self.loaded = []
        serve_runner(type("R", (), {"loaded": lambda _, name: self.loaded.append(name)})())
        self.addCleanup(serve_runner, None)
        self.addCleanup(serve_targets, None)

    def send(self, code, params=None, instance_type="buffer"):
        serve_targets(lambda: Target("amp", instance_type, self.root))
        return self.mcp.tools["send_buffer_process"](code, params)

    def test_send_buffer_process_saves_loads_and_runs(self):
        result = self.send(GAIN, json.dumps(GAIN_PARAMS))
        self.assertTrue(result.startswith("OK."), result)
        self.assertIn("3 runs", result)
        with open(os.path.join(self.root, "processes", "amp.json"), encoding="utf-8") as f:
            panel = json.load(f)
        self.assertEqual(panel["description"], "Changes the level and flips the channels.")
        self.assertEqual(panel["params"], GAIN_PARAMS)
        self.assertEqual(self.bridge.sent, ["amp load_buffer_process amp.json"])
        self.assertEqual(self.loaded, ["amp"])

        self.send(SPECTRAL, SPECTRAL_PARAMS)  # the first version is kept
        self.assertEqual(len([f for f in os.listdir(os.path.join(self.root, "processes", ".history")) if f.endswith(".py")]), 1)

    def test_refusals_keep_the_old_file(self):
        self.send(GAIN, GAIN_PARAMS)
        result = self.send("# x\ndef process(x, sr, p):\n    return x[0, 0, 0]\n")
        self.assertTrue(result.startswith("ERROR in amp.py line 3"), result)
        self.assertIn("Nothing was loaded", result)
        with open(os.path.join(self.root, "processes", "amp.py"), encoding="utf-8") as f:
            self.assertEqual(f.read(), GAIN)
        self.assertIn("is a synth instance", self.send(GAIN, GAIN_PARAMS, "synth"))
        self.assertIn("params must be", self.send(GAIN, {"gain_db": 3}))


class HubTests(Memory):
    def test_max_runs_a_process_through_the_hub(self):
        from bach_mcp.chat.hub import Hub
        from bach_mcp.config import Config
        from bach_mcp.utilities.status import Status

        class Bridge:
            def __init__(self):
                self.sent, self.handler = [], None

            def send(self, text):
                self.sent.append(text)
                return True

            def on_line(self, handler):
                self.handler = handler

        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        bridge = Bridge()
        hub = Hub(bridge, Status(Config(), bridge, "run"))
        self.addCleanup(hub.close)
        bridge.handler(f"set_playground {folder}")
        with open(os.path.join(hub.playground, "processes", "amp.py"), "w", encoding="utf-8") as f:
            f.write(GAIN)
        with open(os.path.join(hub.playground, "processes", "amp.json"), "w", encoding="utf-8") as f:
            json.dump({"description": "x", "params": GAIN_PARAMS}, f)
        source, buf = self.memory(frames=100)
        buf.array[:] = 1.0
        target = shm_name()
        self.cleanup_name(target)
        for text in (f"amp buffer_process_source {source}", f"amp buffer_process_target {target}", "amp buffer_process_param gain_db 0"):
            self.assertTrue(bridge.handler(text))
        deadline = time.time() + 30
        while not any(s.startswith("amp processed") for s in bridge.sent) and time.time() < deadline:
            time.sleep(0.02)
        self.assertTrue(any(s.startswith("amp processed 0") or s.startswith("amp processed") for s in bridge.sent), bridge.sent)
        np.testing.assert_allclose(ShmBuffer(target).array, np.ones((100, 2)))
        self.assertFalse(bridge.handler("amp algo_loaded"))  # what the hub does not know stays for the tools
        for generic in ("amp run", "amp param gain_db 0"):  # an algorithm panel's words, not the hub's
            self.assertFalse(bridge.handler(generic))
        self.assertTrue(bridge.handler("amp buffer_process_stop"))


if __name__ == "__main__":
    unittest.main()
