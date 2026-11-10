"""The hub and who answers it: the local model, or Claude Code (headless.py). One hub, three ways to use it.

    engine.py     one conversation: mode, skill part, docs, the tool loop -> events
    hub.py        every line from Max, the page and the terminal; one conversation per instance
    headless.py   one conversation with Claude Code (claude -p), with the engine's face
    web.py        `run`, and the chat page with the hub's lines in and out (also beside /mcp, for `serve`)
    page.html     the chat page, for a browser or Max's [jweb]
    terminal.py   `agent`: the hub in the terminal
    evaluate.py   `eval`: fixed requests through the same engine, with checks

Imports model/, prompt/ and tools/; headless.py takes one function from claude.py, which serves this page beside /mcp.
"""
