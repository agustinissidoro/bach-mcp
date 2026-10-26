"""
config.py
---------
bachmcp.toml -> one Config object. It is read once, by main.py, and handed down:
no other module reads bachmcp.toml or the environment for its settings.

    [model]       which model runs locally; its runtime (mlx or gguf) follows from the model
    [generation]  reply limit, sampling, reasoning: sent with every request
    [chat]        the skill, tool rounds per answer, instrument docs, the browser
    [server]      Bach's own address: the chat page and /mcp; tool logging
    [max]         the UDP ports of the patch
    [algo]        the Node.js that checks algorithms

Where files go is not set here: the patch sends the playground (set_playground).

Unknown keys are rejected, so a typo cannot be silently ignored. The model
settings are checked only when a model is started: Claude's door never
depends on them.

Models live in models/ at the root of the repository, one folder per model
(`python py/main.py download <repo>` puts them there). [model] model can name
one of them, give any path, or name a Hugging Face repo.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from typing import Any, List, Optional

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONFIG_PATH = os.path.join(REPO_ROOT, "bachmcp.toml")
MODELS_DIR = os.path.join(REPO_ROOT, "models")

BACKENDS = ("mlx", "gguf")
REASONING = ("off", "on")


class ConfigError(ValueError):
    """A problem in bachmcp.toml, phrased for the person editing it."""


@dataclass
class ModelConfig:
    model: str = ""                  # a folder in models/, a path, or a Hugging Face repo
    context_size: int = 65536        # gguf: memory reserved for the conversation (mlx grows as needed)
    extra_args: List[str] = field(default_factory=list)


@dataclass
class GenerationConfig:
    max_tokens: int = 16384
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    presence_penalty: float = 1.5
    reasoning: str = "off"


@dataclass
class ChatConfig:
    skill_file: str = ""
    max_tool_rounds: int = 8
    docs: bool = True
    open_browser: bool = True


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8090
    tool_log: bool = True


@dataclass
class MaxConfig:
    send_port: int = 3000
    receive_port: int = 3001


@dataclass
class AlgoConfig:
    node: str = "node"


# Keys that are gone, and what took their place.
_REMOVED = {
    ("model", "backend"): "Bach reads it from the model",
    ("max", "buffer"): "each instance has its own file in the playground (set_playground from the patch)",
    ("algo", "dir"): "algorithms go to the playground (set_playground from the patch)",
}


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    max: MaxConfig = field(default_factory=MaxConfig)
    algo: AlgoConfig = field(default_factory=AlgoConfig)
    source: str = ""

    # ── Derived values ──────────────────────────────────────────────────── #

    @property
    def url(self) -> str:
        """Where Bach answers: the chat page at /, the tools at /mcp."""
        return f"http://{self.server.host}:{self.server.port}"

    @property
    def mcp_url(self) -> str:
        return f"{self.url}/mcp"

    @property
    def model_path(self) -> str:
        """[model] model as the model server gets it: a local folder or file if there is one
        (in models/, or the path given), else the Hugging Face repo as written."""
        value = self.model.model.strip()
        if not value:
            return ""
        for candidate in (os.path.join(MODELS_DIR, value), _from_repo(value)):
            if os.path.exists(candidate):
                if os.path.isdir(candidate) and model_format(candidate) == "gguf":
                    return gguf_in(candidate)
                return candidate
        return _from_repo(value) if self.model_names_a_path else value

    @property
    def model_names_a_path(self) -> bool:
        """[model] model is written as a path (not a Hugging Face repo), whether or not it exists."""
        value = self.model.model.strip()
        return value.startswith(("/", "~", ".", "models/")) or value.lower().endswith(".gguf")

    @property
    def backend(self) -> str:
        """The runtime the model needs, read from the model itself, so it is never set by hand:
        "gguf" for a .gguf file or a folder with one, or a repo named GGUF or with a :QUANT;
        "mlx" for a folder of .safetensors weights, or any other repo."""
        if self.model_is_local:
            return model_format(self.model_path) or "mlx"
        value = self.model.model.strip()
        return "gguf" if ":" in value or "gguf" in value.lower() else "mlx"

    @property
    def model_is_local(self) -> bool:
        return bool(self.model_path) and os.path.exists(self.model_path)

    def skill_source(self) -> str:
        """The skill file as it is, with its mode markers: [chat] skill_file, else the built-in one."""
        from .prompt.skill import read_skill
        if not self.chat.skill_file:
            return read_skill()
        path = _from_repo(self.chat.skill_file)
        try:
            return read_skill(path)
        except OSError as exc:
            raise ConfigError(f"[chat] skill_file: cannot read {path} ({exc.strerror})") from None

    def system_prompt(self, mode: Optional[str] = None) -> str:
        """The skill for a mode ("score" or "algo", see prompt/modes.py), or all of it."""
        from .prompt.skill import skill_for
        return skill_for(self.skill_source(), mode)

    def check_model(self) -> None:
        """Raise ConfigError if [model] cannot start a model. Called only when one is started."""
        m = self.model
        if not m.model.strip():
            raise ConfigError("no model: [model] model in bachmcp.toml is empty. Get one with "
                              "`python py/main.py download <repo> --use`, or name a folder in models/")
        if self.model_is_local:
            if model_format(self.model_path) not in BACKENDS:
                raise ConfigError(f"{m.model} holds no model: no .safetensors (mlx) or .gguf (gguf) file in it")
        elif self.model_names_a_path:
            raise ConfigError(f"[model] model: no such file or folder {m.model} (models are in {MODELS_DIR})")
        if self.backend == "gguf" and self.generation.max_tokens >= m.context_size:
            raise ConfigError("[generation] max_tokens must be smaller than [model] context_size")


def model_format(path: str) -> str:
    """ "mlx" for a folder with .safetensors weights, "gguf" for a .gguf file or a folder with one, else ""."""
    if os.path.isfile(path):
        return "gguf" if path.lower().endswith(".gguf") else ""
    if not os.path.isdir(path):
        return ""
    names = os.listdir(path)
    if any(n.endswith(".safetensors") for n in names):
        return "mlx"
    if any(n.lower().endswith(".gguf") for n in names):
        return "gguf"
    return ""


def gguf_in(folder: str) -> str:
    """The .gguf file llama-server loads from a folder: the first part of a split model, or the only file."""
    files = sorted(n for n in os.listdir(folder) if n.lower().endswith(".gguf") and "mmproj" not in n.lower())
    return os.path.join(folder, files[0]) if files else folder


def _from_repo(path: str) -> str:
    """A path from bachmcp.toml: absolute as it is, otherwise relative to the repository."""
    path = os.path.expanduser(path)
    return path if os.path.isabs(path) else os.path.join(REPO_ROOT, path)


def _fill(section: Any, values: Any, name: str) -> None:
    if not isinstance(values, dict):
        raise ConfigError(f"[{name}] must be a table")
    known = {f.name: f for f in fields(section)}
    for key, value in values.items():
        if (name, key) in _REMOVED:
            raise ConfigError(f"[{name}] {key} is no longer set: {_REMOVED[name, key]}. Remove that line")
        if key not in known:
            raise ConfigError(f"[{name}] unknown key \"{key}\". Known keys: {', '.join(known)}")
        current = getattr(section, key)
        if isinstance(current, bool) != isinstance(value, bool):
            raise ConfigError(f"[{name}] {key} must be {'true or false' if isinstance(current, bool) else 'a value, not true/false'}")
        if isinstance(current, (int, float)) and not isinstance(current, bool):
            if not isinstance(value, (int, float)):
                raise ConfigError(f"[{name}] {key} must be a number, got {value!r}")
            value = type(current)(value)
        elif isinstance(current, str) and not isinstance(value, str):
            raise ConfigError(f"[{name}] {key} must be text in quotes, got {value!r}")
        elif isinstance(current, list) and not isinstance(value, list):
            raise ConfigError(f"[{name}] {key} must be a list, got {value!r}")
        setattr(section, key, value)


def load_config(path: str = "") -> Config:
    """Load bachmcp.toml. A missing default file yields the built-in defaults."""
    explicit = bool(path)
    path = os.path.expanduser(path) if path else DEFAULT_CONFIG_PATH
    config = Config(source=path)
    if not os.path.exists(path):
        if explicit:
            raise ConfigError(f"config file not found: {path}")
        config.source = "(built-in defaults)"
        return config
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"{path}: {exc}") from None

    sections = {f.name for f in fields(Config)} - {"source"}
    for name, values in data.items():
        if name not in sections:
            raise ConfigError(f"unknown section [{name}]. Known sections: {', '.join(sorted(sections))}")
        _fill(getattr(config, name), values, name)

    if config.generation.reasoning not in REASONING:
        raise ConfigError(f"[generation] reasoning must be \"off\" or \"on\", got {config.generation.reasoning!r}")
    return config


__all__ = ["Config", "ConfigError", "load_config", "model_format", "REPO_ROOT", "MODELS_DIR", "BACKENDS"]
