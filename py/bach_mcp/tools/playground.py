"""
playground.py
-------------
The playground: the folder where everything a model makes is kept, set by the
patch with `set_playground <path>`. It always has these folders:

    <path>/algorithms       <name>.js (and .history/)
    <path>/scores           <name>.json, each roll's score (bachjson-complete)
    <path>/prompts          <name>.jsonl, the conversation of each instance
    <path>/gen
    <path>/processes        <name>.py and <name>.json, the code of each buffer instance (and .history/)
    <path>/skills           <name>.md, the skill files the model's skill is built from
    <path>/skills/profiles  <name>.json, lists of skills

and these files, made when missing:

    <path>/skills/core-algorithmic.md                       a copy of the package's skill (prompt/BACH_SKILL.md)
    <path>/skills/core-electronic.md                        a copy of the sound skill (prompt/GEN_SKILL.md): gen~,
                                                            for synth and fx instances
    <path>/skills/quantizer.md                              a copy of the quantizer skill (prompt/QUANTIZER_SKILL.md):
                                                            markers with a role, the measures bach.quantize reads.
                                                            An extra skill: in no profile until the user adds it
    <path>/skills/profiles/minimal-algorithmic-composer.json  {"skills": ["core-algorithmic"]}
    <path>/skills/profiles/minimal-electronic-composer.json   {"skills": ["core-electronic"]}

A copy of a package skill stays in step with the package as long as the user has not
edited it: <path>/skills/.copied.json keeps a hash of each copy as it was made, and a
copy that still has that hash is replaced when the package's skill changes. An edited
copy is the user's and is never touched; deleting it brings back the package's. A
copy made before .copied.json existed is recorded once it equals the package's.
Profiles are made only when missing.

Whatever is missing is made, the folder itself included (as the patch's
bachmcp.server.playground.js does). Max may send the path as "Macintosh HD:/Users/...":
the volume is dropped.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil

from ..prompt.skill import GEN_SKILL_PATH, QUANTIZER_SKILL_PATH, SKILL_PATH

FOLDERS = ("algorithms", "scores", "prompts", "gen", "processes", "skills", os.path.join("skills", "profiles"))
CORE = os.path.join("skills", "core-algorithmic.md")
PROFILE = os.path.join("skills", "profiles", "minimal-algorithmic-composer.json")
PROFILE_SKILLS = {"skills": ["core-algorithmic"]}
GEN_CORE = os.path.join("skills", "core-electronic.md")
GEN_PROFILE = os.path.join("skills", "profiles", "minimal-electronic-composer.json")
QUANTIZER = os.path.join("skills", "quantizer.md")
GEN_PROFILE_SKILLS = {"skills": ["core-electronic"]}
COPIED = os.path.join("skills", ".copied.json")  # {copy file name: sha256 of the copy as it was made}

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
    _copy_skills(root)
    for file, skills in ((PROFILE, PROFILE_SKILLS), (GEN_PROFILE, GEN_PROFILE_SKILLS)):
        profile = os.path.join(root, file)
        if not os.path.exists(profile):
            try:
                with open(profile, "w", encoding="utf-8") as f:
                    f.write(json.dumps(skills, indent=2) + "\n")
            except OSError as exc:
                raise ValueError(f"cannot write {profile}: {exc.strerror}") from None
    return root


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _copy_skills(root: str) -> None:
    """Copy each package skill that is missing, or that changed while its copy was not edited."""
    record_path = os.path.join(root, COPIED)
    try:
        with open(record_path, encoding="utf-8") as f:
            record = json.load(f)
        if not isinstance(record, dict):
            record = {}
    except (OSError, ValueError):
        record = {}
    before = dict(record)
    for source, copy in ((SKILL_PATH, CORE), (GEN_SKILL_PATH, GEN_CORE), (QUANTIZER_SKILL_PATH, QUANTIZER)):
        core = os.path.join(root, copy)
        key = os.path.basename(copy)
        shipped = _sha256(source)
        if os.path.exists(core):
            current = _sha256(core)
            if current == shipped:
                record[key] = shipped  # in step (also a copy made before the record existed)
                continue
            if record.get(key) != current:
                continue  # edited by the user, or of unknown origin: theirs
        try:
            shutil.copyfile(source, core)
        except OSError as exc:
            raise ValueError(f"cannot copy the skill to {core}: {exc.strerror}") from None
        record[key] = shipped
    if record != before:
        try:
            with open(record_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(record, indent=2, sort_keys=True) + "\n")
        except OSError as exc:
            raise ValueError(f"cannot write {record_path}: {exc.strerror}") from None


__all__ = ["FOLDERS", "CORE", "COPIED", "PROFILE", "GEN_CORE", "GEN_PROFILE", "QUANTIZER", "local_path", "prepare"]
