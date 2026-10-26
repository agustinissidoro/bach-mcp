"""
download.py
-----------
Puts models in models/ (at the root of the repository), one folder per model.
A model can be named four ways:

    qwen3.8-27b                                    a name from models/catalog.toml
    mlx-community/Qwen3.8-27B-4bit                 a Hugging Face repo: MLX takes the whole repo
    unsloth/Qwen3.8-27B-GGUF:Q4_K_M                ... GGUF takes the file(s) of one quantization
    https://huggingface.co/<user>/<repo>[/blob/main/<file>]   a Hugging Face page, or one file in it
    https://<anywhere>/<model>.gguf                a direct link to a .gguf file

From the terminal: `python py/main.py download <name> [--use]` and `models`.
From Max: `bach download_model <name> [use]` (status.py), which runs a
DownloadJob: the download in its own process, reporting its progress.

A download that stops can be started again: it goes on where it was.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import time
import tomllib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ..config import DEFAULT_CONFIG_PATH, MODELS_DIR, REPO_ROOT, Config, ConfigError, model_format

DEFAULT_QUANT = "Q4_K_M"  # what llama-server also picks when a GGUF repo names no quantization
MAIN_PY = os.path.join(REPO_ROOT, "py", "main.py")
LOG_PATH = os.path.join(REPO_ROOT, "logs", "download.log")
_HF_URL = re.compile(r"^https?://(?:www\.)?(?:huggingface\.co|hf\.co)/([^/\s]+/[^/\s]+)(?:/(?:blob|resolve|tree)/[^/\s]+/?(\S*))?/?$")


# ── What is in models/ ──────────────────────────────────────────────────── #

@dataclass
class ModelInfo:
    name: str     # the folder in models/, which is what [model] model can say
    format: str   # "mlx", "gguf" or "" (not a model)
    size: int     # bytes
    path: str

    @property
    def gigabytes(self) -> str:
        return f"{self.size / 1e9:.1f} GB"


def _size(path: str) -> int:
    if os.path.isfile(path):
        return os.path.getsize(path)
    return sum(os.path.getsize(os.path.join(d, f)) for d, _, files in os.walk(path) for f in files)


def list_models(folder: Optional[str] = None) -> List[ModelInfo]:
    """Every model in models/ (or in folder), by name."""
    folder = folder or MODELS_DIR
    if not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.startswith(".") or (os.path.isfile(path) and not name.lower().endswith(".gguf")):
            continue  # README.md, catalog.toml
        out.append(ModelInfo(name, model_format(path), _size(path), path))
    return out


def in_use(info: ModelInfo, config: Config) -> bool:
    """Whether [model] model is this model (its folder, or a file in it)."""
    if not config.model_is_local:
        return False
    used, path = os.path.realpath(config.model_path), os.path.realpath(info.path)
    return used == path or used.startswith(path + os.sep)


# ── The catalogue: models known by name ─────────────────────────────────── #

@dataclass
class CatalogEntry:
    name: str
    repo: str       # "user/repo", with ":QUANT" for a GGUF quantization
    format: str
    size_gb: float
    note: str

    @property
    def folder(self) -> str:
        """The folder its download goes to, in models/ (the repo's name)."""
        return self.repo.split(":")[0].split("/")[-1]

    def downloaded(self, folder: Optional[str] = None) -> bool:
        return os.path.isdir(os.path.join(folder or MODELS_DIR, self.folder))


def load_catalog(path: Optional[str] = None) -> Dict[str, CatalogEntry]:
    path = path or os.path.join(MODELS_DIR, "catalog.toml")
    if not os.path.exists(path):
        return {}
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return {name.lower(): CatalogEntry(name, str(v["repo"]), str(v.get("format", "")), float(v.get("size_gb", 0)),
                                       str(v.get("note", "")))
            for name, v in data.items()}


# ── Naming a model, and what its download fetches ───────────────────────── #

@dataclass
class Plan:
    spec: str                    # what was asked for, as written
    name: str                    # the folder it goes to, in models/
    format: str                  # "mlx" or "gguf"
    size: int                    # bytes to fetch
    repo: str = ""               # a Hugging Face repo ...
    files: Optional[List[str]] = None   # ... and its files to fetch (None: all of them)
    url: str = ""                # or a direct link to one .gguf file

    def target(self, folder: Optional[str] = None) -> str:
        return os.path.join(folder or MODELS_DIR, self.name)


def parse(spec: str, catalog: Optional[Dict[str, CatalogEntry]] = None) -> Dict[str, Optional[str]]:
    """What a name points at: {"repo", "quant", "file", "url"}. Pure: no network."""
    text = spec.strip().strip('"')
    entry = (load_catalog() if catalog is None else catalog).get(text.lower())
    if entry is not None:
        text = entry.repo
    found = _HF_URL.match(text)
    if found:
        return {"repo": found.group(1), "quant": None, "file": found.group(2) or None, "url": None}
    if re.match(r"^https?://", text):
        if not text.split("?")[0].lower().endswith(".gguf"):
            raise ConfigError(f"{spec}: a link outside Hugging Face must point at a .gguf file")
        return {"repo": None, "quant": None, "file": None, "url": text}
    repo, _, quant = text.partition(":")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise ConfigError(f"{spec}: not a model name from models/catalog.toml, a Hugging Face repo "
                          "(user/repo[:QUANT]) or a link")
    return {"repo": repo, "quant": quant or None, "file": None, "url": None}


def gguf_files(files: List[str], quant: Optional[str] = None) -> List[str]:
    """The .gguf files of one quantization in a repo's file list: all parts of a split model.
    Without a quantization: the only one, else Q4_K_M. Raises ConfigError when it cannot choose."""
    ggufs = [f for f in files if f.lower().endswith(".gguf") and "mmproj" not in f.lower()]
    if not ggufs:
        raise ConfigError("the repo has no .gguf file")
    if not quant and len(ggufs) == 1:
        return ggufs
    wanted = (quant or DEFAULT_QUANT).upper()
    match = re.compile(rf"(?<![A-Z0-9]){re.escape(wanted)}(?![A-Z0-9_])")
    chosen = sorted(f for f in ggufs if match.search(os.path.basename(f).upper()))
    if not chosen:
        found = sorted({m.group(0) for f in ggufs for m in [re.search(r"(?:I?Q\d[A-Z0-9_]*|F16|BF16|F32)", f.upper())] if m})
        raise ConfigError(f"no {wanted} file in the repo; it has: {', '.join(found) or ', '.join(ggufs)}. "
                          "Name one after the repo, e.g. user/repo:Q5_K_M")
    return chosen


def make_plan(spec: str, catalog: Optional[Dict[str, CatalogEntry]] = None) -> Plan:
    """Ask Hugging Face (or the link) what the download of `spec` would fetch."""
    where = parse(spec, catalog)
    if where["url"]:
        import httpx
        url = where["url"]
        try:
            size = int(httpx.head(url, follow_redirects=True, timeout=20).headers.get("content-length", 0))
        except Exception as exc:
            raise ConfigError(f"cannot reach {url}: {exc}") from None
        file = os.path.basename(url.split("?")[0])
        return Plan(spec, file[:-5], "gguf", size, url=url)
    from huggingface_hub import HfApi
    repo = where["repo"]
    try:
        info = HfApi().model_info(repo, files_metadata=True)
    except Exception as exc:  # not found, private, no network: say which, in one line
        reason = str(exc).splitlines()[0].split(" (Request ID")[0]
        raise ConfigError(f"cannot read {repo} on Hugging Face: {reason}") from None
    sizes = {s.rfilename: (s.size or 0) for s in info.siblings or []}
    name = repo.split("/")[-1]
    if where["file"]:
        if where["file"] not in sizes:
            raise ConfigError(f"{repo} has no file {where['file']}")
        files = [where["file"]]
        fmt = "gguf" if where["file"].lower().endswith(".gguf") else "mlx"
        return Plan(spec, name, fmt, sizes[where["file"]], repo=repo, files=files)
    if any(n.endswith(".safetensors") for n in sizes):
        return Plan(spec, name, "mlx", sum(sizes.values()), repo=repo)
    files = gguf_files(list(sizes), where["quant"])
    return Plan(spec, name, "gguf", sum(sizes[n] for n in files), repo=repo, files=files)


# ── Fetching ────────────────────────────────────────────────────────────── #

def fetch(plan: Plan, folder: Optional[str] = None) -> ModelInfo:
    """Download what the plan says into models/<name>/ and return what is there."""
    target = plan.target(folder)
    try:
        if plan.url:
            _fetch_url(plan.url, target)
        else:
            from huggingface_hub import snapshot_download
            snapshot_download(plan.repo, local_dir=target, allow_patterns=plan.files)
    except Exception as exc:
        raise RuntimeError(f"the download stopped ({str(exc).splitlines()[0]}); start it again to go on") from None
    return ModelInfo(plan.name, model_format(target), _size(target), target)


def _fetch_url(url: str, target: str) -> None:
    """One file from a link, into target/, going on from a part already there."""
    import httpx
    os.makedirs(target, exist_ok=True)
    path = os.path.join(target, os.path.basename(url.split("?")[0]))
    part = path + ".incomplete"
    have = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    with httpx.stream("GET", url, headers=headers, follow_redirects=True, timeout=httpx.Timeout(60, connect=20)) as r:
        r.raise_for_status()
        with open(part, "ab" if r.status_code == 206 else "wb") as f:
            for block in r.iter_bytes(1 << 20):
                f.write(block)
    os.replace(part, path)


def download(spec: str, folder: Optional[str] = None, announce=print) -> ModelInfo:
    """Plan and fetch, saying first what is coming (the terminal's `download`)."""
    plan = make_plan(spec)
    what = plan.url or plan.repo
    files = f"{len(plan.files)} file(s)" if plan.files else ("1 file" if plan.url else "the whole repo")
    announce(f"Downloading {what} ({plan.format}, {files}, {plan.size / 1e9:.1f} GB) "
             f"into {os.path.relpath(plan.target(folder), REPO_ROOT)}")
    return fetch(plan, folder)


class DownloadJob:
    """A download in its own process (so it can be stopped, and prints nothing into Bach), watched:
    on_progress(done_bytes, total_bytes) every `every` seconds, then on_done(ModelInfo) or
    on_error(message). stop() ends it; what was fetched stays, and a new start goes on from there.

    Progress is what has reached models/<name>/. Hugging Face's Xet storage writes a file only
    when it is whole, so the job switches Xet off: files then grow on disk as they arrive."""

    def __init__(self, plan: Plan, on_progress: Callable[[int, int], None], on_done: Callable[[ModelInfo], None],
                 on_error: Callable[[str], None], every: float = 2.0, folder: Optional[str] = None,
                 command: Optional[List[str]] = None, log_path: str = LOG_PATH) -> None:
        self.plan = plan
        self.target = plan.target(folder)
        self.on_progress, self.on_done, self.on_error = on_progress, on_done, on_error
        self.every = every
        self.command = command or [sys.executable, MAIN_PY, "download", plan.spec]
        self.log_path = log_path
        self.process: Optional[subprocess.Popen] = None
        self.stopped = False

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def start(self) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        log = open(self.log_path, "w", encoding="utf-8")
        env = {**os.environ, "HF_HUB_DISABLE_XET": "1"}
        self.process = subprocess.Popen(self.command, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env)
        log.close()
        threading.Thread(target=self._watch, daemon=True).start()

    def stop(self) -> None:
        self.stopped = True
        if self.running:
            self.process.terminate()

    def done_bytes(self) -> int:
        return min(_size(self.target), self.plan.size) if os.path.exists(self.target) else 0

    def _watch(self) -> None:
        assert self.process is not None
        while self.process.poll() is None:
            self.on_progress(self.done_bytes(), self.plan.size)
            time.sleep(self.every)
        if self.stopped:
            self.on_error("stopped")
        elif self.process.returncode == 0 and model_format(self.target):
            self.on_done(ModelInfo(self.plan.name, model_format(self.target), _size(self.target), self.target))
        else:
            self.on_error(_last_line(self.log_path) or f"the download ended with code {self.process.returncode}")


def _last_line(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [line.strip() for line in f.read().replace("\r", "\n").split("\n") if line.strip()]
        return lines[-1] if lines else ""
    except OSError:
        return ""


# ── Setting the model in bachmcp.toml ──────────────────────────────────────── #

def use_in_config(info: ModelInfo, path: str = DEFAULT_CONFIG_PATH) -> None:
    """Set [model] model in bachmcp.toml to this model, keeping every comment (the runtime follows from it)."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    section, done = "", set()
    for i, line in enumerate(lines):
        header = re.match(r"\s*\[([^\]]+)\]", line)
        if header:
            section = header.group(1).strip()
            continue
        key = re.match(r'(\s*model\s*=\s*)"[^"]*"', line)
        if section == "model" and key:
            lines[i] = f'{key.group(1)}"{info.name}"{line[key.end():]}'
            done.add("model")
    if not done:
        raise ConfigError(f"could not find [model] model in {path}: set it by hand")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


__all__ = ["ModelInfo", "list_models", "in_use", "CatalogEntry", "load_catalog", "Plan", "parse", "gguf_files",
           "make_plan", "fetch", "download", "DownloadJob", "use_in_config"]
