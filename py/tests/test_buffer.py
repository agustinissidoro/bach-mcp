"""The roll files between the MCP server and Max (bachjson-complete), and the score tools that use
them, which speak the compressed form to the model. Run: python -m unittest discover -s py/tests"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.bridge import buffer as buffer_module  # noqa: E402
from bach_mcp.bridge.buffer import RollBuffer, read_json  # noqa: E402
from bach_mcp.bridge.protocol import words as split  # noqa: E402
from bach_mcp.tools.playground import prepare  # noqa: E402
from bach_mcp.tools.score_tools import register_score_tools  # noqa: E402
from bach_mcp.tools.session import NoTarget, Target, new_conversation, serve_targets  # noqa: E402

# A roll's score as the patch writes it (bachmcp.translate @out json), with a header the model never sees.
ROLL = {
    "header": {"slotinfo": {"20": {"name": ["dynamics"], "type": ["dynamics"]},
                            "7": {"name": ["sample"], "type": ["text"]}},
               "clefs": ["G", "F"], "keys": ["CM", "CM"], "voicenames": [["Flute"], []],
               "markers": [{"onset": 0.0, "name": ["A"], "role": "none"}]},
    "voices": [
        {"chords": [{"onset": 0.0, "notes": [{"pitch": 7200.0, "dur": 500.0, "vel": 100,
                                               "slots": {"7": ["Fl-ord-C6-ff.wav"]}, "flag": 0}], "flag": 0},
                    {"onset": 1000.0, "notes": [{"pitch": 7400.0, "dur": 500.0, "vel": 100, "flag": 0}], "flag": 0}],
         "flag": 0},
        {"chords": [], "flag": 0},
    ],
}


class FakeMax:
    """The patch around one instance's roll: on <name> load_roll it takes the file, on
    <name> write_roll it writes its score there and answers <name> roll_written; on
    server write_buffer it writes the score to buffer.json and answers server buffer_done."""

    def __init__(self, rolls, score=ROLL):
        self.rolls = rolls
        self.score = json.loads(json.dumps(score))
        self.sent = []
        self.queue = []
        self.tonedivision = 2

    def send(self, message):
        self.sent.append(message)
        name, command, *args = split(message)
        if name == "server" and command == "write_buffer":
            with open(buffer_module.BUFFER_FILE, "w", encoding="utf-8") as f:
                json.dump(self.score, f)
            self.queue.append("server buffer_done")
        elif command == "load_roll":
            self.score = read_json(os.path.join(self.rolls, args[0]))
        elif command == "write_roll":
            with open(os.path.join(self.rolls, args[0]), "w", encoding="utf-8") as f:
                json.dump(self.score, f)
            self.queue.append(f"{name} roll_written {args[0]}")
        elif command == "tonedivision":
            self.tonedivision = int(args[0])
        return True

    def flush(self):
        self.queue.clear()

    def receive(self, timeout_seconds=0.0):
        return self.queue.pop(0) if self.queue else None


class FakeMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def register(fn):
            self.tools[fn.__name__] = fn
            return fn
        return register


class ScoreToolTests(unittest.TestCase):
    def setUp(self):
        self.folder = prepare(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.target = Target("notes1", "writer", self.folder)
        serve_targets(lambda: self.target)
        self.addCleanup(serve_targets, None)
        self.max = FakeMax(self.target.scores)
        saved = buffer_module.BUFFER_FILE
        buffer_module.BUFFER_FILE = os.path.join(self.folder, "buffer.json")
        self.addCleanup(setattr, buffer_module, "BUFFER_FILE", saved)
        mcp = FakeMCP()
        register_score_tools(mcp, self.max)
        self.tools = mcp.tools

    def test_read_answers_compressed(self):
        reply = self.tools["read_score"]()
        self.assertEqual(self.max.sent[-1], "server write_buffer")
        lines = reply.splitlines()
        self.assertEqual(lines[:4], ["voice 1 (Flute): 2 notes in 2 chords, 0-1500 ms, pitch 7200-7400, clef G",
                                     "voice 2: empty, clef F", "2 voice(s), 2 notes, 1500 ms long.", "markers: A@0"])
        self.assertEqual(json.loads(lines[4]), {"slots": {"7": "sample"}, "markers": [[0, "A"]], "voices": [
            {"voice": 1, "name": "Flute", "chords": [[0, [7200, 500, 100, {"sample": "Fl-ord-C6-ff.wav"}]], [1000, [7400, 500, 100]]]}]})

    def test_a_long_read_is_cut_at_one_time_for_all_voices(self):
        from bach_mcp.music.reader import read_view
        chord = lambda t, p: {"onset": t, "notes": [{"pitch": p, "dur": 100, "vel": 90}]}
        score = {"voices": [{"chords": [chord(t * 100, 6000) for t in range(400)]},
                            {"chords": [chord(t * 100, 4800) for t in range(400)]}]}
        reply = read_view(score, budget=2000)
        shown = json.loads(reply.splitlines()[3])
        last = [v["chords"][-1][0] for v in shown["voices"]]
        self.assertEqual(last[0], last[1], "both voices stop at the same time")
        self.assertLessEqual(len(reply.splitlines()[3]), 2000)
        self.assertIn(f"from_ms={last[0] + 100}", reply)
        later = json.loads(read_view(score, voice=2, from_ms=last[0] + 100, budget=2000).splitlines()[3])
        self.assertEqual([v["voice"] for v in later["voices"]], [2])
        self.assertEqual(later["voices"][0]["chords"][0][0], last[0] + 100)

    def test_write_expands_onto_the_roll_and_keeps_its_header(self):
        written = {"voices": [{"name": "Oboe", "chords": [[0, [6950, 500, 80, {"dynamics": "p<"}]], [500, [7000, 500, 80]]]}]}
        reply = self.tools["write_score"](score=written)
        self.assertTrue(reply.startswith("OK. Score written."), reply)
        self.assertIn("voice 1 (Oboe): 2 notes in 2 chords, 0-1000 ms, pitch 6950-7000", reply)
        self.assertEqual(self.max.sent[-2:], ["notes1 tonedivision 4", "notes1 load_roll notes1.json"])
        roll = self.max.score
        self.assertEqual(roll["header"]["slotinfo"], ROLL["header"]["slotinfo"], "what the model never saw is kept")
        self.assertEqual(roll["header"]["clefs"], ["G", "F"])
        self.assertEqual(roll["header"]["voicenames"], [["Oboe"]])
        self.assertEqual(roll["voices"][0]["chords"][0]["notes"][0]["slots"], {"20": ["p<"]})
        self.assertTrue(all(len(m) < 200 for m in self.max.sent), "no score travels as a message")

    def test_add_puts_chords_in_time(self):
        reply = self.tools["write_score"](score={"voices": [{"chords": [[500, [7300, 250, 90]]]}]}, add=True)
        self.assertTrue(reply.startswith("OK. Added to the score."), reply)
        onsets = [c["onset"] for c in self.max.score["voices"][0]["chords"]]
        self.assertEqual(onsets, [0.0, 500, 1000.0])
        self.assertEqual(self.max.score["voices"][0]["chords"][0]["notes"][0]["slots"], {"7": ["Fl-ord-C6-ff.wav"]})

    def test_mistakes_are_named_and_nothing_is_written(self):
        cases = [({"voices": []}, 'the score needs "voices"'),
                 ({"voices": [{"chords": [[0]]}]}, "voice 1, chord 1: a chord needs at least one note"),
                 ({"voices": [{"chords": [[0, [6000, 500]]]}]}, "voice 1, chord 1, note 1: a note is [pitch, dur, vel]"),
                 ({"voices": [{"chords": [[0, [60, 500, 80]]]}]}, "looks like a MIDI note number"),
                 ('{"voices": [{"chords": [[0, [6000, 500, 80]] [500, [6100, 500, 80]]]}]}', "a comma is missing")]
        for score, expected in cases:
            reply = self.tools["write_score"](score=score)
            self.assertTrue(reply.startswith("ERROR"), reply)
            self.assertIn(expected, reply)
        self.assertEqual(self.max.sent, [])

    def test_a_wrong_closing_sequence_is_repaired(self):
        reply = self.tools["write_score"](score='{"voices": [{"chords": [[0, [6000, 500, 80]] }]}]')
        self.assertTrue(reply.startswith("OK. Score written."), reply)

    def test_only_a_writer_writes_notes(self):
        self.target = Target("scales1", "generator", self.folder)
        reply = self.tools["write_score"](score={"voices": [{"chords": [[0, [6000, 500, 80]]]}]})
        self.assertIn("scales1 is a generator: it takes an algorithm (send_algorithm), not notes", reply)
        self.assertIn("Nothing was cleared", self.tools["clear_score"]())
        self.assertTrue(self.tools["read_score"]().startswith("voice 1 (Flute)"), "any instance's roll can be read")

    def test_without_an_instance_nothing_is_sent(self):
        def none():
            raise NoTarget("no instance is active: select one (set_active_instance <name>)")
        serve_targets(none)
        self.assertIn("no instance is active", self.tools["write_score"](score={"voices": [{"chords": [[0, [6000, 500, 80]]]}]}))
        self.assertIn("no instance is active", self.tools["read_score"]())
        self.assertEqual(self.max.sent, [])

    def test_clear(self):
        self.assertEqual(self.tools["clear_score"](), "Score cleared.")
        self.assertEqual(self.max.sent, ["notes1 clear"])

    def test_a_second_read_is_unchanged_only_within_one_chat(self):
        self.assertTrue(self.tools["read_score"]().startswith("voice 1 (Flute)"))
        self.assertTrue(self.tools["read_score"]().startswith("Unchanged since your previous read_score"))
        new_conversation()
        self.assertTrue(self.tools["read_score"]().startswith("voice 1 (Flute)"))

    def test_when_max_does_not_answer(self):
        class Silent(FakeMax):
            def send(self, message):
                self.sent.append(message)
                return True
        mcp = FakeMCP()
        register_score_tools(mcp, Silent(self.target.scores))
        self.assertIn("Max did not answer", mcp.tools["read_score"]())
        self.assertIn("Nothing was added", mcp.tools["write_score"](score={"voices": [{"chords": [[0, [6000, 500, 80]]]}]}, add=True))

    def test_only_the_instance_answer_counts(self):
        class Other(FakeMax):
            def send(self, message):
                self.sent.append(message)
                self.queue += ["other roll_written other.json", "notes1 algo_done 3 1"]
                return True
        self.assertIsNone(RollBuffer(Other(self.target.scores), "notes1", self.target.roll_file).fetch(timeout_seconds=0.2))


class UDPBridgeTests(unittest.TestCase):
    def test_plain_text_both_ways(self):
        from bach_mcp.bridge.udp import UDPReceiver, UDPSend
        received = []
        receiver = UDPReceiver(port=0)
        receiver.set_default_handler(received.append)
        receiver.start()
        self.addCleanup(receiver.stop)
        sender = UDPSend(port=receiver.port)
        self.addCleanup(sender.close)
        self.assertTrue(sender.send('bach_buffer_written q3'))
        self.assertTrue(sender.send('mcp_buffer_written q4 "/a path/buffer.txt"'))
        self.assertFalse(sender.send("x" * 70000), "a score never travels as a message")
        deadline = __import__("time").time() + 2
        while len(received) < 2 and __import__("time").time() < deadline:
            __import__("time").sleep(0.01)
        self.assertEqual(received, ["bach_buffer_written q3", 'mcp_buffer_written q4 "/a path/buffer.txt"'])

    def test_replies_in_udpsend_packet_form(self):
        from bach_mcp.bridge.udp import decode

        def pad(b):
            b += b"\x00"
            return b + b"\x00" * (-len(b) % 4)
        packet = pad(b"bach_buffer_loaded") + pad(b",sii") + pad(b"q3") + (2).to_bytes(4, "big") + (1).to_bytes(4, "big")
        self.assertEqual(decode(packet), "bach_buffer_loaded q3 2 1")
        self.assertEqual(decode(b"bach_buffer_written q3"), "bach_buffer_written q3")

    def test_messages_leave_as_packets_udpreceive_reads(self):
        from bach_mcp.bridge.udp import decode, encode
        packet = encode('mcp_buffer_written q3 "/a path/buffer.txt"')
        self.assertEqual(len(packet) % 4, 0)
        self.assertTrue(packet.startswith(b"mcp_buffer_written\x00\x00,ss\x00"))
        self.assertEqual(decode(packet), 'mcp_buffer_written q3 "/a path/buffer.txt"')
        self.assertEqual(decode(encode("tonedivision 4")), "tonedivision 4")
        self.assertEqual(decode(encode("clear")), "clear")
        self.assertEqual(decode(encode("algo strings times 32.5")), "algo strings times 32.5")
        said = 'scales1 prompt "a \\"tight\\" canon, don\'t stop"'
        self.assertEqual(decode(encode(said)), said, "quotes and apostrophes survive the trip")


if __name__ == "__main__":
    unittest.main()
