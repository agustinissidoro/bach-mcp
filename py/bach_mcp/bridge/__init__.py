"""The link to Max: short plain-text messages over UDP, scores through one file.

    udp.py      lines of text <-> the UDP packets [udpreceive] reads and [udpsend] writes
    max.py      the bridge object: sends messages to the patch and queues what it answers
    protocol.py the one form of every message: a line of words
    buffer.py   scores travel through files as bachjson-complete, never as messages

Used by the tools and the hub. buffer.py reads REPO_ROOT from config.py; nothing else from above.
"""
