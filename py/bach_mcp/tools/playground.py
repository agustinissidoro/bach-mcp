"""
playground.py
-------------
The playground: the folder where everything a model makes is kept, set by the
patch with `set_playground <path>`. It always has three folders:

    <path>/algorithms   <name>.js (and .history/), <name>.source.json
    <path>/rolls        <name>.json, each roll's score (bachjson-complete)
    <path>/prompts      <name>.jsonl, the conversation of each instance

Whatever is missing is made, the folder itself included (as the patch's
bachmcp.playground.js does). Max may send the path as "Macintosh HD:/Users/...":
the volume is dropped.
"""

from __future__ import annotations

import os
import re

FOLDERS = ("algorithms", "rolls", "prompts")

_MAX_VOLUME = re.compile(r"^[^/:]+:(/.*)$")


def local_path(path: str) -> str:
    """A path as Max or a person writes it, as this machine reads it: absolute, without a Max volume."""
    m = _MAX_VOLUME.match(path.strip())
    return os.path.abspath(os.path.expanduser(m.group(1) if m else path.strip()))


def prepare(path: str) -> str:
    """Make sure the playground and its folders are there; return its absolute path.
    Raises ValueError with what is wrong (no path, a file in the way, no permission)."""
    if not path.strip():
        raise ValueError("set_playground needs a folder")
    root = local_path(path)
    for folder in (root, *(os.path.join(root, name) for name in FOLDERS)):
        if os.path.exists(folder) and not os.path.isdir(folder):
            raise ValueError(f"{folder} is a file, not a folder")
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as exc:
            raise ValueError(f"cannot make {folder}: {exc.strerror}") from None
    return root


__all__ = ["FOLDERS", "local_path", "prepare"]
