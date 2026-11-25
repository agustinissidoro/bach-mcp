"""bachmcp_max: talk to [bachmcp.python] from a running script.

It lives here, in the Python runner's folder, so the runner's scripts can be
driven from Max by [bachmcp.python] with no server running, as well as by the
hub. A script imports it when it sits in the same folder (Python looks in the
script's own folder first); examples/python links to this file for that.

    from bachmcp_max import on, out, loop

    @on("transpose")
    def transpose(pitch, cents):
        return pitch + cents

    loop()

and in Max:

    run my_script.py
    call transpose 6000 200     → transpose 6200 out of the left outlet

Messages travel on a channel of their own (JSON lines on fds 3 and 4, named by
BACHMCP_PYTHON_CHANNEL), so print() and whatever libraries print stay in the
log and can never be taken for a message.

Types, both ways:
    Max int, float, symbol      ↔ int, float, str (a symbol "3" stays the str "3")
    Max "dictionary <name>"     ↔ dict
    bool → 0/1, None → null, numpy scalars and arrays → numbers / lists

A called function's return value goes out with the function's name in front:
None sends nothing, a tuple or list sends several atoms, a dict a dictionary.
out(...) sends a message at any time (progress, streams), from any thread.
An unknown function, wrong arguments or an exception: the traceback goes to
stderr (the log), "failed <function> <message>" to the right outlet, and the
loop goes on with the script's state intact.

Run outside Max (no BACHMCP_PYTHON_CHANNEL), the channel is stdin/stdout, so a
script can be tried from a terminal by typing {"call": "transpose", "args": [6000, 200]}.

Only the standard library is used, so it works with any Python 3.
"""

import json
import os
import sys
import threading
import traceback

__all__ = ["on", "out", "loop", "call", "handlers"]

handlers = {}

_lock = threading.Lock()
_channel = None   # (reader, writer), opened on first use


def _open():
    global _channel
    if _channel is None:
        spec = os.environ.get("BACHMCP_PYTHON_CHANNEL")
        if spec:
            fd_in, fd_out = (int(n) for n in spec.split(","))
            _channel = (open(fd_in, "r", encoding="utf-8", closefd=False),
                        open(fd_out, "w", encoding="utf-8", closefd=False))
        else:
            _channel = (sys.stdin, sys.stdout)
    return _channel


def on(name=None):
    """Register a function for `call <name> ...` (default: the function's name)."""
    if callable(name):           # @on without parentheses
        fn = name
        handlers[fn.__name__] = fn
        return fn

    def register(fn):
        handlers[name or fn.__name__] = fn
        return fn
    return register


def _plain(value):
    """JSON fallback: numpy scalars and arrays, sets, paths."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (set, frozenset)):
        return list(value)
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    raise TypeError(f"can't send a {type(value).__name__} to Max")


def _send(message):
    text = json.dumps(message, ensure_ascii=False, allow_nan=False, default=_plain)
    _, writer = _open()
    with _lock:
        writer.write(text + "\n")
        writer.flush()


def _atoms(values):
    """Flatten one level (lists, tuples, numpy arrays); anything deeper is an error."""
    atoms = []
    for v in values:
        if hasattr(v, "tolist") and not isinstance(v, (int, float)):
            v = v.tolist()
        if isinstance(v, (list, tuple)):
            for item in v:
                if isinstance(item, (list, tuple)):
                    raise TypeError("a list inside a list can't be a Max message: send a dict")
                atoms.append(item)
        else:
            atoms.append(v)
    return atoms


def out(*values):
    """One message out of the left outlet. Lists and tuples are spread into
    atoms, a dict becomes a Max dictionary, strings stay one symbol."""
    atoms = _atoms(values)
    if atoms:
        _send({"out": atoms})


def _fail(name, exc):
    print(traceback.format_exc().rstrip(), file=sys.stderr, flush=True)
    try:
        _send({"error": name, "message": f"{type(exc).__name__}: {exc}"})
    except Exception as e:  # noqa: BLE001 — a failure that cannot be said must not end the loop
        print(f"bachmcp_max: could not report the failure of {name}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)


def call(name, args=()):
    """Run a function as `call` from Max would; returns its result."""
    fn = handlers.get(name)
    if fn is None:
        known = ", ".join(sorted(handlers)) or "none"
        _send({"error": name, "message": f"no function {name!r} (known: {known})"})
        return None
    try:
        result = fn(*args)
        if result is not None:
            out(name, result)
        return result
    except Exception as e:  # noqa: BLE001 — any error of the function: said, and the script goes on
        _fail(name, e)
        return None


def loop():
    """Answer calls from Max until eof, stop or the end of the patch. Says in the log why it ended."""
    reader, _ = _open()
    why = "the channel closed (eof, or the object was deleted)"
    try:
        for line in reader:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                name, args = message["call"], message.get("args", [])
            except (ValueError, KeyError, TypeError) as e:
                print(f"bachmcp_max: not a call: {line[:200]} ({e})", file=sys.stderr, flush=True)
                continue
            try:
                call(name, args)
            except Exception as e:  # noqa: BLE001 — never ends the loop
                print(f"bachmcp_max: {name}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
    except KeyboardInterrupt:    # "stop" (SIGINT): end quietly
        why = "stopped (SIGINT: the object got stop)"
    except BaseException as e:
        why = f"{type(e).__name__}: {e}"
        raise
    finally:
        print(f"bachmcp_max: the loop ended: {why}", file=sys.stderr, flush=True)
