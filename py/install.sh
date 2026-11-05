#!/bin/sh
# Finds a Python 3.11+ and runs the Bach installer with it.
cd "$(dirname "$0")" || exit 1

for p in python3.14 python3.13 python3.12 python3.11 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         python3 python; do
    if command -v "$p" >/dev/null 2>&1 &&
       "$p" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
        echo "Using $(command -v "$p")"
        exec "$p" main.py install "$@"
    fi
done

echo "Bach needs Python 3.11 or newer. Install it from https://www.python.org/downloads/ and try again." >&2
exit 1