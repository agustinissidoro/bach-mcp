"""The 13 tools the model calls, the same for Claude and for the local model.

    registry.py      builds the one MCP app that holds every tool, and logs each call
    score_tools.py   write_score, read_score, clear_score
    pitch_tools.py   the 9 pitch tools (p2mc, get_chord, transpose, ...)
    algo_tools.py    send_algorithm, checked first by algo_check.js in Node
    session.py       which conversation the tools are serving

Imports bridge/ and music/; never the doors above it.
"""
