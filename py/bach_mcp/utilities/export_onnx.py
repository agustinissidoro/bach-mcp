"""
export_onnx.py
--------------
For the maintainer, not for downloads: converts a sound model that has no ONNX copy into one
folder ready to upload to Hugging Face, once. bachmcp's catalogue then names the uploaded repo,
and everyone downloads ONNX like any other sound model (the MCP and Max externals alike).

    python py/bach_mcp/utilities/export_onnx.py laion/clap2-medium-audioxl-s1B [--out <folder>]
        -> models/export/clap2-medium-audioxl-s1B-onnx/, then:
    hf upload <you>/clap2-medium-audioxl-s1B-onnx models/export/clap2-medium-audioxl-s1B-onnx

    python py/bach_mcp/utilities/export_onnx.py --card laion/clap2-medium-audioxl-s1B <folder>
        writes only README.md and LICENSE into a folder already converted

A converted CLAP2 folder (LAION CLAP2, open_clip 4.2+):

    onnx/audio_model.onnx   waveform (1, samples) float32 mono at bachmcp.json's sample_rate,
                            min_samples .. max_seconds long -> audio_embeds (1, dim), unit length.
                            The log-mel spectrogram and its patches are inside the graph.
    onnx/text_model.onnx    input_ids (1, text_context) int64, padded with pad_id -> text_embeds (1, dim), unit length
    tokenizer.json          the words' ids (bos and eos added by it; pad to text_context with pad_id)
    bachmcp.json            the manifest: what the two graphs take (EXPORT_FORMAT, sample_rate, ...)
    README.md, LICENSE      the model card (licence, credit, what changed) and Apache-2.0's text

The conversion is checked: the ONNX must answer as the original (a tone, noise, a 0.2 s grain and
words, cosine >= 0.9999), or nothing is written. Needs torch, open_clip_torch, onnx and onnxscript
(requirements/export.txt), and no file of bach-mcp: it runs on its own.

    python py/bach_mcp/utilities/export_onnx.py maxrmorrison/fcnf0-plus-plus
        -> models/export/fcnf0-plus-plus-onnx/ (PENN's FCNF0++ pitch model; needs torch and onnx only)

A converted pitch folder (PENN, Morrison et al. 2023):

    onnx/pitch_model.onnx   frames (count, 1024) float32: windows of mono sound at 8 kHz, one per pitch
                            value wanted -> pitch (count) in Hz, periodicity (count) 0..1.
                            PENN's decoding is inside the graph: the most likely of its 1440 pitch bins
                            (5 cents each, from 31 Hz), refined by the expected value of the 19 bins
                            around it; periodicity is 1 - the entropy of the bins (PENN's "entropy").
    bachmcp.json            the manifest (kind "pitch": sample_rate, window, hop, fmin, fmax ...)
    README.md, LICENSE      the model card and MIT's text

Its check: the graph must give the pitch and periodicity of the same network in PyTorch (within
0.01 cents and 1e-4) on tones, a sweep, noise and silence, and find a 440 Hz tone within 10 cents.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import tempfile
import urllib.request
from typing import Callable

EXPORT_FORMAT = 1  # bachmcp.json "format": a reader refuses a manifest newer than it knows
MANIFEST = "bachmcp.json"
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXPORT_DIR = os.path.join(REPO_ROOT, "models", "export")
APACHE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"
CONVERTER_URL = "https://github.com/agustinissidoro/bach-mcp/blob/main/py/bach_mcp/utilities/export_onnx.py"
KINDS = {"clap2-": "clap2", "fcnf0": "pitch"}  # a repo's name -> how it is converted
PENN_URL = "https://github.com/interactiveaudiolab/penn"


def export(repo: str, target: str, say: Callable[[str], None] = print) -> None:
    """Convert `repo` into `target` (onnx/, tokenizer, bachmcp.json), then write its model card."""
    name = repo.split("/")[-1]
    kind = next((k for prefix, k in KINDS.items() if name.startswith(prefix)), None)
    if kind is None:
        raise ValueError(f"no ONNX conversion known for {repo}")
    from huggingface_hub import snapshot_download
    with tempfile.TemporaryDirectory(prefix="bachmcp-export-") as source:
        say(f"downloading {repo}")
        snapshot_download(repo, local_dir=source)
        say(f"converting {repo} to ONNX")
        {"clap2": _clap2, "pitch": _penn}[kind](source, target)
    write_card(repo, target)
    say(f"done: {target}")


def _clap2(source: str, target: str) -> None:
    import numpy as np
    import open_clip
    import timm.models.naflexvit as naflexvit
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from open_clip.audio.dsp import mel_filterbank

    model, preprocess = open_clip.create_model_from_pretrained(f"local-dir:{source}")
    model.eval()
    pre = preprocess()
    cfg = pre.cfg
    tokenizer = open_clip.get_tokenizer(f"local-dir:{source}")
    bins = cfg.window_size // 2 + 1
    rows = cfg.n_mels // cfg.patch_freq  # frequency rows of patches

    # timm reads the patch grid from the coordinates' values, which does not export; for one clip
    # (rows outer, time inner) it is the shape: (rows, patches / rows), and every patch is real.
    def grid(coord):
        return [(rows, coord.shape[1] // rows)] * coord.shape[0]

    def rope_one_clip(self, x, patch_coord):
        assert not self.rope_is_mixed and x.shape[0] == 1
        return self.rope.get_embed(shape=grid(patch_coord)[0], dtype=x.dtype)[None, None]

    naflexvit.calculate_naflex_grid_sizes = grid
    naflexvit.NaFlexVit._generate_rope_naflex = rope_one_clip

    class Audio(nn.Module):
        """open_clip's AudioNaFlexPatchify and encode_audio(normalize=True) as one graph: the STFT as two
        convolutions (a centred, reflect-padded periodic Hann STFT), HTK mel, power in dB, the last time
        patch filled with the clip's lowest value ("floor"), 16x16 patches, the tower."""

        def __init__(self):
            super().__init__()
            self.audio = model.audio
            n = torch.arange(cfg.window_size, dtype=torch.float64)
            k = torch.arange(bins, dtype=torch.float64)[:, None]
            window = torch.hann_window(cfg.window_size, dtype=torch.float64)
            angle = 2 * math.pi * k * n / cfg.window_size
            self.register_buffer("cos", (torch.cos(angle) * window).float()[:, None, :])
            self.register_buffer("sin", (torch.sin(angle) * window).float()[:, None, :])
            self.register_buffer("fb", mel_filterbank(bins, float(cfg.fmin), float(cfg.fmax), cfg.n_mels,
                                                      cfg.sample_rate).float())

        def forward(self, waveform):
            half = cfg.window_size // 2
            x = F.pad(waveform[:, None, :], (half, half), mode="reflect")
            re = F.conv1d(x, self.cos, stride=cfg.hop_size)
            im = F.conv1d(x, self.sin, stride=cfg.hop_size)
            mel = torch.matmul((re * re + im * im).transpose(1, 2), self.fb)[0]
            mel = 10.0 * torch.log10(torch.clamp(mel, min=1e-10))                      # (frames, n_mels)
            frames = mel.shape[0]
            columns = (frames + cfg.patch_time - 1) // cfg.patch_time
            floor = mel.min()
            mel = F.pad(mel - floor, (0, 0, 0, columns * cfg.patch_time - frames)) + floor
            patches = (mel.reshape(1, columns, cfg.patch_time, rows, cfg.patch_freq)
                       .permute(3, 1, 0, 4, 2).reshape(rows * columns, -1))
            coord = torch.stack([torch.arange(rows).repeat_interleave(columns), torch.arange(columns).repeat(rows)], 1)
            batch = {"patches": patches[None], "patch_coord": coord[None],
                     "patch_valid": torch.ones(1, rows * columns, dtype=torch.bool)}
            return F.normalize(self.audio(batch), dim=-1)

    class Text(nn.Module):
        def __init__(self):
            super().__init__()
            self.text = model.text

        def forward(self, input_ids):
            return F.normalize(self.text(input_ids), dim=-1)

    audio, text = Audio().eval(), Text().eval()
    sr = cfg.sample_rate
    max_seconds = 30
    out = os.path.join(target, "onnx.partial")  # renamed onnx/ once checked: a failed export is never "downloaded"
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    ids = tokenizer(["A cello plays a slow melody."])
    samples = torch.export.Dim("samples", min=cfg.window_size, max=sr * max_seconds)
    torch.onnx.export(audio, (torch.zeros(1, sr * 3),), os.path.join(out, "audio_model.onnx"), dynamo=True,
                      input_names=["waveform"], output_names=["audio_embeds"],
                      dynamic_shapes={"waveform": {1: samples}}, external_data=False, opset_version=18)
    torch.onnx.export(text, (ids,), os.path.join(out, "text_model.onnx"), dynamo=True,
                      input_names=["input_ids"], output_names=["text_embeds"], external_data=False, opset_version=18)

    # The ONNX must answer as open_clip does: a tone, noise, a grain shorter than one patch, and words.
    import onnxruntime
    audio_session = onnxruntime.InferenceSession(os.path.join(out, "audio_model.onnx"))
    text_session = onnxruntime.InferenceSession(os.path.join(out, "text_model.onnx"))
    t = np.arange(sr * 3) / sr
    tests = [0.3 * np.sin(2 * np.pi * 440 * t), np.random.default_rng(0).uniform(-0.3, 0.3, int(sr * 7.3)),
             0.5 * np.sin(2 * np.pi * 1000 * t[:int(sr * 0.2)])]
    with torch.no_grad():
        for x in tests:
            w = torch.from_numpy(x.astype(np.float32))
            want = model.encode_audio({k: v[None] for k, v in pre((w[None], sr)).items()}, normalize=True)[0].numpy()
            got = audio_session.run(None, {"waveform": x.astype(np.float32)[None]})[0][0]
            _same(want, got, "audio")
        want = model.encode_text(ids, normalize=True)[0].numpy()
        _same(want, text_session.run(None, {"input_ids": ids.numpy()})[0][0], "text")

    for name in ("tokenizer.json", "tokenizer_config.json", "config.json", "processor_config.json"):
        if os.path.exists(os.path.join(source, name)):
            shutil.copy(os.path.join(source, name), os.path.join(target, name))
    manifest = {
        "format": EXPORT_FORMAT, "kind": "clap2", "from": "open_clip " + open_clip.__version__,
        "audio": {"file": "onnx/audio_model.onnx", "input": "waveform", "output": "audio_embeds",
                  "sample_rate": sr, "channels": 1, "min_samples": cfg.window_size, "max_seconds": max_seconds},
        "text": {"file": "onnx/text_model.onnx", "input": "input_ids", "output": "text_embeds",
                 "tokenizer": "tokenizer.json", "text_context": int(ids.shape[1]), "pad_id": int(ids[0, -1])},
        "embedding_dim": int(want.shape[0]), "normalized": True,
    }
    with open(os.path.join(target, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    shutil.rmtree(os.path.join(target, "onnx"), ignore_errors=True)
    os.replace(out, os.path.join(target, "onnx"))


def _penn(source: str, target: str) -> None:
    """PENN's FCNF0++ (penn 1.0: model/fcnf0.py, decode.py, periodicity.py, config/defaults.py)."""
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    sr, window, hop, bins, cents_per_bin, fmin, local = 8000, 1024, 80, 1440, 5.0, 31.0, 19

    def block(i, o, length, pool=False):
        layers = [nn.Conv1d(i, o, 32), nn.ReLU()]
        if pool:
            layers.append(nn.MaxPool1d(2, 2))
        return nn.Sequential(*layers, nn.LayerNorm((o, length)))

    class Fcnf0(nn.Sequential):   # the names of penn's state dict: 0.0 (conv), 0.2 or 0.3 (norm), ..., 6
        def __init__(self):
            super().__init__(block(1, 256, 481, True), block(256, 32, 225, True), block(32, 32, 97, True),
                             block(32, 128, 66), block(128, 256, 35), block(256, 512, 4), nn.Conv1d(512, bins, 4))

    class Pitch(nn.Module):
        """Fcnf0.forward, decode.Argmax (local expected value) and periodicity.entropy as one graph."""

        def __init__(self, net):
            super().__init__()
            self.net = net
            self.register_buffer("offsets", torch.arange(local))

        def forward(self, frames):
            logits = self.net(frames[:, None, 16:-15])[:, :, 0]                  # (count, bins)
            p = F.softmax(logits, dim=1)
            periodicity = 1 + (p * torch.log(p + 1e-7)).sum(dim=1) / math.log(bins)
            padded = F.pad(logits, (local // 2, local // 2), value=-float("inf"))
            index = logits.argmax(dim=1, keepdim=True) + self.offsets[None]      # into padded
            cents = cents_per_bin * torch.clamp(index - local // 2, min=0).to(logits.dtype)
            near = F.softmax(torch.gather(padded, 1, index), dim=1)
            return fmin * 2 ** ((near * cents).sum(dim=1) / 1200), periodicity

    weights = [f for f in os.listdir(source) if f.endswith(".pt")]
    if len(weights) != 1:
        raise RuntimeError(f"expected one .pt file of weights, found {weights}")
    net = Fcnf0()
    net.load_state_dict(torch.load(os.path.join(source, weights[0]), map_location="cpu", weights_only=True)["model"])
    model = Pitch(net).eval()

    out = os.path.join(target, "onnx.partial")  # renamed onnx/ once checked
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    count = torch.export.Dim("count", min=1, max=1 << 20)
    torch.onnx.export(model, (torch.zeros(3, window),), os.path.join(out, "pitch_model.onnx"), dynamo=True,
                      input_names=["frames"], output_names=["pitch", "periodicity"],
                      dynamic_shapes={"frames": {0: count}}, external_data=False, opset_version=18)

    # The ONNX must answer as the network in PyTorch, and the network must hear a tone's pitch.
    import onnxruntime
    session = onnxruntime.InferenceSession(os.path.join(out, "pitch_model.onnx"))
    t = np.arange(sr * 2) / sr
    rng = np.random.default_rng(0)
    sweep = 0.3 * np.sin(2 * np.pi * np.cumsum(110 * 2 ** (t * 1.5)) / sr)
    harmonics = sum(0.3 / k * np.sin(2 * np.pi * 440 * k * t) for k in range(1, 6))
    tests = {"tone": harmonics, "sine": 0.3 * np.sin(2 * np.pi * 220 * t), "sweep": sweep,
             "noise": rng.uniform(-0.3, 0.3, sr * 2), "silence": np.zeros(sr)}
    for name, x in tests.items():
        x = np.pad(x.astype(np.float32), window // 2)
        frames = np.stack([x[i:i + window] for i in range(0, len(x) - window + 1, hop)])
        with torch.no_grad():
            want_pitch, want_periodicity = (v.numpy() for v in model(torch.from_numpy(frames)))
        got_pitch, got_periodicity = session.run(None, {"frames": frames})
        cents = np.abs(1200 * np.log2(got_pitch / want_pitch)).max()
        if cents > 0.01 or np.abs(got_periodicity - want_periodicity).max() > 1e-4:
            raise RuntimeError(f"the ONNX pitch model does not answer as the original ({name}: {cents:.4f} cents)")
        if name == "tone":
            heard = float(np.median(got_pitch[10:-10]))
            if abs(1200 * math.log2(heard / 440)) > 10:
                raise RuntimeError(f"the pitch model hears {heard:.1f} Hz in a 440 Hz tone: wrong weights or layout")

    manifest = {
        "format": EXPORT_FORMAT, "kind": "pitch", "from": "penn 1.0.0 (fcnf0++)",
        "pitch": {"file": "onnx/pitch_model.onnx", "input": "frames", "outputs": ["pitch", "periodicity"],
                  "sample_rate": sr, "channels": 1, "window": window, "hop": hop,
                  "fmin": fmin, "fmax": fmin * 2 ** (bins * cents_per_bin / 1200),
                  "bins": bins, "cents_per_bin": cents_per_bin, "decoder": "argmax, local expected value",
                  "periodicity": "entropy"},
    }
    with open(os.path.join(target, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    shutil.rmtree(os.path.join(target, "onnx"), ignore_errors=True)
    os.replace(out, os.path.join(target, "onnx"))


MIT = """MIT License

Copyright (c) 2022 Interactive Audio Lab

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def _pitch_card(repo: str, target: str, manifest: dict) -> None:
    name = repo.split("/")[-1]
    p = manifest["pitch"]
    card = f"""---
license: mit
base_model: {repo}
library_name: onnx
tags:
  - audio
  - pitch-estimation
  - f0
  - penn
  - onnx
---

# {name} (ONNX)

**An unofficial ONNX conversion** of [{repo}](https://huggingface.co/{repo}): FCNF0++, the pitch and
periodicity estimator of [PENN]({PENN_URL}) (Morrison, Hsieh, Pruyne, Pardo: *Cross-domain Neural Pitch and
Periodicity Estimation*, 2023). It is not made or endorsed by its authors, to whom all credit for the model
goes; see [PENN]({PENN_URL}) for its training data, scores and limitations.

## What changed

- The network is exported to ONNX (opset 18, float32). **The weights are unchanged.**
- PENN's decoding is inside the graph: the most likely of the {p["bins"]} pitch bins ({p["cents_per_bin"]:g} cents
  each, from {p["fmin"]:g} Hz), refined by the expected value of the 19 bins around it (PENN's `argmax` decoder
  with `local_expected_value`), and the entropy-based periodicity. PENN's default Viterbi decoder is not included.
- The conversion was checked against the same network in PyTorch ({manifest.get("from", "")}): pitch within
  0.01 cents and periodicity within 1e-4, on tones, a sweep, noise and silence.

## Files

| File | |
|---|---|
| `onnx/pitch_model.onnx` | `{p["input"]}`: float32 `(count, {p["window"]})`, windows of mono sound at **{p["sample_rate"]} Hz**, one per value wanted -> `pitch`: `(count)` in Hz, `periodicity`: `(count)` 0..1 |
| `bachmcp.json` | the same facts, for programs |

## Use (Python)

```python
import numpy as np, onnxruntime as ort

session = ort.InferenceSession("onnx/pitch_model.onnx")
x = np.zeros({p["sample_rate"]} * 2, np.float32)               # your sound: mono, {p["sample_rate"]} Hz
x = np.pad(x, {p["window"] // 2})                              # so that value i is at i * 10 ms
frames = np.stack([x[i:i + {p["window"]}] for i in range(0, len(x) - {p["window"] - 1}, {p["hop"]})])
pitch, periodicity = session.run(None, {{"{p["input"]}": frames}})   # Hz, 0..1 (low: no pitch there)
```

The pitch is between {p["fmin"]:g} and {p["fmax"]:g} Hz. Where the periodicity is low the pitch means nothing.
Any hop works: the network hears each window on its own.

Converted with [export_onnx.py]({CONVERTER_URL}) for [bach-mcp](https://github.com/agustinissidoro/bach-mcp).

## License and citation

MIT, as PENN (the full text is in `LICENSE`). Please cite the original authors:

```bibtex
@misc{{morrison2023crossdomain,
    title={{Cross-domain Neural Pitch and Periodicity Estimation}},
    author={{Morrison, Max and Hsieh, Caedon and Pruyne, Nathan and Pardo, Bryan}},
    year={{2023}},
    eprint={{2301.12258}},
    archivePrefix={{arXiv}}
}}
```
"""
    with open(os.path.join(target, "README.md"), "w", encoding="utf-8") as f:
        f.write(card)
    with open(os.path.join(target, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(MIT)


def _same(want, got, what: str) -> None:
    import numpy as np
    cosine = float(np.dot(want, got) / max(np.linalg.norm(want) * np.linalg.norm(got), 1e-12))
    if cosine < 0.9999:
        raise RuntimeError(f"the ONNX {what} model does not answer as the original (cosine {cosine:.5f})")


def write_card(repo: str, target: str) -> None:
    """README.md (the model card: licence, credit, what changed, how to use it) and LICENSE."""
    with open(os.path.join(target, MANIFEST), encoding="utf-8") as f:
        manifest = json.load(f)
    if manifest.get("kind") == "pitch":
        return _pitch_card(repo, target, manifest)
    name = repo.split("/")[-1]
    audio, text = manifest["audio"], manifest["text"]
    card = f"""---
license: apache-2.0
base_model: {repo}
library_name: onnx
pipeline_tag: feature-extraction
tags:
  - audio
  - clap
  - onnx
  - zero-shot-audio-classification
language: en
---

# {name} (ONNX)

**An unofficial ONNX conversion** of [{repo}](https://huggingface.co/{repo}), LAION's CLAP2 contrastive
audio-text model. It is not made or endorsed by LAION. All credit for the model goes to its authors; see the
[original model card](https://huggingface.co/{repo}) for its training data, scores, intended use and limitations.

## What changed

- The audio and text towers are exported to ONNX (opset 18, float32). **The weights are unchanged.**
- The audio front end is inside the audio graph: a centred, reflect-padded Hann STFT (n_fft 1024, hop 320),
  a 128-band HTK mel filter bank (50 Hz to 16 kHz), power in dB, the last time patch filled with the clip's
  lowest value, and 16x16 patches, as open_clip's `AudioNaFlexPatchify` does. The graph takes the waveform.
- Both outputs are L2-normalised, as `encode_audio(..., normalize=True)` and `encode_text(..., normalize=True)`.
- The conversion was checked against open_clip {manifest.get("from", "").replace("open_clip ", "")}: cosine similarity
  >= 0.9999 between the original's and the ONNX embeddings, for a tone, noise, a 0.2 s clip and English text.

## Files

| File | |
|---|---|
| `onnx/audio_model.onnx` | `{audio["input"]}`: float32 `(1, samples)`, mono, **{audio["sample_rate"]} Hz**, {audio["min_samples"]} samples to {audio["max_seconds"]} s -> `{audio["output"]}`: `(1, {manifest["embedding_dim"]})` |
| `onnx/text_model.onnx` | `{text["input"]}`: int64 `(1, {text["text_context"]})` -> `{text["output"]}`: `(1, {manifest["embedding_dim"]})` |
| `tokenizer.json` | from the original repo (GPT-2 style BPE; adds the start and end tokens). Pad to {text["text_context"]} with id {text["pad_id"]}. |
| `bachmcp.json` | the same facts, for programs |

## Use (Python)

```python
import json, numpy as np, onnxruntime as ort
from tokenizers import Tokenizer

audio = ort.InferenceSession("onnx/audio_model.onnx")
text = ort.InferenceSession("onnx/text_model.onnx")
tok = Tokenizer.from_file("tokenizer.json")
tok.enable_truncation({text["text_context"]}); tok.enable_padding(length={text["text_context"]}, pad_id={text["pad_id"]})

wave = np.zeros({audio["sample_rate"]} * 3, np.float32)            # your sound: mono, {audio["sample_rate"]} Hz
a = audio.run(None, {{"{audio["input"]}": wave[None]}})[0][0]
t = text.run(None, {{"{text["input"]}": np.array([tok.encode("A cello plays a slow melody.").ids])}})[0][0]
print(float(a @ t))                                      # cosine similarity
```

Sounds longer than {audio["max_seconds"]} s: cut them into pieces and average the embeddings (the original was
trained on clips of at most 30 s). Write prompts as short full sentences, as the original card advises.

Converted with [export_onnx.py]({CONVERTER_URL}) for [bach-mcp](https://github.com/agustinissidoro/bach-mcp).

## License and citation

Apache-2.0, as the original (the full text is in `LICENSE`). Please cite the original authors:

```bibtex
@misc{{wijngaard2026laionaudioxlwebscalecorpusscaling,
      title={{LAION-Audio-XL: A Web-Scale Corpus and Scaling Studies for Contrastive Language-Audio Pretraining}},
      author={{Gijs Wijngaard and Felix Förster and Ross Wightman and Marianna Nezhurina and Christoph Schuhmann and Jenia Jitsev and A. Sophia Koepke}},
      year={{2026}},
      eprint={{2611.11592}},
      archivePrefix={{arXiv}},
      primaryClass={{cs.SD}},
      url={{https://arxiv.org/abs/2611.11592}},
}}
```
"""
    with open(os.path.join(target, "README.md"), "w", encoding="utf-8") as f:
        f.write(card)
    with urllib.request.urlopen(APACHE_URL, timeout=30) as r:
        licence = r.read().decode("utf-8")
    with open(os.path.join(target, "LICENSE"), "w", encoding="utf-8") as f:
        f.write(licence)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Convert a sound model to ONNX, ready to upload (see the docstring).")
    parser.add_argument("repo", help="the original Hugging Face repo, e.g. laion/clap2-medium-audioxl-s1B")
    parser.add_argument("folder", nargs="?", help="where it goes (default: models/export/<name>-onnx)")
    parser.add_argument("--card", action="store_true", help="only write README.md and LICENSE into a converted folder")
    args = parser.parse_args(argv)
    target = args.folder or os.path.join(EXPORT_DIR, args.repo.split("/")[-1] + "-onnx")
    if args.card:
        write_card(args.repo, target)
    else:
        export(args.repo, target)
    print(f"upload: hf upload <you>/{os.path.basename(os.path.normpath(target))} {os.path.relpath(target)}")
    return 0


__all__ = ["export", "write_card", "EXPORT_FORMAT", "MANIFEST"]


if __name__ == "__main__":
    sys.exit(main())
