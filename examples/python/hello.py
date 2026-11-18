"""bachmcp.python example: arguments in, messages out.

    run examples/python/hello.py --count 4 --pitch 6000
"""
import argparse
import os

from bachmcp_max import out

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=3)
parser.add_argument("--pitch", type=int, default=6000)
args = parser.parse_args()

print("working folder:", os.getcwd())     # print() is the log: middle outlet, console
for i in range(args.count):
    out("note", i, args.pitch + 100 * i)  # a message: note 0 6000 out of the left outlet
