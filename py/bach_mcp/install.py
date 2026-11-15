"""
install.py
----------
`main.py install --claude true --local true`: sets Bach up inside its Max package.
At least one of the two must be true; the one not given is false.

It starts on whatever Python the shell has, with nothing installed, so it imports only
the standard library, and only at the top. Two stages:

    outside the .venv   checks Python, makes the .venv, installs the requirements (and
                        requirements-audio.txt, for buffer instances, whichever the mode),
                        then runs this same command again with the .venv's Python
    inside the .venv    the Node path, ONNX Runtime for the externals bachmcp.onnx~ and bachmcp.onnxb~
                        (into support/), the sound models (said to download if missing) and Claude. Claude is
                        registered from here so that its entry names the .venv's Python; Claude Code's login is checked

Every line goes to the console as `installation: ...`. What the user must still do comes
at the end. Running it again repairs or adds; it never removes a Claude registration.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from typing import List, Optional, Sequence

MINIMUM_PYTHON = (3, 11)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VENV = os.path.join(REPO_ROOT, ".venv")
VENV_PYTHON = os.path.join(VENV, "bin", "python")
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
CONFIG = os.path.join(REPO_ROOT, "bachmcp.toml")
MAX_NODE = "/Applications/Max.app/Contents/Resources/C74/packages/Node for Max/source/bin/osx/node/node"
NODE_PLACES = ("/opt/homebrew/bin/node", "/usr/local/bin/node", MAX_NODE)

# ONNX Runtime, which bachmcp.onnx~ and bachmcp.onnxb~ load from support/ (next to their core,
# libbachmcp.onnx.dylib, which is in the repository): 47 MB, so fetched here rather than kept in git.
# Pinned: the same version as sources/bachmcp.onnx/CMakeLists.txt (ORT_VERSION) builds against.
SUPPORT = os.path.join(REPO_ROOT, "support")
ORT_VERSION = "1.32.0"
ORT_URL = (f"https://github.com/microsoft/onnxruntime/releases/download/v{ORT_VERSION}/"
           f"onnxruntime-osx-arm64-{ORT_VERSION}.tgz")
ORT_ARCHIVE_SHA256 = "8ddca23f532b9d4fbb279ba9b08dab6c0ac94fdc9aec2eb44a1db7049216c043"
ORT_DYLIB_SHA256 = "51c5a25a3dfafd74f62f403e6e0dc7881d97c0e627c703a4d9548c5677abc8fd"
ORT_DYLIB = os.path.join(SUPPORT, "libonnxruntime.1.dylib")  # the name the core asks for (@rpath/...)


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
    """One pip run for all of them: the pins of requirements.txt and requirements-local.txt and
    the open versions of requirements-audio.txt are resolved together, so none undoes another."""
    wanted = ["-r", os.path.join(REPO_ROOT, "requirements.txt"), "-r", os.path.join(REPO_ROOT, "requirements-audio.txt")]
    if local:
        if apple_silicon():
            wanted += ["-r", os.path.join(REPO_ROOT, "requirements-local.txt")]
        else:  # no MLX here: gguf models only, for llama-server
            wanted += ["huggingface-hub>=1.0"]
    say("installing the requirements (librosa and the sound models' runtimes among them: a few minutes the first time)")
    run([VENV_PYTHON, "-m", "pip", "install", "--quiet", "--disable-pip-version-check"] + wanted,
        "could not install the requirements")
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
    from bach_mcp.config import ConfigError, set_key  # second stage: inside the .venv
    try:
        set_key(path, "algo", "node", node)
    except ConfigError:
        raise InstallError(f"could not find [algo] node in {path}") from None


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
    check_login(todo)
    return done


def check_login(todo: List[str]) -> None:
    """Prompts from Max run through Claude Code, which needs a login of its own, apart from Claude Desktop's."""
    from bach_mcp import claude
    command = claude.find_claude_code()
    if command is None:
        return  # setup_claude has already said to install it
    state = claude.logged_in(command)
    if state:
        say("claude code logged in")
        return
    say("claude code not logged in" if state is False else "claude code login not checked")
    todo.append(f"to prompt Claude from Max, log in to Claude Code, in a terminal: {claude.login_command(command)}")


def sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def setup_onnx_runtime(todo: List[str], url: str = ORT_URL, archive_sha256: str = ORT_ARCHIVE_SHA256,
                       dylib_sha256: str = ORT_DYLIB_SHA256, folder: str = SUPPORT) -> None:
    """support/: ONNX Runtime's dylib (and its licence) for the externals, the pinned version, checked;
    nothing fetched when the right one is already there. Apple Silicon only (Microsoft ships macOS for arm64)."""
    if not apple_silicon():
        say("onnx runtime skipped (bachmcp.onnx~ and bachmcp.onnxb~ need Apple Silicon)")
        return
    dylib = os.path.join(folder, os.path.basename(ORT_DYLIB))
    if os.path.isfile(dylib) and sha256(dylib) == dylib_sha256:
        say("onnx runtime found")
        return
    os.makedirs(folder, exist_ok=True)
    say(f"downloading onnx runtime {ORT_VERSION} (47 MB, for bachmcp.onnx~ and bachmcp.onnxb~)")
    try:
        with tempfile.TemporaryDirectory(prefix="bachmcp-ort-") as tmp:
            archive = os.path.join(tmp, "ort.tgz")
            with urllib.request.urlopen(url, timeout=60) as r, open(archive, "wb") as f:
                shutil.copyfileobj(r, f)
            if sha256(archive) != archive_sha256:
                raise InstallError("the download is not the archive expected (its SHA-256 differs)")
            with tarfile.open(archive) as tar:
                root = tar.getnames()[0].split("/")[0]
                wanted = {f"{root}/lib/libonnxruntime.{ORT_VERSION}.dylib": dylib,
                          f"{root}/LICENSE": os.path.join(folder, "onnxruntime-LICENSE.txt"),
                          f"{root}/ThirdPartyNotices.txt": os.path.join(folder, "onnxruntime-ThirdPartyNotices.txt")}
                for member, target in wanted.items():
                    source = tar.extractfile(member)
                    if source is None:
                        raise InstallError(f"{member} is not in the archive")
                    with source, open(target + ".part", "wb") as out:
                        shutil.copyfileobj(source, out)
                    os.replace(target + ".part", target)
        if sha256(dylib) != dylib_sha256:
            raise InstallError("the dylib is not the one expected (its SHA-256 differs)")
        os.chmod(dylib, 0o755)
        say("onnx runtime installed")
    except (OSError, InstallError, tarfile.TarError) as exc:
        say("onnx runtime not installed")
        todo.append(f"bachmcp.onnx~ and bachmcp.onnxb~ need ONNX Runtime in support/ ({exc}); run install again")


def check_sound_models(config, todo: List[str]) -> None:
    """The tagger and CLAP of [audio], which describe the sound of buffer instances: downloaded apart, by name."""
    from bach_mcp.utilities.download import audio_downloaded
    if not config.audio.sound_analysis:
        return  # [audio] sound_analysis = false: nothing reads them
    missing = [name for name, ok in audio_downloaded(config).items() if not ok]
    if not missing:
        say("sound models found")
        return
    say("sound models not downloaded")
    for name in missing:
        todo.append(f"to describe sounds to the model (buffer instances), download {name}: "
                    f"{command_line(f'download {name}')}")
    if config.audio.clap_model in missing and config.audio.clap_model != "laion-clap-small":
        todo.append("  (or the lighter CLAP: download laion-clap-small --use)")


def command_line(arguments: str) -> str:
    return f"{shlex.quote(VENV_PYTHON)} {shlex.quote(MAIN_PY)} {arguments}"


def second_stage(args: argparse.Namespace) -> None:
    from bach_mcp.config import load_config
    config = load_config("")
    todo: List[str] = []
    if not bach_found():
        todo.append("install the bach package from Max's Package Manager")
    setup_node(config, todo)
    setup_onnx_runtime(todo)
    check_sound_models(config, todo)
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
