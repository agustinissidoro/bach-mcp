"""max_runner.py — the Python runner driven straight from Max, with no server.

The same runner as the hub's (runner.ProcessRunner: one worker process per instance,
slider drags coalesced into one run, the same files and the same answers), so a buffer
instance's code iterates the same way whether the MCP server is running or not.

    [bachmcp.python @python <the package's .venv/bin/python> @folder <the package>]
    run py/bach_mcp/audio_processing/max_runner.py

First tell it which instance it serves and where its files are:

    call set_name <instance>                         the instance this runner serves
    call playground <folder>                         where recipes/<instance>.py and .json are
                                                     (set_playground <folder>: the same)

Once both are known (after either one, in any order) it looks for the instance's files, says
what it found, and loads the code it found as try_load does (below):

    <instance> load_buffer_process <instance>.json   recipes/<instance>.py and its panel are there
    <instance> no_buffer_panel <instance>.json       the .py is there, its panel is not
    <instance> no_buffer_process <instance>.py       no process yet: prompt the instance for one
    load <instance>.py                               then, when the .py was there and it loaded

Then, with call (the hub's verbs). After set_name they take no instance name, the runner
serves that one (a first word equal to the name is dropped); without set_name, the instance
name comes first, as the hub takes them:

    call buffer_process_source [<name>] <shmbuffer>    the bachmcp.shmbuffer~ it reads (default <name>-in)
    call buffer_process_target [<name>] <pshmbuffer>   the bachmcp.pshmbuffer~ it writes (default <name>,
                                                       the instance's own name): one run is <name>.1,
                                                       variations .1 .. .N; 17 characters at most
    call buffer_process_run [<name>]                   run recipes/<name>.py on its source
    call buffer_process_param [<name>] <param> <value> ...   a panel change: kept, then a run
    call buffer_settings [<name>] <setting> <words> ...      soundfile_sources, fx, fx_exclude, variations ...
    call buffer_process_stop [<name>]                  end the run in progress
    call remove [<name>]                               stop it and end its worker
    call database [<name>] <database> ...              the databases the recipe draws from and
                                                       analyses with (audio_corpus.corpus()):
                                                       a name: <playground>/databases/<name>(.db)
                                                       (sub/folder/name too); a full path
                                                       (absolute or ~/...): that file;
                                                       freesound: accepted, not wired yet (a note says so);
                                                       none: no database. No word: bachmcp.toml's.
                                                       Sound-file folders set with buffer_settings
                                                       soundfile_sources stay.
                                                       → database <path> ... (as found)
                                                       → <name> error database: <why>  (nothing changed)

Loading and running are two things. load puts the recipe into the instance's worker (a Python
process of its own, kept between runs): recipes/<name>.py is executed, its imports and what it
loads at the top, and no sound is processed; the panel values kept from an older version are
dropped, so the recipe starts at its declared values. A run says nothing about loading; if
the file was not loaded, or changed on disk since, the worker executes it first, quietly.

    call load [<name>]                               → load <name>.py         (to [route load];
                                                       <name>.py is taken as <name>)
                                                     → <name> process_error <why>  (no file, a
                                                       syntax error, a failed import: with its line)
    call try_load [<name>]                           the same, silent (as the algorithm runner's
                                                     try_load_algo): load <name>.py if it loads,
                                                     nothing otherwise (why: in the log). Before
                                                     the name or the playground is known it waits
                                                     and is tried when both are: the order things
                                                     arrive in does not matter.
A failed load or try_load changes nothing: the values kept stay.

What comes out of the left outlet besides is what the hub sends Max, word for word:

    <name> processing
    <name> processed <ms> <frames> <channels> <sr>
    <name> processed_variations <count>
    <name> process_note <text>
    <name> process_error <text>
    <name> process_stopped
    <name> error <text>                              a setting refused
    set_name <instance>                              the name taken
    playground <folder>                              the playground taken (set_playground <folder>
                                                     when it came as set_playground)

A new set_name ends the worker of the previous name. eof (or closing the patch) ends every
worker and the script. The workers run with the same Python as this script. bachmcp_max sits
in this folder, so it is imported from here.
"""

from __future__ import annotations

import os
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))  # the bach_mcp package

from bachmcp_max import loop, on, out  # noqa: E402

from bach_mcp.audio_processing.runner import ProcessRunner  # noqa: E402
from bach_mcp.audio_processing.settings import local_path  # noqa: E402

playground = ""
name = ""  # the instance this runner serves (set_name); "" until then
_waiting = None  # a try_load before the name or the playground: its name ("": the set one), tried when both are known


def _words(values) -> list:
    """Arguments as the hub gets them from Max: words (the runner reads numbers back)."""
    return [str(v) for v in values]


def _who(verb: str, args: tuple, least: int = 0):
    """(instance, the rest): the set name, or without one the first argument. With a set name,
    a first argument equal to it is dropped, so lines written name-first still work."""
    if name:
        rest = args[1:] if args and str(args[0]) == name else args
    elif args:
        return str(args[0]), args[1:]
    else:
        raise TypeError(f"{verb} needs the instance name first (or call set_name <instance> before)")
    if len(rest) < least:
        raise TypeError(f"{verb}: {least} argument{'s' if least > 1 else ''} after the name at least")
    return name, rest


def _search() -> None:
    """With a name and a playground: say whether recipes/<name>.py and its panel exist, and
    load the .py found (silently, as try_load: load <name>.py only if it loads)."""
    if not (name and playground):
        return
    folder = os.path.join(playground, "recipes")
    if not os.path.isfile(os.path.join(folder, f"{name}.py")):
        out(name, "no_buffer_process", f"{name}.py")
        return
    if not os.path.isfile(os.path.join(folder, f"{name}.json")):
        out(name, "no_buffer_panel", f"{name}.json")
    else:
        out(name, "load_buffer_process", f"{name}.json")
    _load(name, quiet=True)


runner = ProcessRunner(lambda *said: out(*said), lambda: playground)


@on
def set_name(instance):
    """The instance this runner serves: the verbs then take no name."""
    global name
    instance = str(instance).strip()
    if not instance:
        raise ValueError("set_name needs an instance name")
    if name and name != instance:
        runner.forget(name)  # the old name's worker and what was kept for it
    name = instance
    out("set_name", name)
    _search()
    _try_waiting()


def _set_playground(path, verb: str) -> None:
    """The folder of the instances' files: recipes/<name>.py and recipes/<name>.json."""
    global playground
    folder = os.path.abspath(local_path(str(path)))  # Max's "Macintosh HD:/..." too
    if not os.path.isdir(folder):
        raise ValueError(f"no folder {folder}")
    playground = folder
    out(verb, folder)
    _search()
    _try_waiting()


@on("playground")
def set_playground_folder(path):
    _set_playground(path, "playground")


@on
def set_playground(path):
    _set_playground(path, "set_playground")


def _bare(args: tuple) -> tuple:
    """load pepe.py is load pepe: the first word without its .py."""
    if args and str(args[0]).endswith(".py"):
        return (str(args[0])[:-3],) + tuple(args[1:])
    return args


def _load(who: str, quiet: bool) -> None:
    """recipes/<who>.py into its worker, on a thread of its own (a slow import never holds up a
    stop or a param): load <who>.py when it loaded; otherwise process_error, or with quiet only
    the log (try_load)."""
    global _waiting
    _waiting = None  # a load of any kind: an earlier try_load waits no more

    def work():
        answer = runner.load(who)
        if answer.get("ok"):
            out("load", f"{who}.py")
            return
        where = f"line {answer['line']}: " if answer.get("line") else ""
        if quiet:
            print(f"try_load: {who}.py skipped, {where}{answer.get('error', 'it failed')}", file=sys.stderr, flush=True)
        else:
            out(who, "process_error", where + answer.get("error", "it failed"))
    threading.Thread(target=work, name=f"bach-load-{who}", daemon=True).start()


@on
def load(*args):
    """recipes/<name>.py into its worker; a failure is said (process_error)."""
    who, _ = _who("load", _bare(args))
    _load(who, quiet=False)


@on
def try_load(*args):
    """load, silent: a recipe that cannot be loaded is ignored (said in the log). Without a name
    or a playground yet, it waits for them."""
    global _waiting
    args = _bare(args)
    if name:
        who = name
    else:
        who = str(args[0]) if args else ""
    if who and playground:
        _load(who, quiet=True)
    else:
        _waiting = who
        print(f"try_load: waits for {'the playground' if who else 'set_name'}", file=sys.stderr, flush=True)


def _try_waiting() -> None:
    """A try_load that came early, now that the name or the playground arrived."""
    if _waiting is None:
        return
    who = _waiting or name
    if who and playground:
        _load(who, quiet=True)


@on
def buffer_process_source(*args):
    who, rest = _who("buffer_process_source", args, 1)
    runner.set_source(who, str(rest[0]))


@on
def buffer_process_target(*args):
    who, rest = _who("buffer_process_target", args, 1)
    runner.set_target(who, str(rest[0]))


@on
def buffer_process_run(*args):
    who, _ = _who("buffer_process_run", args)
    runner.run(who)


@on
def buffer_process_param(*args):
    who, rest = _who("buffer_process_param", args, 2)
    runner.set_param(who, str(rest[0]), _words(rest[1:]))


@on
def buffer_settings(*args):
    who, rest = _who("buffer_settings", args, 1)
    why = runner.set_setting(who, str(rest[0]), _words(rest[1:]))
    if why:
        out(who, "error", why)


@on
def buffer_process_stop(*args):
    who, _ = _who("buffer_process_stop", args)
    runner.stop(who)


@on
def remove(*args):
    who, _ = _who("remove", args)
    runner.forget(who)


def _database_word(word: str) -> str:
    """One word of database: freesound and none as they are; a full path (absolute or ~/...),
    that file; anything else, <playground>/databases/<word>(.db). Raises ValueError when there
    is no such file."""
    low = word.lower()
    if low in ("freesound", "none", "database"):
        return low
    path = local_path(word)  # Max's "Macintosh HD:/..." too
    if not os.path.isabs(path):
        if not playground:
            raise ValueError(f"{word}: no playground yet (call playground <folder>), or give a full path")
        path = os.path.join(playground, "databases", word if word.lower().endswith(".db") else word + ".db")
    path = os.path.abspath(path)
    if not path.lower().endswith(".db"):
        raise ValueError(f"{word} is not a database (a .db file)")
    if not os.path.isfile(path):
        raise ValueError(f"no database {word} ({path})")
    return path


@on
def database(*args):
    """The databases the instance's recipe may draw from: see the module's docstring."""
    if name:
        who, words = name, [str(a) for a in (args[1:] if args and str(args[0]) == name else args)]
    elif args:
        who, words = str(args[0]), [str(a) for a in args[1:]]
    else:
        raise TypeError("database needs the instance name first (or call set_name <instance> before)")
    try:
        found = [_database_word(w) for w in words] or ["database"]   # no word: bachmcp.toml's
    except ValueError as exc:
        out(who, "error", f"database: {exc}")
        return
    if "none" in found:
        found = [w for w in found if w != "none"]
    kept = runner.settings(who).paths()                              # sound-file folders stay
    why = runner.set_setting(who, "soundfile_sources", (found + kept) or ["none"])
    if why:
        out(who, "error", f"database: {why}")
        return
    out("database", *(found or ["none"]))
    if "freesound" in found:
        out(who, "process_note", "freesound: not wired to the runner yet, only the databases are used")


if __name__ == "__main__":
    import signal

    def _terminated(signum, frame):  # stop's second step (SIGTERM): said, then the same end
        print("max_runner: terminated (SIGTERM)", file=sys.stderr, flush=True)
        raise SystemExit(128 + signal.SIGTERM)  # 143, as a shell says it
    signal.signal(signal.SIGTERM, _terminated)
    try:
        loop()
    finally:
        runner.close()   # every worker ends with the script
        print("max_runner: ended, its workers too", file=sys.stderr, flush=True)
