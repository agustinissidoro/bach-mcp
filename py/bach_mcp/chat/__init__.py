"""The door for the local model. One conversation engine, one hub, three ways to use it.

    engine.py     one conversation: mode, skill part, docs, the tool loop -> events
    hub.py        every line from Max, the page and the terminal; one conversation per instance
    web.py        `run`: the chat page, the hub's lines in and out, /mcp for Claude Code
    page.html     the chat page, for a browser or Max's [jweb]
    terminal.py   `agent`: the hub in the terminal
    evaluate.py   `eval`: fixed requests through the same engine, with checks

Imports model/, prompt/, tools/ and claude.py (to offer /mcp beside the page).
"""
