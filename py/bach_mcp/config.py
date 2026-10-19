"""
config.py
---------
Loads `bach.toml` and turns it into what each component needs: the
llama-server command line, the web chat's default settings, and the settings
of the MCP server.

One file is the single place to configure the model, the generation limits,
the chat and the tools. Unknown keys are rejected so a typo cannot be silently
ignored.
"""

from __future__ import annotations

import json
import os
import tomllib
from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Union

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_CONFIG_PATH = os.path.join(REPO_ROOT, "bach.toml")

MCP_SERVER_ID = "bach"
REASONING_VALUES = ("on", "off", "auto", "low", "medium", "high", "xhigh")


class ConfigError(ValueError):
    """A problem in bach.toml, phrased for the person editing it."""


@dataclass
class ModelConfig:
    backend: str = "llama"
    path: str = ""
    hf_repo: str = ""
    ollama_model: str = ""
    alias: str = "bach"
    context_size: int = 16384
    gpu_layers: Union[str, int] = "auto"


@dataclass
class GenerationConfig:
    max_tokens: int = 8192
    temperature: float = 0.4
    top_p: float = 0.9
    top_k: int = 40
    reasoning: str = "auto"
    reasoning_budget: int = 2048


@dataclass
class ChatConfig:
    skill_file: str = ""
    max_tool_rounds: int = 4
    tool_timeout_seconds: int = 60
    show_thinking: bool = True
    open_browser: bool = True
    docs: bool = True


@dataclass
class McpConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    toolset: str = "lean"
    verify_writes: bool = True
    tool_log: bool = True


@dataclass
class LlamaConfig:
    binary: str = "llama-server"
    host: str = "127.0.0.1"
    port: int = 8080
    parallel: int = 1
    extra_args: List[str] = field(default_factory=list)


@dataclass
class OllamaConfig:
    url: str = "http://127.0.0.1:11434"
    autostart: bool = True
    keep_alive: str = "30m"


@dataclass
class MaxConfig:
    send_port: int = 3000
    receive_port: int = 3001


@dataclass
class BachConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    mcp: McpConfig = field(default_factory=McpConfig)
    llama: LlamaConfig = field(default_factory=LlamaConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    max: MaxConfig = field(default_factory=MaxConfig)
    source: str = ""

    # ── Derived values ──────────────────────────────────────────────────── #

    @property
    def mcp_url(self) -> str:
        return f"http://{self.mcp.host}:{self.mcp.port}/mcp"

    @property
    def chat_url(self) -> str:
        return f"http://{self.llama.host}:{self.llama.port}"

    @property
    def uses_ollama(self) -> bool:
        return self.model.backend == "ollama"

    @property
    def has_model(self) -> bool:
        if self.uses_ollama:
            return bool(self.model.ollama_model)
        return bool(self.model.path or self.model.hf_repo)

    @property
    def model_label(self) -> str:
        if self.uses_ollama:
            return f"{self.model.ollama_model} (Ollama)"
        return self.model.path or self.model.hf_repo

    def apply_env(self) -> None:
        """Publish the settings that other modules read from the environment."""
        os.environ["BACH_TOOLSET"] = self.mcp.toolset
        os.environ["BACH_VERIFY"] = "1" if self.mcp.verify_writes else "0"
        os.environ["BACH_TOOL_LOG"] = "1" if self.mcp.tool_log else "0"

    def system_prompt(self) -> str:
        """The skill text: the configured file, else the built-in skill of the tool set."""
        if self.chat.skill_file:
            path = os.path.expanduser(self.chat.skill_file)
            if not os.path.isabs(path):
                path = os.path.join(REPO_ROOT, path)
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as exc:
                raise ConfigError(f"[chat] skill_file: cannot read {path} ({exc.strerror})") from None
        from .mcp_app import load_skill
        return load_skill(self.mcp.toolset)

    def llama_ui_args(self, port: int) -> List[str]:
        """Command line for a model-less llama-server that only serves the chat's files."""
        return [self.llama.binary, "--host", "127.0.0.1", "--port", str(port), "--no-models-autoload"]

    def llama_args(self, ui_config_path: str, port: int = 0) -> List[str]:
        """Command line for llama-server.

        port: run it on this internal port (127.0.0.1), behind the gateway; 0 = the [llama] host and port.
        """
        m, g, l = self.model, self.generation, self.llama
        host, port = ("127.0.0.1", port) if port else (l.host, l.port)
        args = [l.binary, "--host", host, "--port", str(port)]
        if m.path:
            args += ["--model", os.path.expanduser(m.path)]
        elif m.hf_repo:
            args += ["--hf-repo", m.hf_repo]
        args += [
            "--alias", m.alias,
            "--ctx-size", str(m.context_size),
            "--gpu-layers", str(m.gpu_layers),
            "--parallel", str(l.parallel),
            "--predict", str(g.max_tokens),
            "--temp", str(g.temperature),
            "--top-p", str(g.top_p),
            "--top-k", str(g.top_k),
            "--reasoning", g.reasoning if g.reasoning in ("off", "auto") else "on",
            "--reasoning-budget", str(g.reasoning_budget),
            "--jinja",
            "--ui-config-file", ui_config_path,
        ]
        return args + [str(a) for a in l.extra_args]

    def webui_settings(self) -> Dict[str, Any]:
        """Default settings for the llama.cpp web chat (its --ui-config-file).

        The chat applies these to every setting the user has not changed by hand
        in the browser. It expects the two MCP entries as JSON strings.
        """
        g, c = self.generation, self.chat
        settings: Dict[str, Any] = {
            "systemMessage": self.system_prompt(),
            "mcpServers": json.dumps([{
                "id": MCP_SERVER_ID,
                "enabled": True,
                "url": self.mcp_url,
                "name": "Bach",
                "requestTimeoutSeconds": c.tool_timeout_seconds,
            }]),
            # New chats start with the Bach tools switched on.
            "mcpDefaultServerOverrides": json.dumps([{"serverId": MCP_SERVER_ID, "enabled": True}]),
            "mcpRequestTimeoutSeconds": c.tool_timeout_seconds,
            "agenticMaxTurns": c.max_tool_rounds,
            "max_tokens": g.max_tokens,
            "temperature": g.temperature,
            "top_p": g.top_p,
            "top_k": g.top_k,
            "showSystemMessage": False,  # the skill is long; keep it out of the conversation view
            "showThoughtInProgress": c.show_thinking,
            "showToolCallInProgress": True,
        }
        if g.reasoning != "auto":
            settings["enableThinking"] = g.reasoning != "off"
        return settings


def _fill(section: Any, values: Any, name: str) -> None:
    if not isinstance(values, dict):
        raise ConfigError(f"[{name}] must be a table")
    known = {f.name: f for f in fields(section)}
    for key, value in values.items():
        if key not in known:
            raise ConfigError(f"[{name}] unknown key \"{key}\". Known keys: {', '.join(known)}")
        current = getattr(section, key)
        if isinstance(current, bool) != isinstance(value, bool):
            raise ConfigError(f"[{name}] {key} must be {'true or false' if isinstance(current, bool) else 'a value, not true/false'}")
        if isinstance(current, (int, float)) and not isinstance(current, bool) and key != "gpu_layers":
            if not isinstance(value, (int, float)):
                raise ConfigError(f"[{name}] {key} must be a number, got {value!r}")
            value = type(current)(value)
        elif isinstance(current, str) and key != "gpu_layers" and not isinstance(value, str):
            raise ConfigError(f"[{name}] {key} must be text in quotes, got {value!r}")
        elif isinstance(current, list) and not isinstance(value, list):
            raise ConfigError(f"[{name}] {key} must be a list, got {value!r}")
        setattr(section, key, value)


def load_config(path: str = "") -> BachConfig:
    """Load bach.toml. A missing default file yields the built-in defaults."""
    explicit = bool(path)
    path = os.path.expanduser(path) if path else DEFAULT_CONFIG_PATH
    config = BachConfig(source=path)
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

    sections = {f.name for f in fields(BachConfig)} - {"source"}
    for name, values in data.items():
        if name not in sections:
            raise ConfigError(f"unknown section [{name}]. Known sections: {', '.join(sorted(sections))}")
        _fill(getattr(config, name), values, name)

    g = config.generation
    if g.reasoning not in REASONING_VALUES:
        raise ConfigError(f"[generation] reasoning must be one of {', '.join(REASONING_VALUES)}; got {g.reasoning!r}")
    if config.model.backend not in ("llama", "ollama"):
        raise ConfigError(f"[model] backend must be \"llama\" or \"ollama\", got {config.model.backend!r}")
    if config.uses_ollama and not config.model.ollama_model:
        raise ConfigError("[model] backend is \"ollama\" but ollama_model is empty (e.g. \"qwen3.8:27b-mlx\")")
    config.ollama.url = config.ollama.url.rstrip("/")
    if config.mcp.toolset not in ("lean", "full"):
        raise ConfigError(f"[mcp] toolset must be \"lean\" or \"full\", got {config.mcp.toolset!r}")
    if config.model.path and config.model.hf_repo:
        raise ConfigError("[model] give either path or hf_repo, not both")
    if config.model.path and not os.path.isfile(os.path.expanduser(config.model.path)):
        raise ConfigError(f"[model] path does not exist: {config.model.path}")
    if config.model.path and not config.model.path.lower().endswith(".gguf"):
        raise ConfigError("[model] path must be a .gguf file (llama.cpp cannot load Ollama or MLX models)")
    if 0 < g.max_tokens >= config.model.context_size:
        raise ConfigError("[generation] max_tokens must be smaller than [model] context_size")
    return config
