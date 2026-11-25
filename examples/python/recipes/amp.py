# Changes the level of the source (the bachmcp.python help's runner tab).
import audio_core as ac


def process(x, sr, p):
    return x * ac.db(p["gain_db"])
