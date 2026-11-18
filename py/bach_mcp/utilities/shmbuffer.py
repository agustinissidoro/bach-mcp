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

A bachmcp.pshmbuffer~ is a polybuffer of such memories, <name>.1 .. <name>.<count>, with a small
index memory under the name itself:

    poly = PShmBuffer("pepe")           # join [bachmcp.pshmbuffer~ pepe]
    len(poly)                           # how many
    poly[3].array                       # the third: a ShmBuffer, the same as ShmBuffer("pepe.3")
    poly.append(samples, sr=48000)      # one more at the end: pepe.<len+1>
    poly.pop()                          # remove the last
    poly[2].write(other); poly.touch()  # the Max object, with @notify 1, writes what changed

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


# ---------------------------------------------------------------- bachmcp.pshmbuffer~

PMAGIC = b"BMPB"
PVERSION = 1
INDEX_SIZE = 64
INDEX_DIGITS = 4                    # <name>.9999 at most
# magic, version, count, zero, serial, state, creator_pid
_INDEX = struct.Struct("<4sIIIQII")
_I_COUNT, _I_SERIAL, _I_STATE = 8, 16, 24


class _Member(ShmBuffer):
    """One memory of a PShmBuffer: touch() also tells the Max object, which listens to the index."""

    def __init__(self, name: str, poly: "PShmBuffer"):
        self._poly = poly
        super().__init__(name)

    def touch(self) -> None:
        super().touch()
        self._poly.touch()


class PShmBuffer:
    """The memories of the bachmcp.pshmbuffer~ of this name: poly[1] .. poly[len(poly)], from 1
    like polybuffer~. Raises NoShmBuffer if there is no index under the name."""

    def __init__(self, name: str):
        self._check(name)
        self.name = name
        self.shm = shm_name(name)
        self._map: mmap.mmap | None = None
        self._listen: tuple[int, int] | None = None
        self._attach()

    @staticmethod
    def _check(name: str) -> None:
        if len(PREFIX + name) + 1 + INDEX_DIGITS > NAME_MAX:
            raise ValueError(f"pshmbuffer name {name!r}: {NAME_MAX - len(PREFIX) - 1 - INDEX_DIGITS} characters at most")

    @classmethod
    def create(cls, name: str) -> "PShmBuffer":
        """A new, empty index under the name (what was there is removed). Max follows."""
        cls._check(name)
        poly = cls.__new__(cls)
        poly.name, poly.shm, poly._map, poly._listen = name, shm_name(name), None, None
        try:
            poly._attach()
            poly.clear()
            poly._put("<I", _I_STATE, RETIRED)
        except NoShmBuffer:
            pass
        poly._map = None
        try:
            _posixshmem.shm_unlink(poly.shm)
        except FileNotFoundError:
            pass
        fd = _posixshmem.shm_open(poly.shm, os.O_CREAT | os.O_EXCL | os.O_RDWR, mode=0o600)
        try:
            os.ftruncate(fd, INDEX_SIZE)
            poly._map = mmap.mmap(fd, INDEX_SIZE)
        finally:
            os.close(fd)
        _INDEX.pack_into(poly._map, 0, b"\0\0\0\0", PVERSION, 0, 0, 1, LIVE, os.getpid())
        poly._map[0:4] = PMAGIC
        return poly

    def _attach(self) -> None:
        self._map = None
        try:
            fd = _posixshmem.shm_open(self.shm, os.O_RDWR, mode=0o600)
        except FileNotFoundError:
            raise NoShmBuffer(self.name) from None
        try:
            if os.fstat(fd).st_size < INDEX_SIZE:
                raise NoShmBuffer(self.name)
            m = mmap.mmap(fd, INDEX_SIZE)
        finally:
            os.close(fd)
        magic, version, _, _, _, state, _ = _INDEX.unpack_from(m)
        if magic != PMAGIC or version != PVERSION or state != LIVE:
            m.close()
            raise NoShmBuffer(self.name)
        self._map = m

    def _refresh(self) -> None:
        if self._map is None or self._get("<I", _I_STATE) != LIVE:
            self._attach()

    def _get(self, fmt: str, offset: int):
        return struct.unpack_from(fmt, self._map, offset)[0]

    def _put(self, fmt: str, offset: int, value) -> None:
        struct.pack_into(fmt, self._map, offset, value)

    # ---------------------------------------------------------------- the set

    def __len__(self) -> int:
        self._refresh()
        return self._get("<I", _I_COUNT)

    @property
    def serial(self) -> int:
        self._refresh()
        return self._get("<Q", _I_SERIAL)

    def member(self, n: int) -> str:
        return f"{self.name}.{n}"

    def __getitem__(self, n: int) -> ShmBuffer:
        """Memory n, from 1 (negative: from the end, -1 the last)."""
        count = len(self)
        if n < 0:
            n += count + 1
        if not 1 <= n <= count:
            raise IndexError(f"{self.name} has memories 1 to {count}")
        return _Member(self.member(n), self)

    def __iter__(self):
        for n in range(1, len(self) + 1):
            yield self[n]

    def touch(self) -> None:
        """Say something changed: raises serial and tells the Max object (with @notify 1 it
        then writes the memories that changed)."""
        self._refresh()
        self._put("<Q", _I_SERIAL, self._get("<Q", _I_SERIAL) + 1)
        if _notify_post:
            _notify_post((NOTIFY_PREFIX + self.name).encode())

    def append(self, samples=None, sr: float = 44100.0, frames: int = 0, channels: int = 1) -> ShmBuffer:
        """One more memory at the end: these samples, or silence of frames x channels."""
        n = len(self) + 1
        if n > 10 ** INDEX_DIGITS - 1:
            raise ValueError(f"{10 ** INDEX_DIGITS - 1} memories at most")
        if samples is not None:
            data = np.asarray(samples, dtype=np.float32)
            data = data[:, None] if data.ndim == 1 else data
            frames, channels = data.shape
        buf = ShmBuffer.create(self.member(n), frames, channels, sr)    # made first, then counted
        if samples is not None:
            buf.array[:] = data
        self._put("<I", _I_COUNT, n)
        self.touch()
        return _Member(buf.name, self)

    def pop(self) -> None:
        """Remove the last memory."""
        n = len(self)
        if n == 0:
            raise IndexError(f"{self.name} has no memories")
        self._put("<I", _I_COUNT, n - 1)                              # uncounted first, then gone
        try:
            ShmBuffer(self.member(n)).unlink()
        except NoShmBuffer:
            pass
        self.touch()

    def clear(self) -> None:
        """Remove every memory."""
        while len(self):
            n = len(self)
            self._put("<I", _I_COUNT, n - 1)
            try:
                ShmBuffer(self.member(n)).unlink()
            except NoShmBuffer:
                pass
        self.touch()

    # ---------------------------------------------------------------- waiting for Max

    def listen(self) -> None:
        if self._listen is None:
            if _notify_register_fd is None:
                raise OSError("waiting for Max needs macOS notifications")
            fd, token = ctypes.c_int(), ctypes.c_int()
            key = (NOTIFY_PREFIX + self.name + NOTIFY_FROM_MAX).encode()
            if _notify_register_fd(key, ctypes.byref(fd), 0, ctypes.byref(token)) != 0:
                raise OSError("can't listen for Max's changes")
            self._listen = (fd.value, token.value)

    def wait(self, timeout: float | None = None) -> bool:
        """Sleep until the Max object changes the set (appendempty, append, remove, clear,
        source). True: it did. False: timeout (seconds)."""
        self.listen()
        fd = self._listen[0]
        if not select.select([fd], [], [], timeout)[0]:
            return False
        while select.select([fd], [], [], 0)[0]:
            os.read(fd, 4)
        return True

    def close(self) -> None:
        self._map = None
        if self._listen is not None:
            _notify_cancel(self._listen[1])
            self._listen = None

    def unlink(self) -> None:
        """Remove the memories and the index this side made, when no Max object owns them."""
        try:
            self._refresh()
            self.clear()
            self._put("<I", _I_STATE, RETIRED)
        except NoShmBuffer:
            pass
        self._map = None
        try:
            _posixshmem.shm_unlink(self.shm)
        except FileNotFoundError:
            pass
