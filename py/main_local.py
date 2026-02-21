"""Entrypoint for the Bach Ollama (Qwen) bridge."""

from bach_mcp.ollama_bridge import OllamaBridge, BridgeConfig
from bach_mcp.ollama_utils import ensure_ollama_running, select_model


def main() -> None:
    """Start Ollama if needed, select model, then run Qwen REPL."""
    config = BridgeConfig()
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
