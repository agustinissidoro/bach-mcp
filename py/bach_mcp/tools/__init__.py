"""The 16 tools the model calls, the same for Claude and for the local model.

    registry.py      builds the one MCP app that holds every tool, and logs each call
    score_tools.py   write_score, write_markers, read_score, clear_score
    pitch_tools.py   the 9 pitch tools (p2mc, get_chord, transpose, ...)
    algo_tools.py    send_algorithm, checked first by algo_check.js in Node
    instance_tools.py  get_instances, set_active_instance: for a Claude written to directly
    session.py       which conversation and which instance the tools are serving

Imports bridge/ and music/; never the doors above it.
"""
