"""
ollama_utils.py
---------------
Ollama lifecycle and model management utilities for the Bach bridge.

Responsibilities:
- Start Ollama if not running
- Discover installed models
- Auto-select the best available Qwen model
- Prompt user to choose or pull a model when none are found
- Pull models with live progress output
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import List, Optional

import requests


# ── Known Qwen models ───────────────────────────────────────────────────── #
# Ordered by preference (best first). Any installed model from this list
# will be auto-selected. Add new variants here as Ollama releases them.

QWEN_MODELS: List[tuple[str, str]] = [
    # (ollama tag,                  human description)
    ("qwen2.5:72b-instruct",       "~47 GB  — flagship, best quality"),
    ("qwen2.5:72b",                "~47 GB  — flagship base"),
    ("qwen2.5:32b-instruct",       "~20 GB  — large, excellent quality"),
    ("qwen2.5:32b",                "~20 GB  — large base"),
    ("qwen2.5:14b-instruct",       "~9 GB   — recommended, great balance"),
    ("qwen2.5:14b",                "~9 GB   — 14B base"),
    ("qwen2.5:7b-instruct",        "~4 GB   — good balance"),
    ("qwen2.5:7b",                 "~4 GB   — 7B base"),
    ("qwen2.5:3b-instruct",        "~2 GB   — fast, lower quality"),
    ("qwen2.5:3b",                 "~2 GB   — 3B base"),
    ("qwen2.5:1.5b-instruct",      "~1 GB   — minimal"),
    ("qwen2.5:1.5b",               "~1 GB   — 1.5B base"),
    ("qwen2.5:0.5b-instruct",      "~400 MB — ultra-light"),
    ("qwen2.5:0.5b",               "~400 MB — 0.5B base"),
]

# Flat list of tags in preference order — used by BridgeConfig
QWEN_PREFERRED: List[str] = [tag for tag, _ in QWEN_MODELS]


# ── Logging ─────────────────────────────────────────────────────────────── #

def _log(msg: str) -> None:
    try:
        print(msg, file=sys.stderr)
    except Exception:
        pass


# ── Ollama server ───────────────────────────────────────────────────────── #

def ensure_ollama_running(
    base_url: str = "http://localhost:11434",
    wait_seconds: int = 20,
) -> None:
    """Ensure Ollama is running, starting it if necessary.

    Raises RuntimeError if Ollama cannot be started within wait_seconds.
    """
    if _ping_ollama(base_url):
        print("Ollama already running.")
        return

    print("Starting Ollama...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Ollama executable not found. "
            "Install it from https://ollama.com and make sure it is on your PATH."
        )

    for i in range(wait_seconds):
        time.sleep(1)
        if _ping_ollama(base_url):
            print("Ollama ready.")
            return
        if i > 0 and i % 5 == 0:
            print(f"  Still waiting for Ollama... ({i}s)")

    raise RuntimeError(
        f"Ollama did not become ready within {wait_seconds} seconds. "
        "Try running `ollama serve` manually and check for errors."
    )


def _ping_ollama(base_url: str, timeout: float = 3.0) -> bool:
    """Return True if Ollama is reachable."""
    try:
        requests.get(f"{base_url}/api/tags", timeout=timeout)
        return True
    except requests.exceptions.ConnectionError:
        return False


# ── Model discovery ──────────────────────────────────────────────────────── #

def get_installed_models(base_url: str = "http://localhost:11434") -> List[str]:
    """Return names of all models currently installed in Ollama."""
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=10)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception as exc:
        _log(f"[ollama_utils] Could not list models: {exc}")
        return []


def get_installed_qwen_models(base_url: str = "http://localhost:11434") -> List[str]:
    """Return installed models that appear in QWEN_PREFERRED, in preference order."""
    installed = set(get_installed_models(base_url))
    return [tag for tag in QWEN_PREFERRED if tag in installed]


# ── Model selection ──────────────────────────────────────────────────────── #

def select_model(base_url: str = "http://localhost:11434") -> str:
    """Show an interactive menu of all installed models and let the user choose.

    Always displays a menu — no silent auto-selection.
    Annotates Qwen models with size hints and marks the recommended default.
    Offers a pull option to download more models.

    Returns the selected model tag string.
    """
    installed_all = get_installed_models(base_url)

    if not installed_all:
        print("\nNo models installed in Ollama.")
        return _pull_menu(base_url)

    return _choice_menu(installed_all, base_url)


def _choice_menu(installed: List[str], base_url: str) -> str:
    """Display installed models as a numbered menu and return the chosen tag."""
    # Build a lookup from tag → description for known Qwen models
    qwen_info: dict[str, str] = {tag: desc for tag, desc in QWEN_MODELS}

    # Find the best installed Qwen model to mark as recommended
    installed_set = set(installed)
    recommended = next(
        (tag for tag in QWEN_PREFERRED if tag in installed_set), None
    )

    print("\n┌─────────────────────────────────────────────────────┐")
    print("│              Select a model to run Bach              │")
    print("├─────────────────────────────────────────────────────┤")

    def _size(tag: str) -> str:
        info = qwen_info.get(tag, "")
        return info.split("—")[0].strip() if info else ""

    col = max(len(m) for m in installed)
    for i, name in enumerate(installed, 1):
        size = _size(name)
        size_str = f"  {size}" if size else ""
        default_marker = "  <--" if name == recommended else ""
        print(f'| [{i:>2}] {name:<{col}}{size_str}{default_marker}')

    print("│")
    print("│  [p] Pull a new model from Ollama")
    print("└─────────────────────────────────────────────────────┘")

    default_idx = installed.index(recommended) + 1 if recommended else 1

    while True:
        prompt = f"Choose [{default_idx}]: " if recommended else "Choose: "
        raw = input(prompt).strip().lower()

        if raw == "":
            # Enter with no input → accept the recommended/default
            return installed[default_idx - 1]

        if raw == "p":
            return _pull_menu(base_url)

        if raw.isdigit() and 1 <= int(raw) <= len(installed):
            return installed[int(raw) - 1]

        print("  Invalid — enter a number, [p] to pull, or Enter for the default.")


def _pull_menu(base_url: str) -> str:
    """Show an interactive menu to pull a Qwen model and return its tag."""
    print("\nNo models installed. Choose a Qwen model to download:\n")
    _print_model_table(QWEN_MODELS)

    while True:
        choice = input("\nEnter model number to download: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(QWEN_MODELS):
            tag = QWEN_MODELS[int(choice) - 1][0]
            pull_model(tag)
            return tag
        print("  Invalid choice — try again.")


def _print_model_table(models: List[tuple[str, str]]) -> None:
    """Print a numbered table of (tag, description) pairs."""
    col = max(len(tag) for tag, _ in models)
    for i, (tag, desc) in enumerate(models, 1):
        print(f"  [{i:>2}] {tag:<{col}}  {desc}")


# ── Model pull ───────────────────────────────────────────────────────────── #

def pull_model(tag: str, base_url: str = "http://localhost:11434") -> None:
    """Pull a model from Ollama registry with live progress in the console.

    Uses the Ollama CLI so the user sees the same progress bar they would
    get from running `ollama pull` manually.

    Raises RuntimeError if the pull fails.
    """
    print(f"\nPulling {tag} — this may take several minutes...\n")
    try:
        result = subprocess.run(
            ["ollama", "pull", tag],
            check=False,  # we check returncode ourselves for a nicer message
        )
    except FileNotFoundError:
        raise RuntimeError("Ollama executable not found on PATH.")

    if result.returncode != 0:
        raise RuntimeError(
            f"Failed to pull model '{tag}' (exit code {result.returncode}). "
            "Check your internet connection and that the model tag is correct."
        )

    print(f"\nModel '{tag}' is ready.\n")


# ── Convenience: list and switch ─────────────────────────────────────────── #

def prompt_switch_model(base_url: str = "http://localhost:11434") -> Optional[str]:
    """Interactively switch to a different installed model.

    Returns the new model tag, or None if the user cancels.
    Useful for mid-session model switching in the REPL.
    """
    installed = get_installed_models(base_url)
    if not installed:
        print("No models installed.")
        return None

    print("\nInstalled models:")
    for i, name in enumerate(installed, 1):
        print(f"  [{i}] {name}")
    print("  [c] Cancel")

    while True:
        choice = input("Select model: ").strip().lower()
        if choice == "c":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(installed):
            return installed[int(choice) - 1]
        print("  Invalid choice — try again.")
