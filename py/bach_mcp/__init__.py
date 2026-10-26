"""Bach: compose in bach.roll (Max) with a model, Claude or a local one.

The package, by level. A module imports only from its own level or below,
never from above; music/ is the base anyone may use.

    ①  config.py      bachmcp.toml -> one Config, read once by main.py and passed down

    ②  claude.py      the door for Claude: the tools over MCP, with the skill, prompts, docs
        chat/          the door for the local model: one conversation engine, its page,
                       the terminal, eval
        model/         runs the local model (mlx or gguf) and talks to it
        prompt/        what any model reads: the skill, the modes, the instrument docs

    ③  tools/         the 13 tools, defined once, used by both doors

    ④  bridge/        the link to Max: UDP messages, scores through the buffer file

        music/         pure music logic: the JSON score <-> llll, pitch arithmetic
        utilities/     helpers around Bach, not its work: what Bach tells Max about
                       itself (status.py), getting models into models/ (download.py)

filemap.md, at the root of the repository, maps every file.
"""
