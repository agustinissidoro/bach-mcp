"""
skills.py
---------
The skill built from the playground's own files, chosen from Max:

    <playground>/skills/<name>.md                   one skill: anything the model should know
    <playground>/skills/profiles/<name>.json        {"skills": ["core-algorithmic", "score-extras", ...]}
    <playground>/skills/.compiled.md                what was built, rewritten at each build
    <playground>/skills/.compiled/<instance>.md     the same, for an instance with its own choice

The patch chooses with two hub commands (chat/hub.py): `set_profile <name>` and
`set_skills <name> ...`, for every instance, or `<instance> set_profile ...` for one,
which then reads only what it chose. The skill is the profile's skills in their order, then the
extra skills; a skill named twice is used once, where it first comes. With neither,
nothing is built (SkillError) and the model reads the built-in skill.

A file says which objects its parts are for with markers that open and close
(`<!-- score --> ... <!-- /score -->`, skill.py); a file with none is for every object.
What a file leaves open is closed at its end (the closing markers are written in):
a part never runs into the next file. The markers stay, and are applied for each
instance as before.

.compiled.md starts with a comment saying what it was built from, which the model
never reads (read_compiled drops it). Tokens are estimated (4 characters a token).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Tuple

from .skill import closed

SKILLS = "skills"
PROFILES = os.path.join(SKILLS, "profiles")
COMPILED = os.path.join(SKILLS, ".compiled.md")
INSTANCE_COMPILED = os.path.join(SKILLS, ".compiled")
_HEADER = re.compile(r"\A<!-- compiled\b.*?-->\n*", re.S)


class SkillError(ValueError):
    """The skill cannot be built: nothing chosen, a missing file, a profile that is not a list of skills."""


@dataclass
class Compiled:
    text: str                                   # the skill, with its markers, without the header
    used: List[Tuple[str, int]] = field(default_factory=list)  # (skill, estimated tokens), in order
    warnings: List[str] = field(default_factory=list)

    @property
    def tokens(self) -> int:
        return sum(tokens for _, tokens in self.used)


def estimate_tokens(text: str) -> int:
    return (len(text) + 3) // 4


def _name(name: str, suffix: str) -> str:
    """A skill or profile name as written: with or without its suffix, never a path."""
    name = name.strip()
    if name.endswith(suffix):
        name = name[:-len(suffix)]
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise SkillError(f"{name or '(empty)'} is not a name: write it as in the folder, without a path")
    return name


def read_profile(playground: str, profile: str) -> List[str]:
    """The skills a profile lists, as written in skills/profiles/<profile>.json."""
    name = _name(profile, ".json")
    path = os.path.join(playground, PROFILES, name + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise SkillError(f"no profile {name}: no {path}") from None
    except (OSError, ValueError) as exc:
        raise SkillError(f"profile {name}: cannot read {path} ({exc})") from None
    skills = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(skills, list) or not all(isinstance(s, str) for s in skills):
        raise SkillError(f'profile {name}: expected {{"skills": ["core-algorithmic", ...]}} in {path}')
    return skills


def compile_skill(playground: str, profile: str = "", skills: List[str] = ()) -> Compiled:
    """The skill of the profile and then the extra skills, and what went into it."""
    if not profile and not skills:
        raise SkillError("no skills chosen: set_profile <name> or set_skills <name> ...")
    names: List[str] = []
    warnings: List[str] = []
    for raw in [*(read_profile(playground, profile) if profile else []), *skills]:
        name = _name(raw, ".md")
        if name in names:
            warnings.append(f"skill {name} is chosen twice: used once")
        else:
            names.append(name)
    if not any(name.startswith("core") for name in names):
        warnings.append("no core skill (core-...): the model may not know how to use the tools")
    parts: List[str] = []
    used: List[Tuple[str, int]] = []
    for name in names:
        path = os.path.join(playground, SKILLS, name + ".md")
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read().strip()
        except FileNotFoundError:
            raise SkillError(f"no skill {name}: no {path}") from None
        except OSError as exc:
            raise SkillError(f"skill {name}: cannot read {path} ({exc.strerror})") from None
        parts.append(closed(text))
        used.append((name, estimate_tokens(text)))
    return Compiled("\n".join(parts), used, warnings)


def header(compiled: Compiled, profile: str = "", skills: List[str] = ()) -> str:
    rows = [f"    {name:<24} ~{tokens:,} tokens" for name, tokens in compiled.used]
    chosen = [f"profile: {profile}"] if profile else []
    chosen += [f"skills: {' '.join(skills)}"] if skills else []
    return ("<!-- compiled: what the model reads, built from skills/ (rewritten at each build).\n"
            f"    {'; '.join(chosen)}\n" + "\n".join(rows) +
            f"\n    total ~{compiled.tokens:,} tokens (before the parts for each instance type are taken)\n-->\n\n")


def compiled_path(playground: str, instance: str = "") -> str:
    """skills/.compiled.md, or skills/.compiled/<instance>.md for an instance's own choice."""
    if not instance:
        return os.path.join(playground, COMPILED)
    return os.path.join(playground, INSTANCE_COMPILED, instance + ".md")


def write_compiled(playground: str, compiled: Compiled, profile: str = "", skills: List[str] = (),
                   instance: str = "") -> str:
    """Write the compiled file; returns its path."""
    path = compiled_path(playground, instance)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header(compiled, profile, skills) + compiled.text)
    return path


def read_compiled(playground: str, instance: str = "") -> str:
    """The compiled file as the model reads it: without its header."""
    with open(compiled_path(playground, instance), encoding="utf-8") as f:
        return _HEADER.sub("", f.read(), count=1)


def remove_compiled(playground: str, instance: str) -> None:
    """An instance back to the shared choice: its compiled file goes (and the folder, once empty)."""
    path = compiled_path(playground, instance)
    if os.path.exists(path):
        os.remove(path)
    folder = os.path.dirname(path)
    if os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)


def build(playground: str, profile: str = "", skills: List[str] = (), instance: str = "") -> Compiled:
    """Compile, write the compiled file and read it back: the text is what the file says."""
    compiled = compile_skill(playground, profile, skills)
    write_compiled(playground, compiled, profile, skills, instance)
    compiled.text = read_compiled(playground, instance)
    return compiled


__all__ = ["SKILLS", "PROFILES", "COMPILED", "INSTANCE_COMPILED", "SkillError", "Compiled", "estimate_tokens",
           "read_profile", "compiled_path", "remove_compiled",
           "compile_skill", "header", "write_compiled", "read_compiled", "build"]
