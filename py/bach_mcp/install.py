"""
install.py
----------
`main.py install --claude true --local true`: sets Bach up inside its Max package.
At least one of the two must be true; the one not given is false.

It starts on whatever Python the shell has, with nothing installed, so it imports only
the standard library, and only at the top. Two stages:

    outside the .venv   checks Python, makes the .venv, installs the requirements,
                        then runs this same command again with the .venv's Python
    inside the .venv    the Node path and Claude. Claude is registered from here so that
                        its entry names the .venv's Python

Every line goes to the console as `installation: ...`. What the user must still do comes
at the end. Running it again repairs or adds; it never removes a Claude registration.
"""

from __future__ import annotations

import argparse
import glob
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional, Sequence

MINIMUM_PYTHON = (3, 11)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV = os.path.join(REPO_ROOT, ".venv")
VENV_PYTHON = os.path.join(VENV, "bin", "python")
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
CONFIG = os.path.join(REPO_ROOT, "bachmcp.toml")
MAX_NODE = "/Applications/Max.app/Contents/Resources/C74/packages/Node for Max/source/bin/osx/node/node"
NODE_PLACES = ("/opt/homebrew/bin/node", "/usr/local/bin/node", MAX_NODE)


class InstallError(Exception):
    """The installation cannot go on."""


def say(text: str) -> None:
    print(f"installation: {text}", flush=True)


def parse(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="bach install", add_help=False)
    for name in ("claude", "local"):
        parser.add_argument(f"--{name}", default="false")
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        raise InstallError(f"unknown argument: {' '.join(unknown)}")
    for name in ("claude", "local"):
        value = getattr(args, name).lower()
        if value not in ("true", "false"):
            raise InstallError(f"--{name} is true or false, not {value}")
        setattr(args, name, value == "true")
    if not (args.claude or args.local):
        raise InstallError("say what to install: --claude true, --local true, or both")
    return args


def in_venv() -> bool:
    return os.path.realpath(sys.prefix) == os.path.realpath(VENV)


def run(command: List[str], what: str) -> None:
    """A command whose output matters only if it fails."""
    done = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
    if done.returncode != 0:
        for line in done.stdout.strip().splitlines()[-15:]:
            say(f"  {line}")
        raise InstallError(what)


def make_venv() -> None:
    """A .venv that still runs is kept. One that does not (the package moved, its Python gone) is made again."""
    if os.path.exists(VENV_PYTHON):
        check = subprocess.run([VENV_PYTHON, "-c", ""], capture_output=True, check=False)
        if check.returncode == 0:
            say("venv already there")
            return
    run([sys.executable, "-m", "venv", "--clear", VENV], "could not create the venv")
    say("venv created")


def install_requirements(local: bool) -> None:
    pip = [VENV_PYTHON, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"]
    run(pip + ["-r", os.path.join(REPO_ROOT, "requirements.txt")], "could not install the requirements")
    if local:
        if apple_silicon():
            run(pip + ["-r", os.path.join(REPO_ROOT, "requirements-local.txt")], "could not install the requirements")
        else:  # no MLX here: gguf models only, for llama-server
            run(pip + ["huggingface-hub>=1.0"], "could not install the requirements")
    say("requirements installed")


def apple_silicon() -> bool:
    return sys.platform == "darwin" and platform.machine() == "arm64"


def find_node(current: str) -> Optional[str]:
    """Node.js: the one bachmcp.toml names if it is there, else one on the PATH, else one in the
    usual places. Max brings its own (Node for Max), so with Max installed there is always one."""
    named = current if os.path.isabs(current) else shutil.which(current or "node")
    if named and os.access(named, os.X_OK):
        return named
    found = shutil.which("node")
    return found or next((p for p in NODE_PLACES if os.access(p, os.X_OK)), None)


def set_node(node: str, path: str = CONFIG) -> None:
    """Set [algo] node in bachmcp.toml, keeping every comment."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    section, done = "", False
    for i, line in enumerate(lines):
        header = re.match(r"\s*\[([^\]]+)\]", line)
        if header:
            section = header.group(1).strip()
            continue
        key = re.match(r'(\s*node\s*=\s*)"[^"]*"', line)
        if section == "algo" and key:
            lines[i] = f'{key.group(1)}"{node}"{line[key.end():]}'
            done = True
    if not done:
        raise InstallError(f"could not find [algo] node in {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def bach_found() -> bool:
    """The bach package: next to this one, or in a Max Packages folder (this one may be a link to elsewhere)."""
    if os.path.isdir(os.path.join(os.path.dirname(REPO_ROOT), "bach")):
        return True
    return bool(glob.glob(os.path.expanduser("~/Documents/Max */Packages/bach")))


def setup_node(config, todo: List[str]) -> None:
    node = find_node(config.algo.node)
    if node is None:
        say("node path not found")
        todo.append('install Node.js, then set its path in bachmcp.toml: [algo] node = "/path/to/node"')
        return
    if node != config.algo.node:
        set_node(node)
    say("node path found")


def setup_claude(config, todo: List[str]) -> bool:
    """Claude Desktop and Claude Code. True if either was set up."""
    from bach_mcp import claude
    done = False
    app = os.path.isdir("/Applications/Claude.app") or os.path.isdir(os.path.dirname(claude.CLAUDE_DESKTOP_CONFIG))
    if not app:
        say("claude desktop not found")
        todo.append(f"install Claude Desktop, then run again: {command_line('install --claude true')}")
    else:
        try:
            claude.register_desktop()
            say("claude desktop set up")
            done = True
        except (OSError, ValueError) as exc:
            say("claude desktop not set up")
            todo.append(f"fix {claude.CLAUDE_DESKTOP_CONFIG} ({exc}), then run this again")
    add_line = claude.claude_code_commands(config)[0]
    try:
        registered = claude.register_code(config, claude.find_claude_code())
    except (OSError, ValueError) as exc:
        say("claude code not set up")
        todo.append(f"fix {claude.CLAUDE_CODE_CONFIG} ({exc}), then run: {add_line}")
    else:
        if registered:
            say("claude code set up")
            done = True
        else:
            say("claude code not found")
            todo.append(f"install Claude Code, then run: {add_line}")
    return done


def command_line(arguments: str) -> str:
    return f"{shlex.quote(VENV_PYTHON)} {shlex.quote(MAIN_PY)} {arguments}"


def second_stage(args: argparse.Namespace) -> None:
    from bach_mcp.config import load_config
    config = load_config("")
    todo: List[str] = []
    if not bach_found():
        todo.append("install the bach package from Max's Package Manager")
    setup_node(config, todo)
    restart = args.claude and setup_claude(config, todo)
    say("successful")
    for item in todo:
        say(f"to do: {item}")
    if args.local:
        say(f"to do: download a model: {command_line('download <name> --use')}")
        say(f"  the names: {command_line('models')}")
        if not apple_silicon():
            say("to do: this computer runs gguf models only: brew install llama.cpp")
    if restart:
        say("restart Claude to load Bach")
    modes = " or ".join(name for name, wanted in (("claude", args.claude), ("local", args.local)) if wanted)
    say(f"ready: launch using bachmcp.server {modes}")


def first_stage(args: argparse.Namespace, argv: Sequence[str]) -> int:
    if sys.version_info[:2] < MINIMUM_PYTHON:
        raise InstallError(f"Python {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]} or newer is needed, "
                           f"this is {platform.python_version()} ({sys.executable})")
    make_venv()
    install_requirements(args.local)
    return subprocess.run([VENV_PYTHON, MAIN_PY, "install", *argv], check=False).returncode


def main(argv: Sequence[str]) -> int:
    try:
        args = parse(argv)
        if in_venv():
            second_stage(args)
            return 0
        say("starting")
        say(" and ".join(name for name, wanted in (("local", args.local), ("claude", args.claude)) if wanted))
        return first_stage(args, argv)
    except InstallError as exc:
        say(f"failed: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 — Max shows this line; nothing else explains what happened
        say(f"failed: {type(exc).__name__}: {exc}")
        return 1


__all__ = ["main", "parse", "find_node", "set_node"]
