"""audio_compose: sounds that remember where they come from, and the canvas they are placed on.

A Sound is samples with their story: the units of the database they were taken from (sources) and
everything done to them since (history). Every function of audio_treat and audio_core is a method,
without the samples and the rate:

    s = unit.sound(48000)                       from the corpus (audio_corpus)
    s = s.tune(unit["pitch"], 6000).stretch(1.5).decay(900)
    h, p = s.split()                            a function that gives several sounds gives several Sounds
    voiced = noise.cross(s, amount=0.8)         another Sound as an argument: its sources are kept too
    s.ms, s.samples, s.sr                       its length in ms, the float32 (frames, channels), the rate

A Canvas is the composed sound: Sounds placed in time.

    canvas.place(s, at_ms=0, gain_db=-3, pan=-0.3)      returns the ms where the sound ends
    canvas.end_ms                                        where the last placed sound ends

The canvas gives the result (render) and its manifest: every placement with its sources and its
history, which is what an export reads to find the original files again.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

import audio_core as ac
import audio_treat as at

_rng: Optional[np.random.Generator] = None   # the variation's generator, given to treatments that take one


def set_rng(rng: Optional[np.random.Generator]) -> None:
    global _rng
    _rng = rng


def rng(p=None) -> np.random.Generator:
    """The random generator of this run, from the parameters `seed` and `variation` (0 and 1 when the
    panel has none): the same two numbers make the same sound again, another variation another one.
    Treatments that take chances (granulate, freeze) use it too unless given their own."""
    p = p or {}
    made = np.random.default_rng([int(p.get("seed", 0) or 0), int(p.get("variation", 1) or 0)])
    set_rng(made)
    return made


def source(x, sr: float) -> "Sound":
    """The instance's own sound (process's x) as a Sound: in a manifest it is "the source"."""
    return Sound(x, sr, [{"buffer": "source"}] if len(x) else [])


def _plain(value: Any) -> Any:
    """A value as a manifest can keep it."""
    if isinstance(value, Sound):
        return {"sound": [s.get("unit") for s in value.sources]}
    if isinstance(value, np.ndarray):
        return f"<{value.size} values>"
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (int, str, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return type(value).__name__


class Sound:
    def __init__(self, samples, sr: float, sources: Optional[List[Dict[str, Any]]] = None,
                 history: Optional[List[Dict[str, Any]]] = None) -> None:
        self.samples = np.ascontiguousarray(ac.as_frames(samples), dtype=np.float32)
        self.sr = float(sr)
        self.sources = list(sources or [])
        self.history = list(history or [])

    @property
    def ms(self) -> float:
        return len(self.samples) * 1000.0 / self.sr

    def at_rate(self, sr: float) -> np.ndarray:
        if int(sr) == int(self.sr) or not len(self.samples):
            return self.samples
        import soxr
        return soxr.resample(self.samples, self.sr, sr, quality="HQ").astype(np.float32)

    def _made(self, samples, op: str, args: Dict[str, Any], others: Sequence["Sound"]) -> "Sound":
        sources = list(self.sources)
        for o in others:
            sources += [s for s in o.sources if s not in sources]
        return Sound(samples, self.sr, sources, self.history + [{"op": op, **({"args": args} if args else {})}])

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        fn = getattr(at, name, None) if name in at.__all__ else getattr(ac, name, None) if name in ac.__all__ else None
        if not callable(fn):
            raise AttributeError(f"a Sound has no {name}: not a function of audio_treat or audio_core")
        params = list(inspect.signature(fn).parameters.values())
        free = [p for p in params[1:] if p.name != "sr" and p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
        star = next((p for p in params if p.kind == p.VAR_POSITIONAL), None)

        def call(*args, **kwargs):
            given: Dict[str, Any] = dict(zip([p.name for p in free], args))
            extra = list(args[len(free):])
            if extra and star is None:
                raise TypeError(f"{name}: {len(args)} values given, it takes {len(free)} ({', '.join(p.name for p in free)})")
            given.update(kwargs)
            others = [v for v in list(given.values()) + extra if isinstance(v, Sound)]
            sent = {k: (v.at_rate(self.sr) if isinstance(v, Sound) else v) for k, v in given.items()}
            if "sr" in [p.name for p in params]:
                sent["sr"] = self.sr
            if "rng" in [p.name for p in params] and sent.get("rng") is None and _rng is not None:
                sent["rng"] = _rng
            if star is not None:   # at.fx(x, sr, *plugins)
                result = fn(self.samples, self.sr, *extra) if "sr" in [p.name for p in params] else fn(self.samples, *extra)
            else:
                result = fn(self.samples, **sent)
            logged = {k: _plain(v) for k, v in given.items() if k != "rng"}
            if extra:
                logged["plugins"] = [repr(e)[:80] for e in extra]
            if isinstance(result, (tuple, list)):
                return [self._made(r, name, {**logged, "part": i}, others) for i, r in enumerate(result)]
            if isinstance(result, np.ndarray) and result.ndim == 2:
                return self._made(result, name, logged, others)
            return result   # a number (loudness) or a curve (envelope)

        return call

    def slice(self, start_ms: float, end_ms: Optional[float] = None) -> "Sound":
        a = max(0, ac.ms(self.sr, start_ms))
        b = len(self.samples) if end_ms is None else min(len(self.samples), ac.ms(self.sr, end_ms))
        return self._made(self.samples[a:max(a, b)].copy(), "slice", {"start_ms": start_ms, "end_ms": end_ms}, [])

    def gain(self, decibels: float) -> "Sound":
        return self._made(self.samples * ac.db(decibels), "gain", {"decibels": decibels}, [])

    def then(self, other: "Sound", crossfade_ms: float = 0.0) -> "Sound":
        """This sound, then the other one, overlapping by crossfade_ms."""
        b = other.at_rate(self.sr)
        c = max(self.samples.shape[1], b.shape[1])
        a, b = ac.channels(self.samples, c), ac.channels(b, c)
        n = int(min(ac.ms(self.sr, crossfade_ms), len(a), len(b)))
        out = np.zeros((len(a) + len(b) - n, c), dtype=np.float32)
        out[:len(a)] = ac.fade(a, self.sr, 0, crossfade_ms if n else 0)
        out[len(a) - n:] += ac.fade(b, self.sr, crossfade_ms if n else 0, 0)
        return self._made(out, "then", {"other": _plain(other), "crossfade_ms": crossfade_ms}, [other])

    def __repr__(self) -> str:
        return f"<Sound {self.ms:.0f} ms, {self.samples.shape[1]} ch, {len(self.sources)} source(s), {len(self.history)} step(s)>"


class Canvas:
    def __init__(self, sr: float = 48000, channels: int = 2) -> None:
        self.sr, self.channels = float(sr), int(channels)
        self.placed: List[Dict[str, Any]] = []
        self._sounds: List[np.ndarray] = []

    @property
    def end_ms(self) -> float:
        return max((p["at_ms"] + p["duration_ms"] for p in self.placed), default=0.0)

    def place(self, sound: Sound, at_ms: float = 0.0, gain_db: float = 0.0, pan: Optional[float] = None,
              fade_in_ms: float = 2.0, fade_out_ms: float = 10.0, label: str = "") -> float:
        """The sound on the canvas from at_ms (short fades against clicks). Returns where it ends, in ms."""
        if not isinstance(sound, Sound):
            raise TypeError("place a Sound (unit.sound(), or a Sound made from one), so that its sources are kept")
        x = sound.at_rate(self.sr)
        x = at.pan(x, pan) if pan is not None and self.channels == 2 else ac.channels(x, self.channels)
        x = ac.fade(x * ac.db(gain_db), self.sr, fade_in_ms, fade_out_ms)
        at_ms = max(0.0, float(at_ms))
        self._sounds.append(x)
        self.placed.append({"at_ms": round(at_ms, 2), "duration_ms": round(len(x) * 1000.0 / self.sr, 2),
                            "gain_db": round(float(gain_db), 2), "pan": pan, **({"label": label} if label else {}),
                            "sources": sound.sources, "history": sound.history})
        return at_ms + len(x) * 1000.0 / self.sr

    def render(self, peak_db: float = -1.0, silence_db: float = -80.0) -> np.ndarray:
        """Everything placed, mixed. A mix that would clip is brought down to peak_db (said in the manifest);
        the silence left at the end by tails (under silence_db) is cut."""
        total = ac.ms(self.sr, self.end_ms)
        out = np.zeros((total, self.channels), dtype=np.float32)
        for p, x in zip(self.placed, self._sounds):
            a = ac.ms(self.sr, p["at_ms"])
            out[a:a + len(x)] += x[:max(0, total - a)]
        peak = float(np.max(np.abs(out))) if out.size else 0.0
        self.trim_db = 0.0
        if peak > ac.db(peak_db):
            self.trim_db = round(peak_db - ac.to_db(peak), 2)
            out *= ac.db(self.trim_db)
        loud = np.nonzero(np.abs(out).max(axis=1) > ac.db(silence_db))[0] if out.size else []
        if len(loud):
            out = ac.fade(out[:min(total, loud[-1] + 1 + ac.ms(self.sr, 50))], self.sr, 0, 50)
        self.rendered_ms = round(len(out) * 1000.0 / self.sr, 2)
        return out

    def manifest(self) -> Dict[str, Any]:
        files = sorted({s["path"] for p in self.placed for s in p["sources"] if "path" in s})
        if not hasattr(self, "rendered_ms"):
            self.render()
        return {"sr": self.sr, "channels": self.channels, "duration_ms": getattr(self, "rendered_ms", round(self.end_ms, 2)),
                "trim_db": getattr(self, "trim_db", 0.0), "files": files, "placed": self.placed}


def manifest_of(result) -> Optional[Dict[str, Any]]:
    """What a result is made of, when it says so: a Canvas's manifest, a Sound's as one placement."""
    if isinstance(result, Canvas):
        return result.manifest()
    if isinstance(result, Sound):
        files = sorted({s["path"] for s in result.sources if "path" in s})
        return {"sr": result.sr, "channels": result.samples.shape[1], "duration_ms": round(result.ms, 2), "trim_db": 0.0,
                "files": files, "placed": [{"at_ms": 0.0, "duration_ms": round(result.ms, 2), "gain_db": 0.0, "pan": None,
                                            "sources": result.sources, "history": result.history}]}
    return None


__all__ = ["Sound", "Canvas", "rng", "source", "set_rng", "manifest_of"]
