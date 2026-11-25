"""bachmcp.shmbuffer~ / bachmcp.pshmbuffer~ help: Python on the very memories Max holds.

    run examples/python/shmbuffers.py

One memory, [bachmcp.shmbuffer~ <name>]:
    call gain <name> 0.5            the samples times 0.5, in place  → gain <name> <frames> <channels>
    call reverse <name>             backwards, in place
    call sine <name> 440 1000       replaced by a sine of 440 Hz, 1000 ms (another size: a new memory)
    call info <name>                → info <name> <frames> <channels> <sr> <serial>
    call watch <name>               from now on, each change made in Max → changed <name> <serial> <frames> <channels>

A polybuffer of memories, [bachmcp.pshmbuffer~ <name>]:
    call poly_add <name> 330 500    one more memory at the end: a sine   → poly_add <name> <count>
    call poly_gain <name> 2 0.5     memory 2 times 0.5
    call poly_pop <name>            remove the last                      → poly_pop <name> <count>
    call poly_count <name>          → poly_count <name> <count>
    call poly_watch <name>          from now on, each change made in Max → poly_changed <name> <count> <serial>

    eof                             the script ends

Each change ends with touch(): the Max object hears it and, with @notify 1, writes its buffer~(s).
"""
import os
import sys
import threading

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "py")))  # the bach_mcp package

from bachmcp_max import loop, on, out  # noqa: E402

from bach_mcp.utilities.shmbuffer import PShmBuffer, ShmBuffer  # noqa: E402

watching = set()


def sine(hz, ms, sr, channels):
    t = np.arange(int(round(ms * sr / 1000.0))) / sr
    wave = 0.5 * np.sin(2 * np.pi * hz * t)
    return np.repeat(wave[:, None], channels, axis=1)


# ---------------------------------------------------------------- one memory

@on("gain")
def gain(name, factor):
    buf = ShmBuffer(name)
    buf.array[:] *= factor                  # Max's own samples, worked in place
    buf.touch()                             # say so: with @notify 1 the object writes its buffer~
    return name, buf.frames, buf.channels


@on("reverse")
def reverse(name):
    buf = ShmBuffer(name)
    buf.array[:] = buf.array[::-1].copy()
    buf.touch()
    return name, buf.frames, buf.channels


@on("sine")
def make_sine(name, hz, ms):
    buf = ShmBuffer(name)
    sr = buf.sr or 44100.0
    buf.write(sine(hz, ms, sr, buf.channels), sr=sr)    # write() touches by itself
    return name, buf.frames, buf.channels


@on("info")
def info(name):
    buf = ShmBuffer(name)
    return name, buf.frames, buf.channels, buf.sr, buf.serial


@on("watch")
def watch(name):
    if name in watching:
        return
    buf = ShmBuffer(name)
    buf.listen()                            # from now on: nothing Max does is missed
    watching.add(name)

    def run():
        while buf.wait():                   # sleeps until Max changes the memory
            out("changed", name, buf.serial, buf.frames, buf.channels)

    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- a polybuffer of memories

@on("poly_add")
def poly_add(name, hz, ms):
    poly = PShmBuffer(name)
    sr = poly[1].sr if len(poly) else 44100.0
    poly.append(sine(hz, ms, sr, 1), sr=sr)  # <name>.<count+1>; append() touches by itself
    return name, len(poly)


@on("poly_gain")
def poly_gain(name, n, factor):
    member = PShmBuffer(name)[n]            # the same memory as ShmBuffer("<name>.<n>")
    member.array[:] *= factor
    member.touch()                          # tells the index too, which is what Max listens to
    return name, n


@on("poly_pop")
def poly_pop(name):
    poly = PShmBuffer(name)
    poly.pop()
    return name, len(poly)


@on("poly_count")
def poly_count(name):
    return name, len(PShmBuffer(name))


@on("poly_watch")
def poly_watch(name):
    key = "poly " + name
    if key in watching:
        return
    poly = PShmBuffer(name)
    poly.listen()
    watching.add(key)

    def run():
        while poly.wait():
            out("poly_changed", name, len(poly), poly.serial)

    threading.Thread(target=run, daemon=True).start()


out("ready")
loop()
