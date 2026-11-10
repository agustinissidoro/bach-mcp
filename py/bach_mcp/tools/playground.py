"""
playground.py
-------------
The playground: the folder where everything a model makes is kept, set by the
patch with `set_playground <path>`. It always has these folders:

    <path>/algorithms       <name>.js (and .history/)
    <path>/scores           <name>.json, each roll's score (bachjson-complete)
    <path>/prompts          <name>.jsonl, the conversation of each instance
    <path>/gen
    <path>/skills           <name>.md, the skill files the model's skill is built from
    <path>/skills/profiles  <name>.json, lists of skills

and these files, made only when missing (once there, they are the user's to edit):

    <path>/skills/core-algorithmic.md                       a copy of the package's skill (prompt/BACH_SKILL.md)
    <path>/skills/core-electronic.md                        a copy of the sound skill (prompt/GEN_SKILL.md): gen~,
                                                            for synth and fx instances
    <path>/skills/profiles/minimal-algorithmic-composer.json  {"skills": ["core-algorithmic"]}
    <path>/skills/profiles/minimal-electronic-composer.json   {"skills": ["core-electronic"]}

Whatever is missing is made, the folder itself included (as the patch's
bachmcp.server.playground.js does). Max may send the path as "Macintosh HD:/Users/...":
the volume is dropped.
"""

from __future__ import annotations

import json
import os
import re
import shutil

from ..prompt.skill import GEN_SKILL_PATH, SKILL_PATH

FOLDERS = ("algorithms", "scores", "prompts", "gen", "skills", os.path.join("skills", "profiles"))
CORE = os.path.join("skills", "core-algorithmic.md")
PROFILE = os.path.join("skills", "profiles", "minimal-algorithmic-composer.json")
PROFILE_SKILLS = {"skills": ["core-algorithmic"]}
GEN_CORE = os.path.join("skills", "core-electronic.md")
GEN_PROFILE = os.path.join("skills", "profiles", "minimal-electronic-composer.json")
GEN_PROFILE_SKILLS = {"skills": ["core-electronic"]}

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
    for source, copy in ((SKILL_PATH, CORE), (GEN_SKILL_PATH, GEN_CORE)):
        core = os.path.join(root, copy)
        if not os.path.exists(core):
            try:
                shutil.copyfile(source, core)
            except OSError as exc:
                raise ValueError(f"cannot copy the skill to {core}: {exc.strerror}") from None
    for file, skills in ((PROFILE, PROFILE_SKILLS), (GEN_PROFILE, GEN_PROFILE_SKILLS)):
        profile = os.path.join(root, file)
        if not os.path.exists(profile):
            try:
                with open(profile, "w", encoding="utf-8") as f:
                    f.write(json.dumps(skills, indent=2) + "\n")
            except OSError as exc:
                raise ValueError(f"cannot write {profile}: {exc.strerror}") from None
    return root


__all__ = ["FOLDERS", "CORE", "PROFILE", "GEN_CORE", "GEN_PROFILE", "local_path", "prepare"]
