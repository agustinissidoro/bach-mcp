"""bachmcp.python example: a script that stays running and answers calls.

    run examples/python/functions.py
    call transpose 6000 200        → transpose 6200
    call chord 6000 4 3            → chord 6000 6400 6700
    call describe "big world" 3    → describe dictionary <name>  ({"text": ..., "words": 2, ...})
    call count                     → count 3
    eof                            → loop() returns, the script ends: done 0
"""
from bachmcp_max import on, out, loop

calls = 0


@on("transpose")
def transpose(pitch, cents):
    global calls
    calls += 1
    return pitch + cents                    # returned: "transpose 6200"


@on("chord")
def chord(root, *intervals):                # any number of arguments
    global calls
    calls += 1
    pitches = [root]
    for i in intervals:
        pitches.append(pitches[-1] + 100 * i)
    return pitches                          # a list: "chord 6000 6400 6700"


@on
def describe(text, times):                  # @on alone: the function's own name
    global calls
    calls += 1
    return {"text": text, "words": len(text.split()), "repeated": [text] * times}  # a dictionary


@on("count")
def count():
    return calls                            # state lasts as long as the script


out("ready")                                # a message at any time, not only as a reply
loop()
