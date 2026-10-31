"""What Bach tells Max about itself: answers to bach, warnings, and a real UDP round trip."""

import os
import shutil
import socket
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from bach_mcp.bridge.max import MaxBridge, line  # noqa: E402
from bach_mcp.bridge.udp import decode, encode  # noqa: E402
from bach_mcp.config import Config, load_config  # noqa: E402
from bach_mcp.utilities.download import DownloadJob, Plan, load_catalog  # noqa: E402
from bach_mcp.model.backends import free_port  # noqa: E402
from bach_mcp.utilities.status import Status, settings  # noqa: E402


class Recorder:
    """A bridge that keeps what Bach says to Max, as Max would receive it."""

    def __init__(self):
        self.said = []

    def say(self, *words):
        self.said.append(decode(encode(line(*words))))
        return True

    def stop(self):
        self.stopped = True


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.max = Recorder()
        self.status = Status(Config(), self.max, "run")

    def ask(self, what):
        self.max.said.clear()
        self.status.answer(f"bach {what}")
        return self.max.said

    def test_unasked_only_status_1_after_starting_and_0_last(self):
        self.status.set("no_model", message="no model: set one")
        self.status.set("loading", model="Qwen (mlx)")
        self.assertEqual(self.max.said, [], "state changes are not sent unasked")
        self.status.started()
        self.status.off()
        self.status.off()
        self.assertEqual(self.max.said, ["server status 1", "server status 0"], "0 once, last")

    def test_asked_status_gives_the_state_too(self):
        self.status.set("no_model", message="no model: set one")
        self.assertEqual(self.ask("status"), ["server status 1", 'server warning no model: set one'])
        self.status.set("loading", model="Qwen (mlx)")
        self.assertEqual(self.ask("status"), ["server status 1"], "no model line until it is loaded")
        self.status.set("ready", model="Qwen (mlx)")
        self.assertEqual(self.ask("status")[1:], ['server model Qwen (mlx)'])
        self.assertTrue(self.status.ready)

    def test_texts_arrive_as_plain_words_without_commas_or_quotes(self):
        self.status.warning('a "quoted" text, with commas; and a semicolon')
        self.assertEqual(self.max.said[-1], "server warning a quoted text with commas and a semicolon")

    def test_settings_one_line_each_then_the_count(self):
        said = self.ask("settings")
        self.assertIn("server model.runtime -", said)
        self.assertIn("server generation.temperature 0.7", said)
        self.assertIn("server chat.docs 1", said)
        self.assertIn("server model.model -", said)
        self.assertEqual(said[-1], f"server end settings {len(settings(Config()))}")

    def test_models_end_with_their_count(self):
        said = self.ask("models")
        self.assertTrue(said[-1].startswith("server end models "))

    def test_the_catalogue(self):
        said = self.ask("catalog")
        self.assertTrue(said[0].startswith("server catalog qwen3.8-27b mlx 16.1 "), said[0])
        self.assertIn("mlx-community/Qwen3.8-27B-4bit", said[0])
        self.assertEqual(said[-1], f"server end catalog {len(load_catalog())}")

    def test_help_ping_and_an_unknown_request(self):
        self.assertEqual(self.ask("help"), ["server help status settings models catalog download_model download_stop "
                                            "quit help ping"])
        self.assertEqual(self.ask("ping"), ["server pong"])
        self.assertIn("unknown request", self.ask("dance")[0])

    def test_claudes_door(self):
        status = Status(Config(), self.max, "serve")
        self.assertEqual(status.state, "claude")


class DownloadTests(unittest.TestCase):
    """download_model from Max, with a stand-in download process (no network)."""

    def setUp(self):
        from test_models import FAKE_DOWNLOAD
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        folder = self.folder

        class FakeJob(DownloadJob):
            def __init__(self, plan, **kwargs):
                super().__init__(plan, every=0.05, folder=folder, log_path=os.path.join(folder, "download.log"),
                                 command=[sys.executable, "-c", FAKE_DOWNLOAD, os.path.join(folder, plan.name), "ok"],
                                 **kwargs)

        for name, value in (("DownloadJob", FakeJob),
                            ("make_plan", lambda spec: Plan(spec, "Fake-4bit", "mlx", 1000, repo="user/Fake-4bit"))):
            patcher = mock.patch(f"bach_mcp.utilities.status.{name}", value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.toml = os.path.join(self.folder, "bachmcp.toml")
        with open(self.toml, "w", encoding="utf-8") as f:
            f.write('[model]\nmodel = ""  # the model\n')
        self.max = Recorder()
        self.status = Status(load_config(self.toml), self.max, "run")

    def wait_for(self, prefix):
        deadline = time.time() + 10
        while not any(s.startswith(prefix) for s in self.max.said):
            self.assertLess(time.time(), deadline, self.max.said)
            time.sleep(0.02)

    def test_start_progress_done_and_use(self):
        self.status.answer("bach download_model fake use")
        self.wait_for("server warning")
        said = self.max.said
        self.assertEqual(said[0], "server download_start Fake-4bit 0")
        progress = [s for s in said if s.startswith("server download_progress ")]
        self.assertGreater(len(progress), 1)
        self.assertIn("server download_done Fake-4bit", said)
        self.assertEqual(said[-1], 'server warning bachmcp.toml now uses Fake-4bit (mlx): restart Bach to load it')
        with open(self.toml, encoding="utf-8") as f:
            self.assertEqual(f.read(), '[model]\nmodel = "Fake-4bit"  # the model\n')

    def test_one_download_at_a_time_and_stop(self):
        self.status.answer("bach download_model fake")
        self.wait_for("server download_start")
        self.status.download("again")
        self.assertTrue(any("already running" in s for s in self.max.said))
        self.status.answer("bach download_stop")
        self.wait_for("server download_stopped Fake-4bit")

    def test_nothing_to_download_or_stop(self):
        self.status.answer("bach download_model")
        self.assertTrue(self.max.said[-1].startswith("server download_error "), self.max.said[-1])
        self.status.answer("bach download_stop")
        self.assertEqual(self.max.said[-1], 'server warning no download is running')


class UDPRoundTripTests(unittest.TestCase):
    """Max -> Bach -> Max over real sockets, as the patch does it."""

    def test_a_request_is_answered_and_never_mistaken_for_an_answer(self):
        to_max = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # stands for [udpreceive 3000]
        to_max.bind(("127.0.0.1", 0))
        to_max.settimeout(2)
        self.addCleanup(to_max.close)
        bridge = MaxBridge(send_port=to_max.getsockname()[1], receive_port=free_port())
        bridge.on_request(Status(Config(), bridge, "run").answer)
        bridge.start()
        self.addCleanup(bridge.stop)

        patch = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # stands for [udpsend 127.0.0.1 3001]
        self.addCleanup(patch.close)
        patch.sendto(encode("bach ping"), ("127.0.0.1", bridge.receive_port))
        self.assertEqual(decode(to_max.recvfrom(65507)[0]), "server pong")

        patch.sendto(encode("bach_buffer_written"), ("127.0.0.1", bridge.receive_port))
        self.assertEqual(bridge.receive(timeout_seconds=2), "bach_buffer_written", "answers still reach the tools")
        time.sleep(0.05)
        self.assertIsNone(bridge.receive(timeout_seconds=0.1), "the request was not queued as an answer")


class OneBachTests(unittest.TestCase):
    def test_quit_stops_what_was_registered_and_exits(self):
        stopped = []
        status = Status(Config(), Recorder(), "run")
        status.on_quit(lambda: stopped.append("model server"))
        with mock.patch("bach_mcp.utilities.status.os._exit") as exit_:
            status.quit()
        self.assertEqual(stopped, ["model server"])
        exit_.assert_called_once_with(0)
        self.assertEqual(status.bridge.said, ["server status 0"], "the last and only word")
        self.assertTrue(status.bridge.stopped)

    def test_a_second_start_typed_into_a_running_bach_warns(self):
        from bach_mcp.utilities.status import on_input
        status = Status(Config(), Recorder(), "run")
        on_input(status, "zsh -ic \"cd '/x/py' && conda activate bach-mcp && python main.py run\" 2>&1\n")
        on_input(status, "\n")
        on_input(status, "hello\n")
        self.assertEqual(status.bridge.said, ["server warning Another bach server is already running",
                                              "server warning Bach is running and did not run: hello"])
        with mock.patch.object(Status, "quit") as quit_:
            on_input(status, "quit\n")
        quit_.assert_called_once()

    def test_a_second_bach_does_not_start_and_warns(self):
        from bach_mcp.bridge.max import BridgeBusy
        from bach_mcp.utilities.status import start_bridge
        to_max = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        to_max.bind(("127.0.0.1", 0))
        to_max.settimeout(2)
        self.addCleanup(to_max.close)
        first = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # the Bach already running
        first.bind(("127.0.0.1", 0))
        first.settimeout(0.3)
        self.addCleanup(first.close)
        config = Config()
        config.max.send_port, config.max.receive_port = to_max.getsockname()[1], first.getsockname()[1]
        with self.assertRaisesRegex(BridgeBusy, "Another bach server is already running"):
            start_bridge(config, "run")
        self.assertEqual(decode(to_max.recvfrom(65507)[0]), 'server warning Another bach server is already running')
        with self.assertRaises(socket.timeout):
            first.recvfrom(65507)  # the running one was not asked to quit


if __name__ == "__main__":
    unittest.main()
