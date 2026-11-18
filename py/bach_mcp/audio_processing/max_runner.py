"""max_runner.py — the Python runner driven straight from Max, with no server.

The same runner as the hub's (runner.ProcessRunner: one worker process per instance,
slider drags coalesced into one run, the same files and the same answers), so a buffer
instance's code iterates the same way whether the MCP server is running or not.

    [bachmcp.python @python <the package's .venv/bin/python> @folder <the package>]
    run py/bach_mcp/audio_processing/max_runner.py

Then, with call (the hub's verbs, the instance name first):

    call set_playground <folder>                     where processes/<name>.py and .json are
    call buffer_process_source <name> <shmbuffer>    the bachmcp.shmbuffer~ it reads (default <name>-in)
    call buffer_process_target <name> <shmbuffer>    the one it writes (default <name>-out)
    call buffer_process_run <name>                   run processes/<name>.py on its source
    call buffer_process_param <name> <param> <value> ...   a panel change: kept, then a run
    call buffer_settings <name> <setting> <words> ...      soundfile_sources, fx, fx_exclude, variations ...
    call buffer_process_stop <name>                  end the run in progress
    call remove <name>                               stop it and end its worker

What comes out of the left outlet is what the hub sends Max, word for word:

    <name> processing
    <name> processed <ms> <frames> <channels> <sr>
    <name> processed_variations <count>
    <name> process_note <text>
    <name> process_error <text>
    <name> process_stopped
    <name> error <text>                              a setting refused
    set_playground <folder>                          the playground taken

eof (or closing the patch) ends every worker and the script. The workers run with the
same Python as this script. bachmcp_max sits in this folder, so it is imported from here.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))  # the bach_mcp package

from bachmcp_max import loop, on, out  # noqa: E402

from bach_mcp.audio_processing.runner import ProcessRunner  # noqa: E402

playground = ""


def _words(values) -> list:
    """Arguments as the hub gets them from Max: words (the runner reads numbers back)."""
    return [str(v) for v in values]


runner = ProcessRunner(lambda *said: out(*said), lambda: playground)


@on
def set_playground(path):
    """The folder of the instances' files: processes/<name>.py and processes/<name>.json."""
    global playground
    folder = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isdir(folder):
        raise ValueError(f"no folder {folder}")
    playground = folder
    out("set_playground", folder)


@on
def buffer_process_source(name, shm):
    runner.set_source(str(name), str(shm))


@on
def buffer_process_target(name, shm):
    runner.set_target(str(name), str(shm))


@on
def buffer_process_run(name):
    runner.run(str(name))


@on
def buffer_process_param(name, param, *values):
    if not values:
        raise TypeError("buffer_process_param needs a name, a parameter and a value")
    runner.set_param(str(name), str(param), _words(values))


@on
def buffer_settings(name, setting, *words):
    why = runner.set_setting(str(name), str(setting), _words(words))
    if why:
        out(str(name), "error", why)


@on
def buffer_process_stop(name):
    runner.stop(str(name))


@on
def remove(name):
    runner.forget(str(name))


if __name__ == "__main__":
    try:
        loop()
    finally:
        runner.close()   # every worker ends with the script
