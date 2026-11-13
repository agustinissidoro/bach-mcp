"""Fill a bachmcp.shmbuffer~ with white noise, once.

    python py/bach_mcp/audio_processing/test.py <name>

<name> is the name of the object in Max: [bachmcp.shmbuffer~ <name> 1000]. The memory keeps
its size, channels and sampling rate; in Max, bang the object to write it to a buffer~.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from bach_mcp.utilities.shmbuffer import NoShmBuffer, ShmBuffer  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python py/bach_mcp/audio_processing/test.py <name>")
        return 2
    name = sys.argv[1]
    try:
        buf = ShmBuffer(name)
    except NoShmBuffer:
        print(f"no shmbuffer named {name}: make [bachmcp.shmbuffer~ {name} <ms>] in Max first")
        return 1
    samples = buf.array
    if samples.size == 0:
        print(f"shmbuffer {name} is empty: give it a size in Max")
        return 1
    samples[:] = np.random.default_rng().uniform(-1.0, 1.0, samples.shape)
    buf.touch()
    print(f"{name}: {samples.shape[0]} frames, {samples.shape[1]} channels of noise at {buf.sr:g} Hz")
    return 0


if __name__ == "__main__":
    sys.exit(main())
