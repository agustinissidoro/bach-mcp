"""
listen.py
---------
The models that say what a sound is, for analysis.py's description. All are ONNX models in
models/audio/ (`python py/main.py download <name>`, named in bachmcp.toml [audio]), full precision,
in the folders Max externals read too:

    Tagger(path).tags(x, sr)           AudioSet labels and their scores: [("Speech", 0.82), ...] (CED, sherpa-onnx)
    Clap(path).similarity(x, sr, text) how close the sound is to the words, -1..1 (CLAP, onnxruntime)
    Clap(path).embed(x, sr)            the sound's embedding, to compare many sounds with one text
    Pitch(path).describe(x, sr)        its pitch in midicents, how much of it is pitched, a value per step
                                       (PENN), as bachmcp.onnx~ and bachmcp.onnxb~ answer (their core's
                                       Model::pitch and summarise, which sources/bachmcp.onnx/check.py
                                       compares this with)

A tagger's folder: model.onnx and its labels (class_labels_indices.csv). A CLAP's folder:
onnx/audio_model.onnx, onnx/text_model.onnx and tokenizer.json, with either preprocessor_config.json
(LAION CLAP, Hugging Face's ONNX: the mel spectrogram is computed here) or bachmcp.json (CLAP2,
converted on download by utilities/export_onnx.py: the graph takes the waveform itself). A pitch
model's folder: onnx/pitch_model.onnx and bachmcp.json of kind "pitch" (converted by export_onnx.py).

They run in the worker of a buffer instance (worker.py), which keeps them loaded. sherpa-onnx and
onnxruntime are imported only here, and only when a model is used; LAION CLAP's mel spectrogram is
computed with librosa (ClapMel), as Hugging Face's ClapFeatureExtractor does, without its torch. Long sounds are listened to in a few windows spread over them (WINDOWS), not whole.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

TAGGER_SR = 16000
TAGGER_MIN = 2560  # CED needs 16 frames (0.16 s): a shorter sound is heard with silence after it (as the externals do)
CLAP_SR = 48000
WINDOW_SECONDS = 10.0
WINDOWS = 3
THREADS = 2
MANIFEST = "bachmcp.json"   # written by utilities/export_onnx.py next to a converted model
MANIFEST_FORMAT = 1         # the newest manifest this reader knows (export_onnx.EXPORT_FORMAT)
PITCH_STEP_MS = 250.0       # a pitch value every so often (the externals' @step, the core's PITCH_STEP_SECONDS)
PITCH_THRESHOLD = 0.1       # a value is pitched from this periodicity (@periodicity, PITCH_THRESHOLD)
PITCH_SILENCE_DB = -60.0    # values of quieter steps are not counted (PITCH_SILENCE_DB)


def _mono(x, sr: float, to_sr: int) -> np.ndarray:
    a = np.asarray(x, dtype=np.float32)
    a = a.mean(axis=1) if a.ndim == 2 else a
    if int(sr) != to_sr and a.size:
        import librosa
        a = librosa.resample(a, orig_sr=float(sr), target_sr=to_sr)
    return a.astype(np.float32)


def windows(mono: np.ndarray, sr: int, seconds: float = WINDOW_SECONDS, count: int = WINDOWS) -> List[np.ndarray]:
    """Up to `count` windows of `seconds`, spread evenly over the sound (all of it when shorter)."""
    size = int(seconds * sr)
    if len(mono) <= size:
        return [mono]
    starts = np.linspace(0, len(mono) - size, count).astype(int)
    return [mono[s:s + size] for s in starts]


class Tagger:
    """An AudioSet classifier (CED, through sherpa-onnx): 527 labels, each with its own score."""

    def __init__(self, path: str) -> None:
        import sherpa_onnx
        labels = _first(path, ".csv")
        config = sherpa_onnx.AudioTaggingConfig(
            model=sherpa_onnx.AudioTaggingModelConfig(ced=_onnx(path, "model.onnx"), num_threads=THREADS),
            labels=labels, top_k=_count_labels(labels))
        self.model = sherpa_onnx.AudioTagging(config)

    def tags(self, x, sr: float, top: int = 6, floor: float = 0.05) -> List[Tuple[str, float]]:
        mono = _mono(x, sr, TAGGER_SR)
        if not mono.size:
            return []
        scores: Dict[str, float] = {}
        for window in windows(mono, TAGGER_SR):
            window = np.pad(window, (0, max(0, TAGGER_MIN - len(window))))
            stream = self.model.create_stream()
            stream.accept_waveform(TAGGER_SR, window)
            for event in self.model.compute(stream):
                scores[event.name] = max(scores.get(event.name, 0.0), float(event.prob))
        best = sorted(scores.items(), key=lambda item: -item[1])[:top]
        return [(label, score) for label, score in best if score >= floor]


class Clap:
    """CLAP: sounds and words in one space, so a sound can be measured against a description."""

    def __init__(self, path: str) -> None:
        import onnxruntime
        from tokenizers import Tokenizer
        manifest = os.path.join(path, MANIFEST)
        self.manifest: Optional[Dict[str, Any]] = None
        if os.path.isfile(manifest):
            with open(manifest, encoding="utf-8") as f:
                self.manifest = json.load(f)
            if int(self.manifest.get("format", 0)) > MANIFEST_FORMAT:
                raise ValueError(f"{manifest} is newer than this bachmcp: download the model again or update")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = THREADS
        self.audio = onnxruntime.InferenceSession(_onnx(path, "audio_model.onnx"), options, providers=["CPUExecutionProvider"])
        self.text = onnxruntime.InferenceSession(_onnx(path, "text_model.onnx"), options, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(os.path.join(path, "tokenizer.json"))
        if self.manifest:  # CLAP2: the waveform goes in whole (up to max_seconds), words padded to the context
            audio, text = self.manifest["audio"], self.manifest["text"]
            self.sr, self.seconds, self.min_samples = int(audio["sample_rate"]), float(audio["max_seconds"]), int(audio["min_samples"])
            self.tokenizer.enable_truncation(int(text["text_context"]))
            self.tokenizer.enable_padding(length=int(text["text_context"]), pad_id=int(text["pad_id"]))
        else:              # LAION CLAP: 10 s windows, the mel spectrogram from preprocessor_config.json
            self.extractor = ClapMel(os.path.join(path, "preprocessor_config.json"))
            self.sr, self.seconds, self.min_samples = self.extractor.sr, WINDOW_SECONDS, 1
            self.tokenizer.enable_truncation(512)
            self.tokenizer.no_padding()

    def embed(self, x, sr: float) -> Optional[np.ndarray]:
        """The sound's unit embedding (the mean over its windows), or None for no sound."""
        mono = _mono(x, sr, self.sr)
        if not mono.size:
            return None
        found = []
        for window in windows(mono, self.sr, self.seconds):
            if self.manifest:
                window = np.pad(window, (0, max(0, self.min_samples - len(window))))
                feeds = {self.manifest["audio"]["input"]: window[None].astype(np.float32)}
            else:
                features = {"input_features": self.extractor(window)}
                feeds = {i.name: _as(features[i.name], i.type) for i in self.audio.get_inputs() if i.name in features}
            found.append(_unit(_embedding(self.audio, feeds)))
        mean = np.mean(found, axis=0)
        return mean / max(np.linalg.norm(mean), 1e-12)

    def embed_text(self, text: str) -> np.ndarray:
        encoded = self.tokenizer.encode(text)
        given = {"input_ids": [encoded.ids], "attention_mask": [encoded.attention_mask]}
        feeds = {i.name: _as(np.array(given[i.name]), i.type) for i in self.text.get_inputs() if i.name in given}
        return _unit(_embedding(self.text, feeds))

    def similarity(self, x, sr: float, text: str) -> Optional[float]:
        audio = self.embed(x, sr)
        return None if audio is None else float(audio @ self.embed_text(text))


class ClapMel:
    """LAION CLAP's input: the log-mel spectrogram of a 10 s window, (1, 1, frames, mels). The same numbers as
    Hugging Face's ClapFeatureExtractor with truncation "rand_trunc" (every LAION CLAP of the catalog): a shorter
    sound is repeated (padding "repeatpad"), then padded with silence; Slaney mel filters, power, 10 log10.
    A window is never longer than max_length_s (WINDOW_SECONDS), so the random crop is not needed."""

    def __init__(self, config_path: str) -> None:
        import librosa
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        if config.get("truncation", "rand_trunc") != "rand_trunc":
            raise ValueError(f"{config_path}: truncation {config.get('truncation')!r} is not supported (rand_trunc only)")
        self.sr = int(config.get("sampling_rate", CLAP_SR))
        self.n_fft = int(config.get("fft_window_size", 1024))
        self.hop = int(config.get("hop_length", 480))
        self.length = int(config.get("max_length_s", WINDOW_SECONDS) * self.sr)
        self.padding = config.get("padding", "repeatpad")
        self.filters = librosa.filters.mel(sr=self.sr, n_fft=self.n_fft, n_mels=int(config.get("feature_size", 64)),
                                           fmin=float(config.get("frequency_min", 50)), fmax=float(config.get("frequency_max", 14000)),
                                           htk=False, norm="slaney", dtype=np.float64)

    def __call__(self, window: np.ndarray) -> np.ndarray:
        import librosa
        x = np.asarray(window, dtype=np.float64)[:self.length]
        if 0 < len(x) < self.length:
            if self.padding == "repeat":
                x = np.tile(x, self.length // len(x) + 1)[:self.length]
            elif self.padding == "repeatpad":
                x = np.tile(x, self.length // len(x))
        x = np.pad(x, (0, self.length - len(x)))
        power = np.abs(librosa.stft(x, n_fft=self.n_fft, hop_length=self.hop, window="hann", center=True, pad_mode="reflect")) ** 2
        mel = 10.0 * np.log10(np.maximum(self.filters @ power, 1e-10))
        return mel.T[None, None].astype(np.float32)


class Pitch:
    """A pitch model (PENN's FCNF0++): the pitch of a sound and how clearly it has one, step by step.
    Every number is made as the externals' core makes it (model.cpp: Model::pitch, summarise)."""

    def __init__(self, path: str) -> None:
        import onnxruntime
        with open(os.path.join(path, MANIFEST), encoding="utf-8") as f:
            manifest = json.load(f)
        if int(manifest.get("format", 0)) > MANIFEST_FORMAT:
            raise ValueError(f"{os.path.join(path, MANIFEST)} is newer than this bachmcp: download the model again or update")
        if manifest.get("kind") != "pitch":
            raise ValueError(f"{path} is not a pitch model")
        p = manifest["pitch"]
        self.sr, self.window = int(p["sample_rate"]), int(p["window"])
        self.input, self.outputs = p.get("input", "frames"), list(p.get("outputs", ["pitch", "periodicity"]))
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = THREADS
        self.session = onnxruntime.InferenceSession(os.path.join(path, p.get("file", "onnx/pitch_model.onnx")), options,
                                                    providers=["CPUExecutionProvider"])

    def track(self, x, sr: float, step_ms: float = PITCH_STEP_MS) -> Optional[Dict[str, Any]]:
        """The sound cut into steps of step_ms (round(duration / step) of them, at least one): for each,
        `at` (seconds: the middle of the step, or of the sound when there is one), `hz` and `periodicity`
        (heard in the model's 128 ms around `at`, zeros outside the sound) and `level` (the RMS of the
        whole step, dBFS). None for no sound."""
        a = np.asarray(x, dtype=np.float32)
        a = a.mean(axis=1) if a.ndim == 2 else a
        n = len(a)
        if not n:
            return None
        nearest = lambda v: int(math.floor(v + 0.5))   # C's lround, for what is not negative
        step, seconds = step_ms / 1000.0, n / float(sr)
        count = max(1, nearest(seconds / step))
        at = np.array([seconds / 2]) if count == 1 else (np.arange(count) + 0.5) * step
        level = np.empty(count, dtype=np.float32)
        for i in range(count):
            lo = 0 if count == 1 else min(n, nearest(i * step * sr))
            hi = n if count == 1 else min(n, nearest((i + 1) * step * sr))
            power = float(np.sum(a[lo:hi].astype(np.float64) ** 2)) / (hi - lo) if hi > lo else 0.0
            level[i] = 10.0 * math.log10(max(power, 1e-12))
        mono = _mono(a, sr, self.sr)
        frames = np.zeros((count, self.window), dtype=np.float32)
        for i in range(count):
            start = nearest(at[i] * self.sr) - self.window // 2
            lo, hi = max(0, start), min(len(mono), start + self.window)
            if hi > lo:
                frames[i, lo - start:hi - start] = mono[lo:hi]
        hz, periodicity = [], []
        for first in range(0, count, 256):
            found = self.session.run(self.outputs, {self.input: frames[first:first + 256]})
            hz.append(found[0])
            periodicity.append(found[1])
        return {"step": step_ms, "at": at, "hz": np.concatenate(hz), "periodicity": np.concatenate(periodicity), "level": level}

    def describe(self, x, sr: float, step_ms: float = PITCH_STEP_MS, threshold: float = PITCH_THRESHOLD,
                 silence_db: float = PITCH_SILENCE_DB) -> Optional[Dict[str, Any]]:
        """What bachmcp.onnxb~ says of the sound: {"pitch": midicents (C5 = 6000), the median of the pitched
        values, None when none is; "pitched": the share of the sounding steps that are pitched;
        "periodicity": their mean; "step": ms; "pitches": one per step, 0 where not pitched;
        "periodicities": one per step}. Sounding: within 60 dB of the loudest step and above silence_db
        (every step of a sound that is all silence, none of them pitched). None for no sound."""
        t = self.track(x, sr, step_ms)
        if t is None:
            return None
        loudest = float(t["level"].max())
        silent = loudest < silence_db
        counted = np.ones(len(t["hz"]), dtype=bool) if silent else t["level"] >= max(silence_db, loudest - 60.0)
        pitched = counted & (t["periodicity"] >= threshold) & (not silent)
        pitches = np.where(pitched, 6900.0 + 1200.0 * np.log2(t["hz"].astype(np.float64) / 440.0), 0.0)
        return {"pitch": float(np.median(pitches[pitched])) if pitched.any() else None,
                "pitched": float(pitched.sum() / counted.sum()),
                "periodicity": float(t["periodicity"][counted].astype(np.float64).mean()),
                "step": step_ms, "pitches": pitches.tolist(), "periodicities": t["periodicity"].tolist()}


def _onnx(path: str, name: str) -> str:
    """The model file `name`, at the top of the folder or in its onnx/ (as Hugging Face repos keep it)."""
    for where in (os.path.join(path, name), os.path.join(path, "onnx", name)):
        if os.path.isfile(where):
            return where
    raise FileNotFoundError(f"no {name} in {path}")


def _first(path: str, ending: str) -> str:
    found = sorted(n for n in os.listdir(path) if n.endswith(ending))
    if not found:
        raise FileNotFoundError(f"no {ending} file in {path}")
    return os.path.join(path, found[0])


def _count_labels(csv: str) -> int:
    with open(csv, encoding="utf-8") as f:
        return max(1, sum(1 for line in f if line.strip()) - 1)  # less its header


def _as(array: np.ndarray, onnx_type: str) -> np.ndarray:
    kinds = {"tensor(int64)": np.int64, "tensor(int32)": np.int32, "tensor(bool)": np.bool_, "tensor(float16)": np.float16}
    return np.asarray(array).astype(kinds.get(onnx_type, np.float32))


def _embedding(session, feeds) -> np.ndarray:
    """The embedding a CLAP half answers: its output named *_embeds, else its first one."""
    names = [o.name for o in session.get_outputs()]
    name = next((n for n in names if n.endswith("embeds")), names[0])
    return np.asarray(session.run([name], feeds)[0], dtype=np.float32).reshape(-1)


def _unit(v: np.ndarray) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


VARIANTS = ("_fp16.onnx", "_quantized.onnx", ".int8.onnx", "_int8.onnx", "_uint8.onnx", "_q4.onnx", "_q4f16.onnx", "_bnb4.onnx")


def available(path: str) -> bool:
    """A whole model in the folder: a full-precision .onnx file at its top or in its onnx/
    (Hugging Face moves a file in only when complete)."""
    if not path or not os.path.isdir(path):
        return False
    for where in (path, os.path.join(path, "onnx")):
        if os.path.isdir(where) and any(n.endswith(".onnx") and not n.endswith(VARIANTS) for n in os.listdir(where)):
            return True
    return False


__all__ = ["Tagger", "Clap", "Pitch", "windows", "available"]
