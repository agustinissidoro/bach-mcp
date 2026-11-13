"""The samples of a bachmcp.shmbuffer~, from Python: the same memory Max holds, as a numpy array.

    buf = ShmBuffer("grain")            # join the memory of [bachmcp.shmbuffer~ grain]
    buf.array                           # float32, shape (frames, channels): Max's own samples
    buf.array[:] *= 0.5                 # worked in place; Max has it at once
    buf.touch()                         # say it changed: raises serial, tells the Max object

    while buf.wait():                   # until Max changes the memory (source, size, clear ...)
        buf.array[:] = process(buf.array)
        buf.touch()

    buf.write(result, sr=48000)         # any shape: the memory is replaced if the size differs
    buf = ShmBuffer.create("grain", frames=48000, channels=2, sr=48000)

In Max, `source <buffer~>` fills the memory from a buffer~, `target <buffer~>` puts it into one,
and `bang` writes it to the target or, with none, to a buffer~ the object makes and names.

The memory is a POSIX shared memory object, "/bachmcp.<name>": a 64-byte header, then float32
samples interleaved by channel (layout: sources/bachmcp.shmbuffer~/source/bachmcp.shmbuffer.h).
It cannot be resized: to change the size, one side retires it (state 0), unlinks the name and
makes a new one. `array` follows such a change by itself, so read it again rather than keeping
it across a resize done in Max. There is no lock between the two programs.

Uses numpy and the standard library only (macOS, Linux).
"""

from __future__ import annotations

import _posixshmem
import ctypes
import mmap
import os
import select
import struct

import numpy as np

PREFIX = "/bachmcp."
NOTIFY_PREFIX = "bachmcp.shmbuffer."
NOTIFY_FROM_MAX = ".max"
NAME_MAX = 31                       # macOS: the leading slash included
MAGIC = b"BMSB"
VERSION = 1
HEADER_SIZE = 64
LIVE, RETIRED = 1, 0

# magic, version, data_offset, channels, frames, sr, serial, state, creator_pid
_HEADER = struct.Struct("<4sIIIQdQII")
_CHANNELS, _FRAMES, _SR, _SERIAL, _STATE = 12, 16, 24, 32, 40


try:                                # macOS: Darwin notifications, what the Max object listens to
    _notify_post = ctypes.CDLL(None).notify_post
    _notify_post.argtypes = [ctypes.c_char_p]
    _notify_register_fd = ctypes.CDLL(None).notify_register_file_descriptor
    _notify_register_fd.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int), ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_int)]
    _notify_cancel = ctypes.CDLL(None).notify_cancel
    _notify_cancel.argtypes = [ctypes.c_int]
except (AttributeError, OSError):
    _notify_post = _notify_register_fd = _notify_cancel = None


class NoShmBuffer(Exception):
    """No live shared memory under this name."""


def shm_name(name: str) -> str:
    full = PREFIX + name
    if not name or "/" in name or len(full) > NAME_MAX:
        raise ValueError(f"shmbuffer name {name!r}: 1 to {NAME_MAX - len(PREFIX)} characters, no slash")
    return full


class ShmBuffer:
    """The memory of the bachmcp.shmbuffer~ of this name. Raises NoShmBuffer if there is none."""

    def __init__(self, name: str):
        self.name = name
        self.shm = shm_name(name)
        self._map: mmap.mmap | None = None
        self._listen: tuple[int, int] | None = None     # fd, token of the notification from Max
        self._attach()

    # ---------------------------------------------------------------- making and joining

    @classmethod
    def create(cls, name: str, frames: int, channels: int = 1, sr: float = 44100.0) -> "ShmBuffer":
        """New, silent memory under the name, replacing what was there. Max follows."""
        buf = cls.__new__(cls)
        buf.name, buf.shm, buf._map, buf._listen = name, shm_name(name), None, None
        buf._create(frames, channels, sr)
        return buf

    def _attach(self) -> None:
        self._map = None            # arrays handed out keep the old mapping alive
        try:
            fd = _posixshmem.shm_open(self.shm, os.O_RDWR, mode=0o600)
        except FileNotFoundError:
            raise NoShmBuffer(self.name) from None
        try:
            size = os.fstat(fd).st_size
            if size < HEADER_SIZE:
                raise NoShmBuffer(self.name)
            with mmap.mmap(fd, HEADER_SIZE, prot=mmap.PROT_READ) as head:
                magic, version, offset, channels, frames, _, _, state, _ = _HEADER.unpack_from(head)
            need = offset + frames * channels * 4
            if (magic != MAGIC or version != VERSION or state != LIVE or offset < HEADER_SIZE
                    or channels < 1 or need > size):
                raise NoShmBuffer(self.name)
            self._map = mmap.mmap(fd, need)
            self._offset = offset
        finally:
            os.close(fd)

    def _create(self, frames: int, channels: int, sr: float) -> None:
        frames, channels = int(frames), int(channels)
        if frames < 0 or channels < 1:
            raise ValueError("frames >= 0 and channels >= 1")
        serial = 0
        try:
            self._refresh()
            serial = self.serial
            self._put("<I", _STATE, RETIRED)
        except NoShmBuffer:
            pass
        self._map = None
        try:
            _posixshmem.shm_unlink(self.shm)
        except FileNotFoundError:
            pass
        fd = _posixshmem.shm_open(self.shm, os.O_CREAT | os.O_EXCL | os.O_RDWR, mode=0o600)
        try:
            size = HEADER_SIZE + frames * channels * 4
            os.ftruncate(fd, size)
            self._map = mmap.mmap(fd, size)
        finally:
            os.close(fd)
        self._offset = HEADER_SIZE
        _HEADER.pack_into(self._map, 0, b"\0\0\0\0", VERSION, HEADER_SIZE, channels, frames,
                          float(sr), serial + 1, LIVE, os.getpid())
        self._map[0:4] = MAGIC      # last: now it is ready

    def _refresh(self) -> None:
        """Make sure the mapping is the live memory: Max may have replaced it."""
        if self._map is None or self._get("<I", _STATE) != LIVE:
            self._attach()

    def _get(self, fmt: str, offset: int):
        return struct.unpack_from(fmt, self._map, offset)[0]

    def _put(self, fmt: str, offset: int, value) -> None:
        struct.pack_into(fmt, self._map, offset, value)

    # ---------------------------------------------------------------- the header

    @property
    def frames(self) -> int:
        self._refresh()
        return self._get("<Q", _FRAMES)

    @property
    def channels(self) -> int:
        self._refresh()
        return self._get("<I", _CHANNELS)

    @property
    def sr(self) -> float:
        self._refresh()
        return self._get("<d", _SR)

    @sr.setter
    def sr(self, value: float) -> None:
        self._refresh()
        self._put("<d", _SR, float(value))
        self.touch()

    @property
    def serial(self) -> int:
        """Raised by whoever changes the memory: compare two readings to know if it changed."""
        self._refresh()
        return self._get("<Q", _SERIAL)

    def touch(self) -> None:
        """Say the samples changed: raises serial and tells the Max object, which with
        @notify 1 then writes them to its buffer~."""
        self._refresh()
        self._put("<Q", _SERIAL, self._get("<Q", _SERIAL) + 1)
        if _notify_post:
            _notify_post((NOTIFY_PREFIX + self.name).encode())

    # ---------------------------------------------------------------- the samples

    @property
    def array(self) -> np.ndarray:
        """The samples themselves, not a copy: float32, shape (frames, channels)."""
        self._refresh()
        frames, channels = self._get("<Q", _FRAMES), self._get("<I", _CHANNELS)
        return np.frombuffer(self._map, dtype="<f4", count=frames * channels,
                             offset=self._offset).reshape(frames, channels)

    def read(self) -> np.ndarray:
        """A copy of the samples."""
        return self.array.copy()

    def write(self, samples, sr: float | None = None) -> None:
        """Put samples in: shape (frames,) or (frames, channels). Another size replaces the memory."""
        data = np.asarray(samples, dtype=np.float32)
        if data.ndim == 1:
            data = data[:, None]
        if data.ndim != 2 or data.shape[1] < 1:
            raise ValueError("samples: shape (frames,) or (frames, channels)")
        try:
            self._refresh()
            same = (self.frames, self.channels) == data.shape
            old_sr = self.sr
        except NoShmBuffer:
            same, old_sr = False, 44100.0
        if not same:
            self._create(data.shape[0], data.shape[1], old_sr if sr is None else sr)
        elif sr is not None:
            self._put("<d", _SR, float(sr))
        self.array[:] = data
        self.touch()

    # ---------------------------------------------------------------- waiting for Max

    def listen(self) -> None:
        """Start hearing Max's changes. wait() does it by itself; call it earlier so that
        nothing Max does between now and the first wait() is missed."""
        if self._listen is None:
            if _notify_register_fd is None:
                raise OSError("waiting for Max needs macOS notifications")
            fd, token = ctypes.c_int(), ctypes.c_int()
            key = (NOTIFY_PREFIX + self.name + NOTIFY_FROM_MAX).encode()
            if _notify_register_fd(key, ctypes.byref(fd), 0, ctypes.byref(token)) != 0:
                raise OSError("can't listen for Max's changes")
            self._listen = (fd.value, token.value)

    def wait(self, timeout: float | None = None) -> bool:
        """Sleep until the Max object changes the memory (source, size, sizeinsamps, sr,
        clear). True: it did, since the last wait() or listen(). False: timeout (seconds)."""
        self.listen()
        fd = self._listen[0]
        if not select.select([fd], [], [], timeout)[0]:
            return False
        while select.select([fd], [], [], 0)[0]:    # several changes: one answer
            os.read(fd, 4)
        return True

    # ---------------------------------------------------------------- leaving

    def close(self) -> None:
        """Let go of the memory; it stays for Max. Arrays handed out stay valid."""
        self._map = None
        if self._listen is not None:
            _notify_cancel(self._listen[1])
            self._listen = None

    def unlink(self) -> None:
        """Remove memory this side made, when no Max object owns it."""
        try:
            self._refresh()
            self._put("<I", _STATE, RETIRED)
        except NoShmBuffer:
            pass
        self._map = None
        try:
            _posixshmem.shm_unlink(self.shm)
        except FileNotFoundError:
            pass
