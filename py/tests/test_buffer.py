"""Tests for the buffer file between the MCP server and bach.roll, and the score tools that use it.
Run: python -m unittest discover -s py/tests"""

import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.buffer import RollBuffer, add_to_roll, is_complete, spaced  # noqa: E402
from bach_mcp.score_tools import register_score_tools  # noqa: E402
from bach_mcp.translate import count_notes, llll_to_score, normalize_score  # noqa: E402

# A score as bach.roll's writetxt writes it: a header bach owns, slots the JSON does not model,
# quoted symbols, an empty voice.
BACH_TEXT = """roll
\t[ slotinfo
\t\t[ 7
\t\t\t[ name "sample file" ]
\t\t\t[ type text ]
\t\t]
\t]
\t[ commands
\t\t[ 1 note chord 0 ]
\t]
\t[ clefs G F ]
\t[ voicenames Flute "[Cello]" ]
\t[ markers
\t\t[ 0.0 A none ]
\t]
\t[
\t\t[ 0.0
\t\t\t[ 7200.0 500.0 100
\t\t\t\t[ slots
\t\t\t\t\t[ 7 Elements:/samples/Fl-ord-C6-ff.wav ]
\t\t\t\t]
\t\t\t0 ]
\t\t0 ]
\t\t[ 1000.0
\t\t\t[ 7400.0 500.0 100 0 ]
\t\t0 ]
\t0 ]
\t[ 0 ]
"""


def chord(onset, pitch, dur=500):
    return {"onset": onset, "notes": [{"pitch": pitch, "dur": dur}]}


class TextTests(unittest.TestCase):
    def test_spaced_and_complete(self):
        self.assertEqual(spaced("roll [clefs G] [[0 [6000 500 80]]]"), "roll [ clefs G ] [ [ 0 [ 6000 500 80 ] ] ]")
        self.assertTrue(is_complete(BACH_TEXT))
        self.assertFalse(is_complete(BACH_TEXT[:200]), "a file still being written")
        self.assertFalse(is_complete("[ 1 2 ]"))

    def test_adding_keeps_everything_the_json_does_not_model(self):
        new = normalize_score({"voices": [{"chords": [chord(2000, 7500)]},
                                          {"chords": [chord(0, 3600, 2000)]},
                                          {"name": "Viola", "chords": [chord(500, 4800)]}],
                               "markers": [{"onset": 2000, "name": "B"}]})
        merged = add_to_roll(BACH_TEXT, new)
        for kept in ('[ name "sample file" ]', "Elements:/samples/Fl-ord-C6-ff.wav", "[ 1 note chord 0 ]", '"[Cello]"'):
            self.assertIn(kept, merged)
        self.assertTrue(is_complete(merged))
        score = llll_to_score(merged)
        self.assertEqual([[c["onset"] for c in v["chords"]] for v in score["voices"]], [[0, 1000, 2000], [0], [500]])
        self.assertEqual([m["name"] for m in score["markers"]], ["A", "B"])

    def test_adding_to_a_roll_without_markers_or_voices(self):
        merged = add_to_roll("roll [ clefs G ] [ 0 ]", normalize_score(
            {"voices": [{"chords": [chord(0, 6000)]}, {"chords": [chord(100, 6100)]}],
             "markers": [{"onset": 0, "name": "A"}]}))
        score = llll_to_score(merged)
        self.assertEqual(count_notes(score), 2)
        self.assertEqual(score["markers"], [{"onset": 0, "name": "A"}])
        with self.assertRaises(ValueError):
            add_to_roll("[ 1 2 ]", normalize_score({"voices": [{"chords": [chord(0, 6000)]}]}))


class FakeMax:
    """bach.roll behind the bridge: it reads the buffer on mcp_buffer_written, and writes it on
    write_buffer, then answers bach_buffer_written."""

    def __init__(self, roll_text=BACH_TEXT):
        self.roll = roll_text
        self.sent = []
        self.queue = []
        self.tonedivision = 2

    def send_info(self, message):
        self.sent.append(message)
        words = message.split(" ", 1)
        if words[0] == "mcp_buffer_written":
            with open(words[1].strip('"'), encoding="utf-8") as f:
                self.roll = f.read()
        elif words[0] == "write_buffer":
            with open(words[1].strip('"'), "w", encoding="utf-8") as f:
                f.write(self.roll)
            self.queue.append({"data": "bach_buffer_written"})
        elif words[0] == "tonedivision":
            self.tonedivision = int(words[1])
        return True

    def flush_incoming(self):
        self.queue.clear()

    def wait_for_incoming(self, timeout_seconds=0.0):
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
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        os.environ["BACH_BUFFER"] = os.path.join(self.folder, "buffer.txt")
        self.addCleanup(os.environ.pop, "BACH_BUFFER", None)
        self.max = FakeMax()
        mcp = FakeMCP()
        register_score_tools(mcp, self.max)
        self.tools = mcp.tools

    def test_write_replaces_through_the_file(self):
        reply = self.tools["write_score"](score={"voices": [{"name": "Oboe", "chords": [chord(0, 6950), chord(500, 7000)]}]})
        self.assertTrue(reply.startswith("OK. Score written."), reply)
        path = os.environ["BACH_BUFFER"]
        self.assertEqual(self.max.sent[:2], ["tonedivision 4", f'mcp_buffer_written "{path}"'])
        self.assertTrue(all(len(m) < 200 for m in self.max.sent), "no score travels as a message")
        self.assertTrue(self.max.roll.startswith("roll [ clefs G ] [ voicenames Oboe ]"))

    def test_a_score_sent_as_text(self):
        good = '{"voices": [{"name": "Oboe", "chords": [[0, {}, [6900, 500, 80]], [500, {}, [7000, 500, 80]]]}]}'
        self.assertTrue(self.tools["write_score"](score=good).startswith("OK. Score written."))
        broken = good.replace("[6900, 500, 80]] [500", "[6900, 500, 80]][500").replace("]], [500", "]] [500")
        reply = self.tools["write_score"](score=broken)
        self.assertIn("ERROR: the score is not valid JSON: a comma is missing at character", reply)
        self.assertIn("[6900, 500, 80]] <HERE>[500", reply)

    def test_a_wrong_closing_sequence_is_repaired_and_nothing_else(self):
        from bach_mcp.score_tools import close_brackets
        captured = ('{"voices": [{"name": "Cello", "chords": [[3550, {"art": "staccato"}, [5600, 300, 80]], '
                    '[4350, {"art": "staccato"}, [5900, 1000, 80]] }]}]')  # Qwen's ending, as captured
        self.assertEqual(close_brackets(captured)["voices"][0]["chords"][1], [4350, {"art": "staccato"}, [5900, 1000, 80]])
        self.assertIsNotNone(close_brackets('{"voices": [{"chords": [[0, {}, [6000, 500, 80]]'), "a missing ending")
        self.assertIsNone(close_brackets('{"voices": [{"chords": [[0, {} [6000, 500, 80]]]}]}'), "a missing comma inside")
        self.assertIsNone(close_brackets('{"voices": [{"chords": [[0, {}, [6000, 500, 80}, [500, {}, [6100, 500, 80]]]}]}'),
                          "a wrong bracket inside")
        self.assertIsNone(close_brackets('{"voices": [{"name": "Vio'), "an open text")
        reply = self.tools["write_score"](score=captured)
        self.assertTrue(reply.startswith("OK. Score written."), reply)

    def test_add_inserts_into_the_current_score(self):
        reply = self.tools["write_score"](score={"voices": [{"chords": [chord(3000, 7600)]}]}, add=True)
        self.assertTrue(reply.startswith("OK. Added to the score."), reply)
        self.assertEqual(count_notes(llll_to_score(self.max.roll)), 3)
        self.assertIn("Elements:/samples/Fl-ord-C6-ff.wav", self.max.roll)
        self.assertEqual([m.split()[0] for m in self.max.sent], ["write_buffer", "mcp_buffer_written"])

    def test_read_score_reads_the_file(self):
        reply = self.tools["read_score"]()
        self.assertTrue(reply.startswith("2 voice(s), 2 notes in the whole score."))
        self.assertIn('"name":"Flute"', reply)
        self.assertIn('"chords":[[0,{},[7200,500,100]],[1000,{},[7400,500,100]]]', reply)
        self.assertRegex(reply, re.escape('"markers":[{"onset":0,"name":"A"}]'))

    def test_a_second_read_is_unchanged_only_within_one_chat(self):
        from bach_mcp.gateway import ModeSwitch
        from bach_mcp.config import BachConfig
        self.assertTrue(self.tools["read_score"]().startswith("2 voice(s)"))
        self.assertTrue(self.tools["read_score"]().startswith("Unchanged since your previous read_score"))
        ModeSwitch(BachConfig())({"messages": [{"role": "user", "content": "a new chat"}]})
        self.assertTrue(self.tools["read_score"]().startswith("2 voice(s)"), "a new chat reads the score again")

    def test_when_max_does_not_answer(self):
        class Silent(FakeMax):
            def send_info(self, message):  # reachable, but bach.roll never answers
                self.sent.append(message)
                return True

        mcp = FakeMCP()
        register_score_tools(mcp, Silent())
        self.assertIn("Max did not answer", mcp.tools["read_score"]())
        self.assertIn("Nothing was added", mcp.tools["write_score"](score={"voices": [{"chords": [chord(0, 6000)]}]}, add=True))

    def test_only_the_answer_bach_buffer_written_counts(self):
        self.max.queue.append({"data": "algo_status done algo 3 1"})
        self.assertTrue(is_complete(RollBuffer(self.max).fetch()))


class UDPBridgeTests(unittest.TestCase):
    def test_plain_text_both_ways(self):
        from bach_mcp.udp import UDPReceiver, UDPSend
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
        from bach_mcp.udp import decode

        def pad(b):
            b += b"\x00"
            return b + b"\x00" * (-len(b) % 4)
        packet = pad(b"bach_buffer_loaded") + pad(b",sii") + pad(b"q3") + (2).to_bytes(4, "big") + (1).to_bytes(4, "big")
        self.assertEqual(decode(packet), "bach_buffer_loaded q3 2 1")
        self.assertEqual(decode(b"bach_buffer_written q3"), "bach_buffer_written q3")

    def test_messages_leave_as_packets_udpreceive_reads(self):
        from bach_mcp.udp import decode, encode
        packet = encode('mcp_buffer_written q3 "/a path/buffer.txt"')
        self.assertEqual(len(packet) % 4, 0)
        self.assertTrue(packet.startswith(b"mcp_buffer_written\x00\x00,ss\x00"))
        self.assertEqual(decode(packet), 'mcp_buffer_written q3 "/a path/buffer.txt"')
        self.assertEqual(decode(encode("tonedivision 4")), "tonedivision 4")
        self.assertEqual(decode(encode("clear")), "clear")
        self.assertEqual(decode(encode("algo strings times 32.5")), "algo strings times 32.5")


if __name__ == "__main__":
    unittest.main()
