"""Bach's command line. Everything is configured in bachmcp.toml.

    run      the local model: starts the model (mlx or gguf, as the model is), the
             bridge to Max and the chat page, and opens the page. run.command does this.
    serve    the tools for Claude, or another MCP host: --stdio when the host starts
             Bach itself (Claude Desktop), HTTP at [server] otherwise.
    agent    the local model in the terminal: the same engine as the chat page.
    eval     the evaluation suite against the local model (Max is not needed).
    claude   adds Bach to Claude Desktop, and prints the line that adds it to Claude Code.
    download puts a model in models/: a name from models/catalog.toml, a Hugging Face repo,
             or a link (--use: and sets it in bachmcp.toml).
    models   lists the models in models/, and the ones the catalogue knows by name.

Usage:
    python py/main.py run
    python py/main.py serve --stdio
    python py/main.py download qwen3.8-27b --use
    python py/main.py download unsloth/Qwen3.8-27B-GGUF:Q4_K_M
    python py/main.py download https://huggingface.co/mlx-community/Qwen3-8B-4bit
    python py/main.py eval --runs 3 --case neapolitan,trio
    python py/main.py run --config other.toml
"""

from __future__ import annotations

import argparse
import sys

from bach_mcp.bridge.max import BridgeBusy
from bach_mcp.config import ConfigError, load_config


def main() -> None:
    parser = argparse.ArgumentParser(prog="bach", description="Bach: compose in bach.roll with a model.")
    parser.add_argument("command", nargs="?", default="serve",
                        choices=["run", "serve", "agent", "eval", "claude", "download", "models"],
                        help="run = local model + chat page. serve = the tools for Claude (default). "
                             "agent = local model in the terminal. eval = evaluation suite. claude = register in Claude. "
                             "download = a model into models/. models = list them.")
    parser.add_argument("repo", nargs="?", default="",
                        help="download: a name from models/catalog.toml, a Hugging Face repo (user/name[:QUANT]) or a link.")
    parser.add_argument("--use", action="store_true", help="download: also set the model in bachmcp.toml.")
    parser.add_argument("--config", default="", help="the config file (default: bachmcp.toml in the repository).")
    parser.add_argument("--stdio", action="store_true", help="serve: over stdio, for a host that starts Bach itself.")
    parser.add_argument("--runs", type=int, default=5, help="eval: runs per case (default 5).")
    parser.add_argument("--case", default="", help="eval: only these cases, comma-separated.")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)

    try:
        config = load_config(args.config)
        if args.command == "run":
            from bach_mcp.chat import web
            web.run(config)
        elif args.command == "agent":
            from bach_mcp.chat import terminal
            terminal.run(config)
        elif args.command == "eval":
            from bach_mcp.chat.evaluate import run_suite
            run_suite(config, runs=args.runs, only=[c.strip() for c in args.case.split(",") if c.strip()])
        elif args.command == "download":
            from bach_mcp.utilities import download
            if not args.repo:
                raise ConfigError("download needs a model: a name (python py/main.py models lists them), "
                                  "a Hugging Face repo or a link")
            info = download.download(args.repo)
            print(f"Done: models/{info.name} ({info.format}, {info.gigabytes}).")
            if args.use:
                download.use_in_config(info, config.source)
                print(f"bachmcp.toml now uses it: [model] model = \"{info.name}\" ({info.format}).")
            else:
                print(f"To use it, set in bachmcp.toml: [model] model = \"{info.name}\" "
                      "(or download again with --use).")
        elif args.command == "models":
            from bach_mcp.utilities.download import in_use, list_models, load_catalog
            models = list_models()
            print(f"In models/ ({len(models)}):")
            for m in models:
                used = " (in use)" if in_use(m, config) else ""
                print(f"  {m.name:40s} {m.format or 'not a model':6s} {m.gigabytes:>9s}{used}")
            print("\nBy name (python py/main.py download <name> --use):")
            for e in load_catalog().values():
                mark = "downloaded" if e.downloaded() else f"{e.size_gb:.1f} GB"
                print(f"  {e.name:18s} {e.format:4s} {mark:>10s}  {e.note}")
        elif args.command == "claude":
            from bach_mcp import claude
            print(claude.register_desktop())
            print("Claude Code, either of:")
            print("  its own Bach:            " + claude.claude_code_commands(config)[0])
            print("  the Bach of run.command: " + claude.claude_code_commands(config)[1])
        else:
            from bach_mcp import claude
            claude.serve(config, stdio=args.stdio)
    except (ConfigError, BridgeBusy) as exc:
        sys.exit(f"Bach: {exc}")
    except RuntimeError as exc:  # the model server stopped or never became ready
        sys.exit(f"Bach: {exc}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
