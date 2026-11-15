"""
analysis.py
-----------
A sound as text, for a model that cannot hear: what a buffer instance's source is (added to
its prompts by the hub) and what its result became (in send_buffer_process's answer).

    describe(x, sr, title)           the whole description: numbers, then the text spectrogram
    features(x, sr)                  the numbers alone, as a dict (compare() reads two of them)
    spectrogram(x, sr)               the text spectrogram alone
    compare(before, after)           one line per thing that changed, before -> after

Units as in the score: ms, dB, Hz, and pitches in midicents (6000 = middle C).

The text spectrogram is the sound in time: SLICES columns (equal stretches of the sound) by
BANDS rows (from the air down to the sub), each cell one digit, 0-9, 6 dB a step: 9 is the
loudest cell, 0 is 54 dB or more below it, `.` is silence. A last row, `all`, is the level of
the whole slice. Uses numpy, scipy and librosa; the models that name the sound are in listen.py.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

SLICES = 24
BANDS: List[Tuple[str, float, float]] = [  # name, low Hz, high Hz; printed from the top down
    ("16k+", 16000, 24000), ("12k", 12000, 16000), ("8k", 8000, 12000), ("6k", 6000, 8000),
    ("4k", 4000, 6000), ("2.5k", 2500, 4000), ("1.5k", 1500, 2500), ("800", 800, 1500),
    ("400", 400, 800), ("200", 200, 400), ("100", 100, 200), ("sub", 20, 100),
]
SUMMARY_BANDS = [("sub", 20, 60), ("low", 60, 250), ("low-mid", 250, 1000), ("mid", 1000, 4000),
                 ("presence", 4000, 8000), ("air", 8000, 24000)]
SILENCE_DB = -70.0
N_FFT, HOP = 2048, 512


def _db(power: np.ndarray | float, floor: float = -120.0) -> np.ndarray | float:
    return np.maximum(10.0 * np.log10(np.maximum(power, 1e-30)), floor)


def _frames(x) -> np.ndarray:
    a = np.asarray(x, dtype=np.float32)
    return a[:, None] if a.ndim == 1 else a


def _mono(x: np.ndarray) -> np.ndarray:
    """The channels' mean, with silence after it up to one analysis window: a sound shorter
    than N_FFT samples (a grain, a click) is analysed like any other."""
    mono = x.mean(axis=1).astype(np.float32)
    return np.pad(mono, (0, N_FFT - len(mono))) if len(mono) < N_FFT else mono


def _power_spectrogram(mono: np.ndarray, sr: float) -> Tuple[np.ndarray, np.ndarray]:
    """|STFT|^2 of the mono signal, (bins, frames), and the frequency of each bin."""
    from scipy.signal import stft
    _, _, z = stft(mono, fs=sr, nperseg=N_FFT, noverlap=N_FFT - HOP, boundary="zeros", padded=True)
    return (np.abs(z) ** 2).astype(np.float64), np.fft.rfftfreq(N_FFT, 1.0 / sr)


def spectrogram(x, sr: float, slices: int = SLICES) -> str:
    """The text spectrogram (see the module's docstring)."""
    x = _frames(x)
    if len(x) == 0:
        return "spectrogram: no sound"
    mono = _mono(x)
    power, freqs = _power_spectrogram(mono, sr)
    edges = np.linspace(0, power.shape[1], slices + 1).astype(int)
    edges[-1] = power.shape[1]
    cells = np.full((len(BANDS), slices), -120.0)
    total = np.full(slices, -120.0)
    for s in range(slices):
        a, b = edges[s], max(edges[s + 1], edges[s] + 1)
        block = power[:, a:b].mean(axis=1)
        total[s] = _db(block.sum())
        for r, (_, low, high) in enumerate(BANDS):
            band = block[(freqs >= low) & (freqs < min(high, sr / 2))]
            cells[r, s] = _db(band.sum()) if band.size else -120.0
    top = cells.max()

    def digit(value: float, loudest: float) -> str:
        if value <= -110 or value < loudest - 80:
            return "."
        return str(int(np.clip(9 + np.floor((value - loudest) / 6.0 + 1e-9), 0, 9)))

    ms_per = len(x) * 1000.0 / sr / slices
    lines = [f"spectrogram: {slices} slices of {ms_per:.0f} ms (left to right), one digit per cell, 6 dB a step; "
             f"9 = the loudest cell, 0 = 54 dB or more below it, . = silence"]
    for r, (name, _, _) in enumerate(BANDS):
        if BANDS[r][1] >= sr / 2:
            continue
        lines.append(f"{name:>5} " + " ".join(digit(v, top) for v in cells[r]))
    lines.append(f"{'all':>5} " + " ".join(digit(v, total.max()) for v in total))
    marks = [f"{int(round(s * ms_per)):d}" for s in range(0, slices, 6)]
    lines.append(f"{'ms':>5} " + "".join(m.ljust(12) for m in marks))
    return "\n".join(lines)


def features(x, sr: float) -> Dict[str, Any]:
    """The numbers the description is made of. Empty sound: {"frames": 0}."""
    x = _frames(x)
    out: Dict[str, Any] = {"frames": int(len(x)), "channels": int(x.shape[1]), "sr": float(sr),
                           "ms": len(x) * 1000.0 / sr if sr else 0.0}
    if len(x) == 0 or not np.any(x):
        out["silent"] = True
        return out
    import librosa

    mono = _mono(x)
    peak = float(np.max(np.abs(x)))
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    out.update(peak_db=float(_db(peak ** 2)), rms_db=float(_db(rms ** 2)), crest_db=float(_db(peak ** 2) - _db(rms ** 2)))

    frame_rms = librosa.feature.rms(y=mono, frame_length=N_FFT, hop_length=HOP)[0]
    frame_db = _db(frame_rms ** 2)
    loud = np.nonzero(frame_db > max(SILENCE_DB, frame_db.max() - 60))[0]
    to_ms = HOP * 1000.0 / sr
    out["sound_from_ms"] = float(loud[0] * to_ms) if loud.size else 0.0
    out["sound_to_ms"] = float(min((loud[-1] + 1) * to_ms, out["ms"])) if loud.size else 0.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        onsets = librosa.onset.onset_detect(y=mono, sr=sr, hop_length=HOP, units="time", backtrack=True)
    out["onsets_ms"] = [float(t * 1000.0) for t in onsets]

    power, freqs = _power_spectrogram(mono, sr)
    spectrum = power.mean(axis=1)
    weights = power.sum(axis=0)
    active = weights > weights.max() * 1e-6
    centroid = (freqs[:, None] * power).sum(axis=0) / np.maximum(weights, 1e-30)
    out["centroid_hz"] = float(np.average(centroid[active], weights=weights[active]))
    out["centroid_range_hz"] = [float(np.percentile(centroid[active], 10)), float(np.percentile(centroid[active], 90))]
    cumulative = np.cumsum(spectrum) / max(spectrum.sum(), 1e-30)
    out["rolloff_hz"] = float(freqs[min(np.searchsorted(cumulative, 0.85), len(freqs) - 1)])
    flat = librosa.feature.spectral_flatness(S=np.sqrt(power[:, active]) if active.any() else np.sqrt(power))[0]
    out["flatness"] = float(np.mean(flat))
    total = max(spectrum.sum(), 1e-30)
    out["bands_db"] = {name: float(_db(spectrum[(freqs >= low) & (freqs < high)].sum() / total))
                       for name, low, high in SUMMARY_BANDS if low < sr / 2}

    harmonic, percussive = librosa.decompose.hpss(librosa.stft(mono, n_fft=N_FFT, hop_length=HOP))
    h, p = float(np.sum(np.abs(harmonic) ** 2)), float(np.sum(np.abs(percussive) ** 2))
    out["harmonic_share"] = h / max(h + p, 1e-30)
    out["partials"] = _partials(np.mean(np.abs(harmonic) ** 2, axis=1), freqs, sr)
    out["tail_ms"] = _tail(frame_db, to_ms)

    if x.shape[1] >= 2:
        left, right = x[:, 0].astype(np.float64), x[:, 1].astype(np.float64)
        denominator = np.sqrt(np.sum(left ** 2) * np.sum(right ** 2))
        out["correlation"] = float(np.sum(left * right) / denominator) if denominator > 0 else 1.0
        mid, side = (left + right) / 2, (left - right) / 2
        out["side_db"] = float(_db(np.mean(side ** 2)) - _db(np.mean(mid ** 2)))
        out["balance_db"] = float(_db(np.mean(right ** 2)) - _db(np.mean(left ** 2)))
    return out


def _partials(spectrum: np.ndarray, freqs: np.ndarray, sr: float, count: int = 8) -> List[Tuple[int, float]]:
    """The strongest peaks of the harmonic part: (midicents, dB below the strongest), low to high."""
    from scipy.signal import find_peaks
    usable = (freqs >= 30) & (freqs <= min(8000, sr / 2))
    db = _db(spectrum)
    top = db[usable].max() if usable.any() else -120
    peaks, _ = find_peaks(np.where(usable, db, -200), prominence=10, height=top - 40)
    peaks = sorted(peaks, key=lambda k: -db[k])[:count]
    out = []
    for k in sorted(peaks):
        if 0 < k < len(db) - 1:  # parabolic interpolation of the peak's frequency
            a, b, c = db[k - 1], db[k], db[k + 1]
            shift = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) != 0 else 0.0
        else:
            shift = 0.0
        hz = (k + shift) * sr / N_FFT
        if hz > 0:
            out.append((int(round(6900 + 1200 * np.log2(hz / 440.0))), float(db[k] - top)))
    return out


def _tail(frame_db: np.ndarray, to_ms: float) -> Optional[float]:
    """How long the end takes to fall 30 dB from the last strong peak, in ms (None: it does not)."""
    if frame_db.size < 4:
        return None
    strong = np.nonzero(frame_db > frame_db.max() - 12)[0]
    last = strong[-1]
    level = frame_db[last]
    below = np.nonzero(frame_db[last:] < level - 30)[0]
    return float(below[0] * to_ms) if below.size else None


def _quality(f: Dict[str, Any]) -> List[str]:
    """A few plain words on what the numbers mean, so they are read the same way every time."""
    words = []
    words.append("bright" if f["centroid_hz"] > 3000 else "dark" if f["centroid_hz"] < 800 else "mid-bright")
    words.append("noisy" if f["flatness"] > 0.3 else "tonal" if f["flatness"] < 0.05 else "mixed tonal/noisy")
    words.append("very dynamic" if f["crest_db"] > 18 else "compressed" if f["crest_db"] < 9 else "dynamic")
    return words


def describe(x, sr: float, title: str, extra: Optional[List[str]] = None,
             f: Optional[Dict[str, Any]] = None) -> str:
    """The description of a sound: a title line, the numbers, the lines in `extra` (what it is,
    from listen.py), then the text spectrogram. f: its features(x, sr), when already computed."""
    f = features(x, sr) if f is None else f
    head = f"{title}: {f['ms']:.0f} ms, {f['channels']} ch, {f['sr']:g} Hz"
    if f.get("silent"):
        return head + "\nsilent (no sound in it)"
    lines = [head, f"level      peak {f['peak_db']:.1f} dBFS, rms {f['rms_db']:.1f} dB, crest {f['crest_db']:.0f} dB "
             f"({', '.join(_quality(f))})"]
    if f["sound_from_ms"] > 50 or f["ms"] - f["sound_to_ms"] > 50:
        lines.append(f"sound      from {f['sound_from_ms']:.0f} to {f['sound_to_ms']:.0f} ms (silence around it)")
    onsets = f["onsets_ms"]
    if onsets:
        shown = " ".join(f"{t:.0f}" for t in onsets[:16]) + (" ..." if len(onsets) > 16 else "")
        lines.append(f"events     {len(onsets)} onsets, at ms: {shown}")
    else:
        lines.append("events     no clear onsets (continuous)")
    low, high = f["centroid_range_hz"]
    lines.append(f"spectrum   centroid {f['centroid_hz']:.0f} Hz (from {low:.0f} to {high:.0f}), rolloff {f['rolloff_hz']:.0f} Hz, "
                 f"flatness {f['flatness']:.2f}")
    lines.append("bands dB   " + " | ".join(f"{k} {v:.0f}" for k, v in f["bands_db"].items()))
    lines.append(f"material   harmonic {100 * f['harmonic_share']:.0f} % / percussive {100 * (1 - f['harmonic_share']):.0f} %")
    if f["partials"]:
        lines.append("partials   (midicents, dB) " + "  ".join(f"{mc} {db:.0f}" for mc, db in f["partials"]))
    tail = f["tail_ms"]
    lines.append(f"tail       falls 30 dB in {tail:.0f} ms after the last strong peak" if tail is not None
                 else "tail       does not fall 30 dB before the end (it is cut, or rings on)")
    if "correlation" in f:
        width = "mono-like" if f["correlation"] > 0.95 else "narrow" if f["correlation"] > 0.7 else "wide" if f["correlation"] > 0.2 else "very wide / out of phase"
        lines.append(f"stereo     correlation {f['correlation']:.2f} ({width}), side {f['side_db']:.0f} dB below mid, "
                     f"right-left {f['balance_db']:+.1f} dB")
    lines += extra or []
    lines.append(spectrogram(x, sr))
    return "\n".join(lines)


def compare(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    """What changed, before -> after, one line each (only what both have)."""
    if before.get("silent") or after.get("silent") or not before.get("frames") or not after.get("frames"):
        return [f"duration    {before.get('ms', 0):.0f} -> {after.get('ms', 0):.0f} ms"]
    rows = [("duration", "ms", "{:.0f} ms"), ("level rms", "rms_db", "{:.1f} dB"), ("peak", "peak_db", "{:.1f} dBFS"),
            ("crest", "crest_db", "{:.0f} dB"), ("centroid", "centroid_hz", "{:.0f} Hz"), ("rolloff", "rolloff_hz", "{:.0f} Hz"),
            ("flatness", "flatness", "{:.2f}"), ("harmonic", "harmonic_share", "{:.0%}"), ("correlation", "correlation", "{:.2f}")]
    out = []
    for label, key, fmt in rows:
        if key in before and key in after:
            out.append(f"{label:<12}{fmt.format(before[key])} -> {fmt.format(after[key])}")
    out.append(f"onsets      {len(before['onsets_ms'])} -> {len(after['onsets_ms'])}")
    tails = [f"{t:.0f} ms" if t is not None else "rings on" for t in (before["tail_ms"], after["tail_ms"])]
    out.append(f"tail        {tails[0]} -> {tails[1]}")
    return out


__all__ = ["describe", "features", "spectrogram", "compare", "SLICES", "BANDS"]
