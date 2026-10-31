"""The installer's arguments and the Node path; quitting on signals and on closed input."""

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp import install  # noqa: E402


class ArgumentTests(unittest.TestCase):
    def test_the_one_not_given_is_false(self):
        args = install.parse(["--claude", "true"])
        self.assertEqual((args.claude, args.local), (True, False))
        args = install.parse(["--local", "true"])
        self.assertEqual((args.claude, args.local), (False, True))

    def test_both(self):
        args = install.parse(["--claude", "true", "--local", "true"])
        self.assertEqual((args.claude, args.local), (True, True))

    def test_at_least_one_is_needed(self):
        for argv in ([], ["--claude", "false"], ["--claude", "false", "--local", "false"]):
            with self.assertRaises(install.InstallError):
                install.parse(argv)

    def test_only_true_or_false(self):
        with self.assertRaises(install.InstallError):
            install.parse(["--claude", "yes"])

    def test_no_arguments_runs_nothing_and_says_failed(self):
        main_py = os.path.join(os.path.dirname(__file__), "..", "main.py")
        done = subprocess.run([sys.executable, main_py, "install"], capture_output=True, text=True)
        self.assertEqual(done.returncode, 1)
        self.assertTrue(done.stdout.startswith("installation: failed: "))


class NodeTests(unittest.TestCase):
    def test_set_node_keeps_the_rest(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "bachmcp.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write('[other]\nnode = "x"\n\n[algo]\nnode = "/old"   # a comment\n')
        install.set_node("/a path/node", path)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), '[other]\nnode = "x"\n\n[algo]\nnode = "/a path/node"   # a comment\n')

    def test_a_node_that_is_gone_is_not_found_there(self):
        self.assertNotEqual(install.find_node("/not/here/node"), "/not/here/node")


# A Status with what quit() would stop: a child process standing for the model server.
PROGRAM = textwrap.dedent("""
    import os, subprocess, sys, time
    sys.path.insert(0, sys.argv[1])
    from bach_mcp.bridge.max import OfflineBridge
    from bach_mcp.config import Config
    from bach_mcp.utilities.status import Status, quit_on_signals, watch_input
    status = Status(Config(), OfflineBridge(), "run")
    model = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], start_new_session=True)
    status.on_quit(model.terminate)
    print(model.pid, flush=True)
    quit_on_signals(status)
    watch_input(status)
    time.sleep(60)
""")


class QuitTests(unittest.TestCase):
    def start(self, stdin):
        py = os.path.join(os.path.dirname(__file__), "..")
        process = subprocess.Popen([sys.executable, "-c", PROGRAM, py], stdin=stdin, stdout=subprocess.PIPE, text=True)
        self.addCleanup(process.kill)
        return process, int(process.stdout.readline())

    def assert_all_gone(self, process, model):
        self.assertEqual(process.wait(timeout=10), 0)
        for _ in range(100):
            try:
                os.kill(model, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        os.kill(model, signal.SIGKILL)
        self.fail("the model server stayed behind")

    def test_signals_stop_the_model_server(self):
        for number in (signal.SIGTERM, signal.SIGHUP):
            process, model = self.start(subprocess.PIPE)
            process.send_signal(number)
            self.assert_all_gone(process, model)
            process.stdin.close()

    def test_closed_input_stops_the_model_server(self):
        process, model = self.start(subprocess.PIPE)
        process.stdin.close()
        self.assert_all_gone(process, model)

    def test_no_input_at_all_keeps_running(self):
        process, model = self.start(subprocess.DEVNULL)
        time.sleep(0.5)
        self.assertIsNone(process.poll())
        process.send_signal(signal.SIGTERM)
        self.assert_all_gone(process, model)


if __name__ == "__main__":
    unittest.main()
