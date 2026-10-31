"""
backends.py
-----------
Starts the program that runs the local model, and stops it. Both backends are
servers that speak the OpenAI chat API; Bach starts them on an internal port
and only client.py talks to them.

    mlx    mlx_lm.server, Apple's MLX on the Mac's GPU (the mlx-lm package in this
           Python environment). Models: a folder of .safetensors weights.
    gguf   llama-server, from llama.cpp (`brew install llama.cpp`). Models: a .gguf file.

[model] model names a folder in models/ (download.py puts them there), a path,
or a Hugging Face repo, which the server downloads on its first start.
Everything the server prints goes to logs/model-server.log.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from typing import Iterator, List, Optional

from ..config import REPO_ROOT, Config, ConfigError

LOG_PATH = os.path.join(REPO_ROOT, "logs", "model-server.log")
ALIAS = "bach"  # the model's name in llama-server's API


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def command(config: Config, port: int) -> List[str]:
    """The command line that starts the model server of [model] on 127.0.0.1:port."""
    m, g = config.model, config.generation
    model = config.model_path
    if config.backend == "mlx":
        args = [sys.executable, "-m", "mlx_lm", "server", "--model", model,
                "--host", "127.0.0.1", "--port", str(port), "--max-tokens", str(g.max_tokens)]
    else:
        source = ["--model", model] if config.model_is_local or config.model_names_a_path else ["--hf-repo", model]
        args = ["llama-server", *source, "--host", "127.0.0.1", "--port", str(port), "--alias", ALIAS,
                "--ctx-size", str(m.context_size), "--parallel", "1", "--predict", str(g.max_tokens),
                "--jinja", "--no-webui"]
    return args + [str(a) for a in m.extra_args]


def tail(path: str, lines: int = 15) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return ""


class ModelServer:
    """The running model server: start(), wait_ready(), stop(). Its API is at base_url."""

    def __init__(self, config: Config, port: Optional[int] = None, log_path: str = LOG_PATH) -> None:
        config.check_model()
        self.config = config
        self.port = port or free_port()
        self.log_path = log_path
        self.process: Optional[subprocess.Popen] = None
        self._log = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    @property
    def request_model(self) -> Optional[str]:
        """The "model" field of a request: llama-server's alias; mlx_lm.server uses its own model without one."""
        return ALIAS if self.config.backend == "gguf" else None

    @property
    def label(self) -> str:
        return f"{self.config.model.model} ({self.config.backend})"

    def start(self) -> None:
        args = command(self.config, self.port)
        if args[0] == "llama-server" and not shutil.which("llama-server"):
            raise ConfigError("llama-server was not found: install llama.cpp (`brew install llama.cpp`) for GGUF models")
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        self._log = open(self.log_path, "w", encoding="utf-8")
        self.process = subprocess.Popen(args, stdout=self._log, stderr=subprocess.STDOUT)

    def wait_ready(self, timeout_seconds: float = 900.0) -> None:
        """Wait until the model is loaded (a first download can take long). Raises RuntimeError if the server stops."""
        started = time.time()
        while True:
            if self.process is None or self.process.poll() is not None:
                code = self.process.returncode if self.process else None
                raise RuntimeError(f"the model server stopped (exit code {code}). Last lines of "
                                   f"{os.path.relpath(self.log_path, REPO_ROOT)}:\n{tail(self.log_path)}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as response:
                    if response.status == 200:
                        return
            except OSError:
                pass
            if time.time() - started > timeout_seconds:
                raise RuntimeError(f"the model server is not ready after {timeout_seconds:.0f} s; "
                                   f"see {os.path.relpath(self.log_path, REPO_ROOT)}")
            time.sleep(1)

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
        log, self._log = self._log, None  # a quit and the door's own ending may both stop it
        if log is not None:
            log.close()


@contextlib.contextmanager
def running_model(config: Config, announce=print) -> Iterator[ModelServer]:
    """Start the model server of [model], wait until it is ready, and stop it afterwards."""
    server = ModelServer(config)
    announce(f"  model     {server.label}: starting (log: {os.path.relpath(server.log_path, REPO_ROOT)})")
    server.start()
    try:
        server.wait_ready()
        announce("  model     ready")
        yield server
    finally:
        server.stop()


__all__ = ["ModelServer", "running_model", "command", "free_port", "LOG_PATH"]
