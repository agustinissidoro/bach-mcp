"""
listen.py
---------
The two models that say what a sound is, for analysis.py's description. Both are ONNX models in
models/audio/ (`python py/main.py download <name>`, named in bachmcp.toml [audio]), full precision,
in the folders Max externals read too:

    Tagger(path).tags(x, sr)           AudioSet labels and their scores: [("Speech", 0.82), ...] (CED, sherpa-onnx)
    Clap(path).similarity(x, sr, text) how close the sound is to the words, -1..1 (CLAP, onnxruntime)
    Clap(path).embed(x, sr)            the sound's embedding, to compare many sounds with one text

A tagger's folder: model.onnx and its labels (class_labels_indices.csv). A CLAP's folder:
onnx/audio_model.onnx, onnx/text_model.onnx and tokenizer.json, with either preprocessor_config.json
(LAION CLAP, Hugging Face's ONNX: the mel spectrogram is computed here) or bachmcp.json (CLAP2,
converted on download by utilities/export_onnx.py: the graph takes the waveform itself).

They run in the worker of a buffer instance (worker.py), which keeps them loaded. sherpa-onnx,
onnxruntime and transformers (CLAP's mel spectrogram, numpy only) are imported only here, and only
when a model is used. Long sounds are listened to in a few windows spread over them (WINDOWS), not whole.
"""

from __future__ import annotations

import json
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
            from transformers import ClapFeatureExtractor
            self.extractor = ClapFeatureExtractor.from_pretrained(path)
            self.sr, self.seconds, self.min_samples = CLAP_SR, WINDOW_SECONDS, 1
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
                features = self.extractor(window, sampling_rate=self.sr, return_tensors="np")
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


__all__ = ["Tagger", "Clap", "windows", "available"]
