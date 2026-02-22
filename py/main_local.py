"""Entrypoint for the Bach Ollama (Qwen) bridge."""

from __future__ import annotations

import os

from bach_mcp.ollama_bridge import OllamaBridge, BridgeConfig
from bach_mcp.ollama_utils import ensure_ollama_running, select_model

# Load the shared skill doc as the system prompt.
# Both the Claude path and the Qwen path now draw from the same BACH_SKILL.md
# so there is one single source of truth for all bach/llll knowledge.
_SKILL_PATH = os.path.join(os.path.dirname(__file__), "bach_mcp", "BACH_SKILL.md")

try:
    with open(_SKILL_PATH) as _f:
        _SYSTEM_PROMPT = _f.read()
except FileNotFoundError:
    raise RuntimeError(
        f"BACH_SKILL.md not found at {_SKILL_PATH}. "
        "Make sure the file exists inside the bach_mcp/ folder."
    )


def main() -> None:
    """Start Ollama if needed, select model, then run Qwen REPL."""
    config = BridgeConfig()
    config.system_prompt = _SYSTEM_PROMPT

    ensure_ollama_running(config.ollama_base_url)
    config.model = select_model(config.ollama_base_url)

    with OllamaBridge(config=config) as bridge:
        greeting = bridge.chat(
            "Introduce yourself in one sentence, starting with: I am ready"
        )
        print(f"\nBach: {greeting}\n")
        bridge._bach.send_info(f"bach_ready {greeting}")

        print("Type a message and press Enter. Ctrl-C to quit.\n")
        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                bridge._bach.send_info("bach_offline")
                break
            if not user_input:
                continue
            try:
                reply = bridge.chat(user_input)
                print(f"\nBach: {reply}\n")
            except RuntimeError as exc:
                print(f"[Error] {exc}")


if __name__ == "__main__":
    main()
