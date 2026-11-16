"""audio_treat: what can be done to a sound before it is placed (`import audio_treat as at`).

A sound taken from the corpus is material, not a result: these change its length, pitch, formants,
spectrum, envelope, layers and space, alone or against another sound. Samples are float32 arrays
of shape (frames, channels), as in audio_core; times in ms, intervals in cents (100 = a semitone),
pitches in midicents (C5 = 6000), levels in dB. Every function returns new samples.

Time and pitch
    at.stretch(x, sr, 2.0)             twice as long, the pitch kept (0.5: half as long)
    at.fit(x, sr, 1500)                stretched to 1500 ms exactly
    at.pitch(x, sr, -700)              a fifth lower, the length kept; formants kept (formants=False: moved with it)
    at.tune(x, sr, 5830, 6000)         from the pitch it has (midicents, the database's `pitch`) to the one wanted
    at.formant(x, sr, 300)             the spectral envelope 300 cents up, the pitch kept (a smaller body)
    at.varispeed(x, sr, -1200)         as a tape at half speed: an octave lower and twice as long
    at.glide(x, sr, 0, -1200)          the pitch moving from 0 to -1200 cents over the sound
    at.reverse(x)

Layers (a sound taken apart)
    h, p = at.split(x, sr)             the harmonic (sustained, pitched) and percussive (attacks, noise) parts
    at.harmonic(x, sr) / at.percussive(x, sr)
    at.layers(x, sr, 4)                4 layers that sum to x, each a recurring spectral shape (NMF), lowest first
    at.band(x, sr, 200, 2000)          what is between 200 and 2000 Hz (None: no bound)
    at.attack(x, sr, 80) / at.body(x, sr, 80)    the first 80 ms, and what follows them

Spectrum (one sound through another)
    at.cross(a, b, sr)                 a's pitch and movement with b's spectral envelope: b's colour on a
    at.morph(a, b, sr, 0.5)            the spectra in between a and b (0: a, 1: b)
    at.convolve(a, b)                  a through b as a space or a resonator (b an impulse, a hit, a room)
    at.match_spectrum(x, ref, sr)      x filtered towards ref's average spectrum (amount=1)
    at.freeze(x, sr, 300, 4000)        the spectrum x has at 300 ms, held for 4 s: a resonance, a drone
    at.blur(x, sr, 200)                the spectrum smeared over 200 ms: attacks melt, the colour stays

Envelope and level
    at.envelope(x, sr, 10)             the level over time (one value per sample, linear)
    at.shape(x, env)                   an envelope imposed (any length: stretched over x)
    at.match_envelope(x, ref, sr)      x with the envelope of ref (its attack, its decay)
    at.decay(x, sr, 800)               an exponential fall: 60 dB down after 800 ms
    at.swell(x, sr, 500)               a rise from nothing over 500 ms
    at.loudness(x, sr)                 LUFS;  at.match_loudness(x, sr, -18)  (a number, or samples to match)

Grains and time
    at.granulate(x, sr, 5000, grain_ms=60, density=30, jitter=1.0, pitch_spread=50, rng=rng)
                                       5 s of grains of x: a cloud (jitter 1: from anywhere in x; 0: read in order)
    at.loop(x, sr, 6000, crossfade_ms=100)       repeated with crossfades to 6 s
    at.stutter(x, sr, 120, 6)          its first 120 ms six times

Space
    at.reverb(x, sr, size=0.8, wet=0.4)
    at.width(x, 1.5)                   stereo wider (0: mono, 1: as it is)
    at.pan(x, -0.5)                    -1 left .. 1 right (equal power)
    at.fx(x, sr, Chorus(), Distortion(drive_db=12))     any pedalboard plugins, in order
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

import numpy as np

import audio_core as ac

N_FFT, HOP = ac.N_FFT, ac.HOP
Samples = np.ndarray


def _f32(x) -> np.ndarray:
    return np.ascontiguousarray(ac.as_frames(x), dtype=np.float32)


def _length(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, ((0, n - len(x)), (0, 0)))


# ── Time and pitch ───────────────────────────────────────────────────────── #

def stretch(x, sr: float, factor: float, cents: float = 0.0, formants: bool = True) -> Samples:
    """`factor` times as long (Rubber Band, through pedalboard), the pitch moved by `cents`."""
    import pedalboard
    x = _f32(x)
    factor = float(np.clip(factor, 0.02, 100.0))
    if len(x) < 8 or (abs(factor - 1.0) < 1e-6 and abs(cents) < 1e-6):
        return x.copy()
    y = pedalboard.time_stretch(x.T, float(sr), stretch_factor=1.0 / factor, pitch_shift_in_semitones=float(cents) / 100.0,
                                preserve_formants=bool(formants))
    return _length(_f32(y.T), int(round(len(x) * factor)))


def fit(x, sr: float, millis: float) -> Samples:
    x = _f32(x)
    return stretch(x, sr, ac.ms(sr, millis) / max(1, len(x))) if len(x) else x


def pitch(x, sr: float, cents: float, formants: bool = True) -> Samples:
    return stretch(x, sr, 1.0, cents, formants)


def tune(x, sr: float, from_midicents: float, to_midicents: float, formants: bool = True) -> Samples:
    return pitch(x, sr, float(to_midicents) - float(from_midicents), formants)


def varispeed(x, sr: float, cents: float) -> Samples:
    """Pitch and length together, as a tape: +1200 is an octave up and half as long."""
    x = _f32(x)
    ratio = 2.0 ** (float(cents) / 1200.0)
    n = max(1, int(round(len(x) / ratio)))
    if len(x) < 2:
        return x.copy()
    from scipy.signal import resample_poly
    from fractions import Fraction
    f = Fraction(n, len(x)).limit_denominator(1000)
    return _length(resample_poly(x, f.numerator, f.denominator, axis=0).astype(np.float32), n)


def glide(x, sr: float, start_cents: float, end_cents: float, formants: bool = True) -> Samples:
    """The pitch moving from start_cents to end_cents over the sound, its length kept."""
    import pedalboard
    x = _f32(x)
    if len(x) < 8:
        return x.copy()
    curve = np.linspace(float(start_cents), float(end_cents), len(x)) / 100.0
    y = pedalboard.time_stretch(x.T, float(sr), pitch_shift_in_semitones=curve, preserve_formants=bool(formants))
    return _length(_f32(y.T), len(x))


def reverse(x) -> Samples:
    return _f32(x)[::-1].copy()


def _envelope_of(mag: np.ndarray, sr: float, n_fft: int) -> np.ndarray:
    """The spectral envelope of magnitudes (..., bins, frames): the cepstrum's first 2 ms."""
    log = np.log(np.maximum(mag, 1e-9))
    cep = np.fft.irfft(log, n=n_fft, axis=-2)
    keep = max(8, int(0.002 * sr))
    lifter = np.zeros(n_fft)
    lifter[:keep] = 1.0
    lifter[-keep + 1:] = 1.0
    shape = [1] * cep.ndim
    shape[-2] = n_fft
    return np.exp(np.fft.rfft(cep * lifter.reshape(shape), axis=-2).real)


def formant(x, sr: float, cents: float) -> Samples:
    """The spectral envelope moved by `cents` (up: a smaller body, down: a larger one), the pitch kept."""
    x = _f32(x)
    S, f, _ = ac.stft(x, sr)
    env = _envelope_of(np.abs(S), sr, N_FFT)
    ratio = 2.0 ** (float(cents) / 1200.0)
    bins = np.arange(len(f))
    at = bins / ratio                      # the new envelope at bin k is the old one at k / ratio
    lo = np.clip(np.floor(at).astype(int), 0, len(f) - 1)
    hi = np.clip(lo + 1, 0, len(f) - 1)
    w = (at - np.floor(at))[None, :, None]
    moved = env[:, lo] * (1 - w) + env[:, hi] * w
    return ac.istft(S * (moved / np.maximum(env, 1e-9)), sr, len(x))


# ── Layers ───────────────────────────────────────────────────────────────── #

def split(x, sr: float, margin: float = 1.0) -> Tuple[Samples, Samples]:
    """(harmonic, percussive): what holds over time and what holds over frequency (median filtering).
    margin above 1 leaves what is neither out of both."""
    import librosa
    x = _f32(x)
    S, _, _ = ac.stft(x, sr)
    mag = np.abs(S).mean(axis=0)
    mh, mp = librosa.decompose.hpss(mag, margin=margin, mask=True)
    return ac.istft(S * mh[None], sr, len(x)), ac.istft(S * mp[None], sr, len(x))


def harmonic(x, sr: float, margin: float = 1.0) -> Samples:
    return split(x, sr, margin)[0]


def percussive(x, sr: float, margin: float = 1.0) -> Samples:
    return split(x, sr, margin)[1]


def layers(x, sr: float, count: int = 4, seed: int = 0) -> list:
    """`count` layers that sum to x: each one spectral shape of the sound with its own level over time
    (non-negative matrix factorization of the spectrogram), ordered from the lowest to the brightest."""
    from sklearn.decomposition import NMF
    x = _f32(x)
    count = max(1, int(count))
    S, f, _ = ac.stft(x, sr)
    mag = np.abs(S).mean(axis=0) + 1e-9
    if count == 1 or mag.shape[1] < count:
        return [x.copy()]
    model = NMF(n_components=count, init="nndsvda", max_iter=300, random_state=seed)
    W = model.fit_transform(mag)           # (bins, count)
    H = model.components_                  # (count, frames)
    parts = W[:, :, None] * H[None, :, :]  # (bins, count, frames)
    masks = parts / np.maximum(parts.sum(axis=1, keepdims=True), 1e-12)
    order = np.argsort((W * f[:, None]).sum(axis=0) / np.maximum(W.sum(axis=0), 1e-12))
    return [ac.istft(S * masks[None, :, k, :], sr, len(x)) for k in order]


def band(x, sr: float, low: Optional[float] = None, high: Optional[float] = None, order: int = 4) -> Samples:
    from scipy import signal
    x = _f32(x)
    nyquist = sr / 2.0
    low = None if low is None or low <= 0 else min(float(low), nyquist * 0.99)
    high = None if high is None or high >= nyquist else max(float(high), 1.0)
    if low is None and high is None or len(x) < 16:
        return x.copy()
    if low is not None and high is not None:
        sos = signal.butter(order, [low, max(high, low * 1.01)], btype="band", fs=sr, output="sos")
    elif low is not None:
        sos = signal.butter(order, low, btype="high", fs=sr, output="sos")
    else:
        sos = signal.butter(order, high, btype="low", fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def attack(x, sr: float, millis: float = 80.0, fade_ms: float = 10.0) -> Samples:
    x = _f32(x)
    return ac.fade(x[:ac.ms(sr, millis)], sr, 0, fade_ms)


def body(x, sr: float, millis: float = 80.0, fade_ms: float = 10.0) -> Samples:
    x = _f32(x)
    return ac.fade(x[ac.ms(sr, millis):], sr, fade_ms, 0)


# ── Spectrum ─────────────────────────────────────────────────────────────── #

def _frames_like(S: np.ndarray, count: int) -> np.ndarray:
    """Spectra (channels, bins, frames) read over `count` frames (the nearest frame of each)."""
    if S.shape[2] == count:
        return S
    idx = np.clip(np.round(np.linspace(0, S.shape[2] - 1, count)).astype(int), 0, S.shape[2] - 1)
    return S[:, :, idx]


def cross(a, b, sr: float, amount: float = 1.0, follow: bool = True) -> Samples:
    """Cross-synthesis: a's fine structure (its pitch, its noise, its movement) under b's spectral
    envelope, so a speaks with b's colour. b is read over a's length; follow=False uses b's average
    envelope instead of its envelope at each moment. amount 0..1: how much of b's envelope."""
    a, b = _f32(a), _f32(b)
    A, _, _ = ac.stft(a, sr)
    B, _, _ = ac.stft(ac.channels(b, 1) if b.shape[1] != a.shape[1] else b, sr)
    env_a = _envelope_of(np.abs(A), sr, N_FFT)
    env_b = _envelope_of(np.abs(B), sr, N_FFT)
    env_b = _frames_like(env_b, A.shape[2]) if follow else np.repeat(env_b.mean(axis=2, keepdims=True), A.shape[2], axis=2)
    if env_b.shape[0] != env_a.shape[0]:
        env_b = np.repeat(env_b[:1], env_a.shape[0], axis=0)
    gain = (env_b / np.maximum(env_a, 1e-9)) ** float(np.clip(amount, 0.0, 1.0))
    y = ac.istft(A * gain, sr, len(a))
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    return y if peak <= 1.0 else (y / peak).astype(np.float32)


def morph(a, b, sr: float, position: float = 0.5) -> Samples:
    """The spectra between a (0) and b (1): magnitudes interpolated in dB, a's phases below the middle
    and b's above it. b is read over a's length."""
    a, b = _f32(a), _f32(b)
    A, _, _ = ac.stft(a, sr)
    B, _, _ = ac.stft(ac.channels(b, a.shape[1]), sr)
    B = _frames_like(B, A.shape[2])
    k = float(np.clip(position, 0.0, 1.0))
    mag = np.exp((1 - k) * np.log(np.abs(A) + 1e-9) + k * np.log(np.abs(B) + 1e-9))
    phase = np.angle(A if k < 0.5 else B)
    return ac.istft(mag * np.exp(1j * phase), sr, len(a))


def convolve(a, b, normalize: bool = True) -> Samples:
    """a through b (b as an impulse response: a room, a resonant hit). The result is as long as both."""
    from scipy.signal import fftconvolve
    a, b = _f32(a), _f32(b)
    c = max(a.shape[1], b.shape[1])
    a, b = ac.channels(a, c), ac.channels(b, c)
    y = np.stack([fftconvolve(a[:, k], b[:, k]) for k in range(c)], axis=1).astype(np.float32)
    if normalize and y.size:
        peak, want = float(np.max(np.abs(y))), float(np.max(np.abs(a)))
        if peak > 0:
            y = y * (want / peak)
    return y.astype(np.float32)


def match_spectrum(x, ref, sr: float, amount: float = 1.0, smooth_bins: int = 9) -> Samples:
    """x filtered so that its average spectrum goes towards ref's (a static filter, at most 24 dB)."""
    from scipy.ndimage import uniform_filter1d
    x, ref = _f32(x), _f32(ref)
    X, _, _ = ac.stft(x, sr)
    R, _, _ = ac.stft(ref, sr)
    px = uniform_filter1d((np.abs(X) ** 2).mean(axis=(0, 2)), smooth_bins)
    pr = uniform_filter1d((np.abs(R) ** 2).mean(axis=(0, 2)), smooth_bins)
    gain_db = np.clip(5.0 * np.log10(np.maximum(pr, 1e-12) / np.maximum(px, 1e-12)), -24.0, 24.0) * float(amount)
    return ac.istft(X * (10.0 ** (gain_db / 20.0))[None, :, None], sr, len(x))


def freeze(x, sr: float, at_ms: float, millis: float, spread_ms: float = 60.0, rng=None) -> Samples:
    """The spectrum x has around at_ms held for `millis`: every bin a steady partial, so a hit becomes
    its own resonance and a moment becomes a drone."""
    rng = np.random.default_rng(0) if rng is None else rng
    x = _f32(x)
    S, _, t = ac.stft(x, sr)
    near = np.abs(t - float(at_ms)) <= max(float(spread_ms), HOP * 1000.0 / sr)
    if not near.any():
        near[np.argmin(np.abs(t - float(at_ms)))] = True
    mag = np.abs(S[:, :, near]).mean(axis=2)                         # (channels, bins)
    count = max(2, ac.ms(sr, millis) // HOP + 1)
    advance = 2 * np.pi * np.arange(mag.shape[1]) * HOP / N_FFT      # each bin's own frequency
    start = rng.uniform(0, 2 * np.pi, mag.shape)
    drift = np.cumsum(rng.normal(0, 0.15, (mag.shape[0], mag.shape[1], count)), axis=2)   # alive, not a held tone
    phase = start[:, :, None] + advance[None, :, None] * np.arange(count)[None, None, :] + drift
    return ac.istft(mag[:, :, None] * np.exp(1j * phase), sr, ac.ms(sr, millis))


def blur(x, sr: float, millis: float) -> Samples:
    """The magnitudes averaged over `millis`, the phases kept: attacks soften into the colour."""
    from scipy.ndimage import uniform_filter1d
    x = _f32(x)
    S, _, _ = ac.stft(x, sr)
    width = max(1, int(round(float(millis) * sr / 1000.0 / HOP)))
    mag = uniform_filter1d(np.abs(S), width, axis=2, mode="nearest")
    return ac.istft(mag * np.exp(1j * np.angle(S)), sr, len(x))


# ── Envelope and level ───────────────────────────────────────────────────── #

def envelope(x, sr: float, millis: float = 10.0) -> np.ndarray:
    """The level of x over time: the RMS over `millis`, one value per sample (linear)."""
    from scipy.ndimage import uniform_filter1d
    x = _f32(x)
    if not len(x):
        return np.zeros(0, dtype=np.float32)
    power = (x.astype(np.float64) ** 2).mean(axis=1)
    return np.sqrt(uniform_filter1d(power, max(1, ac.ms(sr, millis)), mode="nearest")).astype(np.float32)


def shape(x, env) -> Samples:
    """x multiplied by an envelope of any length (stretched over x)."""
    x = _f32(x)
    env = np.asarray(env, dtype=np.float64).reshape(-1)
    if not len(x) or not len(env):
        return x.copy()
    if len(env) != len(x):
        env = np.interp(np.linspace(0, len(env) - 1, len(x)), np.arange(len(env)), env)
    return (x * env[:, None]).astype(np.float32)


def match_envelope(x, ref, sr: float, millis: float = 10.0, floor_db: float = -50.0) -> Samples:
    """x with ref's envelope (read over x's length): x is levelled, then ref's level is imposed."""
    x = _f32(x)
    own = envelope(x, sr, millis).astype(np.float64)
    want = envelope(ref, sr, millis).astype(np.float64)
    if not len(own) or not len(want):
        return x.copy()
    want = np.interp(np.linspace(0, len(want) - 1, len(x)), np.arange(len(want)), want)
    floor = max(float(own.max()) * ac.db(floor_db), 1e-9)
    y = x * (want / np.maximum(own, floor))[:, None]
    peak = float(np.max(np.abs(y))) if y.size else 0.0
    return (y / peak * min(1.0, float(want.max()) * 3)).astype(np.float32) if peak > 1.0 else y.astype(np.float32)


def decay(x, sr: float, millis: float, start_ms: float = 0.0) -> Samples:
    """An exponential fall from start_ms on: 60 dB down after `millis`."""
    x = _f32(x)
    t = np.maximum(0.0, np.arange(len(x)) / sr * 1000.0 - float(start_ms))
    return (x * (10.0 ** (-3.0 * t / max(float(millis), 1.0)))[:, None]).astype(np.float32)


def swell(x, sr: float, millis: float, curve: float = 2.0) -> Samples:
    """A rise from nothing over `millis` (curve above 1: slow at first)."""
    x = _f32(x)
    n = min(len(x), ac.ms(sr, millis))
    env = np.ones(len(x))
    env[:n] = np.linspace(0.0, 1.0, n) ** float(curve)
    return (x * env[:, None]).astype(np.float32)


def loudness(x, sr: float) -> float:
    """Integrated loudness in LUFS (BS.1770); the RMS level in dB for less than 400 ms."""
    x = _f32(x)
    if len(x) >= int(0.4 * sr) + 1:
        import pyloudnorm
        value = float(pyloudnorm.Meter(int(sr)).integrated_loudness(x.astype(np.float64)))
        if np.isfinite(value):
            return value
    rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) if x.size else 0.0
    return ac.to_db(rms)


def match_loudness(x, sr: float, target: Union[float, np.ndarray], limit_db: float = 30.0) -> Samples:
    """x at `target` LUFS, or as loud as the samples given (peaks kept under 0 dBFS)."""
    x = _f32(x)
    want = float(target) if np.isscalar(target) else loudness(target, sr)
    have = loudness(x, sr)
    if have <= -119.0 or not np.isfinite(want):
        return x.copy()
    y = x * ac.db(float(np.clip(want - have, -limit_db, limit_db)))
    peak = float(np.max(np.abs(y)))
    return (y / peak * 0.999).astype(np.float32) if peak > 0.999 else y.astype(np.float32)


# ── Grains and time ──────────────────────────────────────────────────────── #

def granulate(x, sr: float, millis: float, grain_ms: float = 60.0, density: float = 30.0, jitter: float = 1.0,
              pitch_spread: float = 0.0, pan_spread: float = 0.0, rng=None) -> Samples:
    """`millis` of grains of x: `density` grains a second, each `grain_ms` long under a Hann window.
    jitter 0 reads x in order over the result, 1 takes each grain from anywhere in it; pitch_spread:
    each grain off by up to so many cents; pan_spread 0..1: grains spread over two channels."""
    rng = np.random.default_rng(0) if rng is None else rng
    x = _f32(x)
    total, grain = ac.ms(sr, millis), max(16, ac.ms(sr, grain_ms))
    chans = 2 if pan_spread > 0 else x.shape[1]
    out = np.zeros((total + grain * 2, chans), dtype=np.float32)
    if len(x) < 16 or total <= 0:
        return out[:max(total, 0)]
    count = max(1, int(round(float(density) * millis / 1000.0)))
    starts = np.sort(rng.uniform(0, total, count))
    for at in starts:
        ordered = at / max(total, 1) * max(1, len(x) - grain)
        source = (1 - jitter) * ordered + jitter * rng.uniform(0, max(1, len(x) - grain))
        ratio = 2.0 ** (rng.uniform(-pitch_spread, pitch_spread) / 1200.0) if pitch_spread else 1.0
        positions = source + np.arange(grain) * ratio
        positions = positions[positions < len(x) - 1]
        if len(positions) < 8:
            continue
        lo = positions.astype(int)
        w = (positions - lo)[:, None]
        g = (x[lo] * (1 - w) + x[lo + 1] * w) * np.hanning(len(positions))[:, None]
        if pan_spread > 0:
            angle = (0.5 + rng.uniform(-0.5, 0.5) * float(pan_spread)) * np.pi / 2
            g = ac.mono(g) * np.array([[np.cos(angle), np.sin(angle)]]) * np.sqrt(2.0)
        i = int(at)
        out[i:i + len(g)] += g.astype(np.float32)
    return out[:total]


def loop(x, sr: float, millis: float, crossfade_ms: float = 50.0) -> Samples:
    """x repeated to `millis`, each repeat crossfaded into the next."""
    x = _f32(x)
    total = ac.ms(sr, millis)
    if len(x) < 4 or total <= len(x):
        return _length(x, total).copy()
    fade = int(np.clip(ac.ms(sr, crossfade_ms), 0, len(x) // 2))
    step = len(x) - fade
    piece = ac.fade(x, sr, crossfade_ms if fade else 0, crossfade_ms if fade else 0)
    out = np.zeros((total + len(x), x.shape[1]), dtype=np.float32)
    for at in range(0, total, max(1, step)):
        out[at:at + len(piece)] += piece
    out[:fade] = x[:fade]   # the first repeat begins as the sound does
    return out[:total]


def stutter(x, sr: float, millis: float, times: int, fade_ms: float = 3.0) -> Samples:
    x = _f32(x)
    piece = ac.fade(x[:max(8, ac.ms(sr, millis))], sr, fade_ms, fade_ms)
    return np.concatenate([piece] * max(1, int(times)), axis=0)


# ── Space ────────────────────────────────────────────────────────────────── #

def fx(x, sr: float, *plugins) -> Samples:
    """x through pedalboard plugins, in order."""
    import pedalboard
    x = _f32(x)
    return _f32(pedalboard.Pedalboard(list(plugins))(x.T, float(sr)).T) if len(x) else x


def reverb(x, sr: float, size: float = 0.6, wet: float = 0.3, damping: float = 0.5, tail_ms: Optional[float] = None) -> Samples:
    """A room around x; the result is longer by the tail (tail_ms, by default from the size)."""
    import pedalboard
    x = ac.channels(_f32(x), 2)
    tail = 500.0 + 5500.0 * float(size) if tail_ms is None else float(tail_ms)
    return fx(ac.pad(x, sr, tail), sr, pedalboard.Reverb(room_size=float(np.clip(size, 0, 1)), damping=float(damping),
                                                         wet_level=float(wet), dry_level=1.0 - float(wet), width=1.0))


def width(x, amount: float) -> Samples:
    """Stereo width: 0 mono, 1 unchanged, above 1 wider (the side signal scaled). Mono stays mono."""
    x = _f32(x)
    if x.shape[1] < 2:
        return x.copy()
    mid, side = (x[:, :1] + x[:, 1:2]) / 2, (x[:, :1] - x[:, 1:2]) / 2
    y = x.copy()
    y[:, :1], y[:, 1:2] = mid + side * amount, mid - side * amount
    return y


def pan(x, position: float) -> Samples:
    """Two channels: -1 left, 0 the middle, 1 right (equal power; a stereo sound is balanced)."""
    x = ac.channels(_f32(x), 2)
    angle = (float(np.clip(position, -1, 1)) + 1) * np.pi / 4
    return (x * np.array([[np.cos(angle), np.sin(angle)]], dtype=np.float32) * np.sqrt(2.0)).astype(np.float32)


__all__ = ["stretch", "fit", "pitch", "tune", "formant", "varispeed", "glide", "reverse",
           "split", "harmonic", "percussive", "layers", "band", "attack", "body",
           "cross", "morph", "convolve", "match_spectrum", "freeze", "blur",
           "envelope", "shape", "match_envelope", "decay", "swell", "loudness", "match_loudness",
           "granulate", "loop", "stutter", "fx", "reverb", "width", "pan"]
