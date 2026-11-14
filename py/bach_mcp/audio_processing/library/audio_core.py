"""audio_core: small helpers for the code of a buffer instance (`import audio_core as ac`).

Samples are always float32 arrays of shape (frames, channels), as process(x, sr, p) gets them
and returns them. Times are in ms, like the score; frequencies in Hz; levels in dB.

    ac.ms(sr, 250)                frames in 250 ms
    ac.mono(x)                    (frames, 1): the mean of the channels
    ac.channels(x, 2)             (frames, 2): mono copied, or extra channels dropped
    ac.db(-6) / ac.to_db(0.5)     dB -> gain, gain -> dB
    ac.normalize(x, -1)           peak at -1 dBFS (silence stays silence)
    ac.fade(x, sr, 10, 50)        10 ms fade-in, 50 ms fade-out
    ac.pad(x, sr, 2000)           2 s of silence added at the end (tails of reverbs and delays)
    ac.mix(a, b, 0.3)             a with 30 % of b, the shorter padded with silence
    S, f, t = ac.stft(x, sr)      complex spectra, shape (channels, bins, frames); bin Hz; frame ms
    y = ac.istft(S, sr, len(x))   back to samples, cut or padded to len(x) frames
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

N_FFT = 2048
HOP = 512


def ms(sr: float, millis: float) -> int:
    """Frames in `millis` ms at sr."""
    return int(round(float(millis) * float(sr) / 1000.0))


def as_frames(x) -> np.ndarray:
    """Any samples as float32 (frames, channels): a 1-D array becomes one channel."""
    a = np.asarray(x, dtype=np.float32)
    return a[:, None] if a.ndim == 1 else a


def mono(x) -> np.ndarray:
    x = as_frames(x)
    return x.mean(axis=1, keepdims=True)


def channels(x, n: int) -> np.ndarray:
    """x with n channels: one channel is copied, more than n are dropped, fewer are cycled."""
    x = as_frames(x)
    if x.shape[1] == n:
        return x
    return x[:, [k % x.shape[1] for k in range(n)]]


def db(decibels: float) -> float:
    return float(10.0 ** (float(decibels) / 20.0))


def to_db(gain: float, floor: float = -120.0) -> float:
    g = abs(float(gain))
    return floor if g <= 0 else max(floor, 20.0 * float(np.log10(g)))


def normalize(x, peak_db: float = -1.0) -> np.ndarray:
    x = as_frames(x)
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    return x if peak == 0 else (x * (db(peak_db) / peak)).astype(np.float32)


def fade(x, sr: float, in_ms: float = 0.0, out_ms: float = 0.0) -> np.ndarray:
    x = as_frames(x).copy()
    n = len(x)
    a, b = min(ms(sr, in_ms), n), min(ms(sr, out_ms), n)
    if a:
        x[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)[:, None]
    if b:
        x[n - b:] *= np.linspace(1.0, 0.0, b, dtype=np.float32)[:, None]
    return x


def pad(x, sr: float, after_ms: float = 0.0, before_ms: float = 0.0) -> np.ndarray:
    x = as_frames(x)
    return np.pad(x, ((ms(sr, before_ms), ms(sr, after_ms)), (0, 0))).astype(np.float32)


def mix(a, b, gain_b: float = 1.0, gain_a: float = 1.0) -> np.ndarray:
    a, b = as_frames(a), as_frames(b)
    n, c = max(len(a), len(b)), max(a.shape[1], b.shape[1])
    out = np.zeros((n, c), dtype=np.float32)
    out[:len(a)] += channels(a, c) * gain_a
    out[:len(b)] += channels(b, c) * gain_b
    return out


def stft(x, sr: float, n_fft: int = N_FFT, hop: int = HOP) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Complex spectra of every channel, shape (channels, n_fft // 2 + 1, frames), with a Hann
    window; the frequency of each bin (Hz) and the time of each frame (ms)."""
    x = as_frames(x)
    window = np.hanning(n_fft).astype(np.float32)
    padded = np.pad(x, ((n_fft // 2, n_fft // 2 + hop), (0, 0)))
    count = max(1, 1 + (len(padded) - n_fft) // hop)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(count)[:, None]
    frames = padded[idx] * window[None, :, None]               # (count, n_fft, channels)
    spectra = np.fft.rfft(frames, axis=1).transpose(2, 1, 0)   # (channels, bins, count)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    times = np.arange(count) * hop * 1000.0 / sr
    return spectra, freqs, times


def istft(spectra: np.ndarray, sr: float, length: Optional[int] = None, n_fft: int = N_FFT,
          hop: int = HOP) -> np.ndarray:
    """Samples from the spectra of stft (overlap-add, window-normalised), (frames, channels)."""
    spectra = np.asarray(spectra)
    if spectra.ndim == 2:
        spectra = spectra[None]
    chans, _, count = spectra.shape
    window = np.hanning(n_fft).astype(np.float32)
    frames = np.fft.irfft(spectra.transpose(2, 1, 0), n=n_fft, axis=1) * window[None, :, None]
    total = n_fft + hop * (count - 1)
    out = np.zeros((total, chans), dtype=np.float64)
    norm = np.zeros(total, dtype=np.float64)
    for k in range(count):
        out[k * hop:k * hop + n_fft] += frames[k]
        norm[k * hop:k * hop + n_fft] += window ** 2
    out /= np.maximum(norm, 1e-8)[:, None]
    out = out[n_fft // 2:]
    if length is not None:
        out = out[:length] if len(out) >= length else np.pad(out, ((0, length - len(out)), (0, 0)))
    return out.astype(np.float32)


__all__ = ["ms", "as_frames", "mono", "channels", "db", "to_db", "normalize", "fade", "pad", "mix",
           "stft", "istft", "N_FFT", "HOP"]
