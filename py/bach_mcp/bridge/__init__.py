"""The link to Max: short plain-text messages over UDP, scores through one file.

    udp.py      lines of text <-> the UDP packets [udpreceive] reads and [udpsend] writes
    max.py      the bridge object: sends messages to the patch and queues what it answers
    buffer.py   scores travel through buffer.txt in bach's text format, never as messages

Used by the tools. Imports only music/.
"""
