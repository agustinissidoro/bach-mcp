"""bachmcp.python example: a long job you can stop.

    run examples/python/slow.py 20
"""
import sys
import time

from bachmcp_max import out

seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
try:
    for i in range(seconds):
        out("tick", i + 1, seconds)
        time.sleep(1)
except KeyboardInterrupt:          # "stop" arrives here first
    out("stopped", i + 1)
    sys.exit(1)
