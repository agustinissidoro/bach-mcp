"""The freesound tool: search Freesound, study a sound before downloading it, download it.

One tool with an action, so the buffer mode keeps few tools. Downloads go to sounds/freesound/ at
the root of the repository, each with a .json beside it (author, license, tags, Freesound's
analysis), ready to be added to the sound database.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from ..config import REPO_ROOT, ConfigError, load_config

FREESOUND_TOOLS = ("freesound",)
FOLDER = os.path.join(REPO_ROOT, "sounds", "freesound")

_DOC = """Search Freesound (freesound.org, free sounds under Creative Commons) and study a sound before
downloading it. Use it when the user wants new material that is not in their sound database. Do not use
it for sounds already in the database (audio_corpus finds those) or to process sound (send_buffer_process).

action:
  "search"   query (words) and/or filter, e.g. "duration:[0.5 TO 4] tag:metal pitch:[430 TO 450]".
             sort: "score" (default), "downloads_desc", "duration_asc", or target values, nearest
             first: "pitch:440,pitch_var:0". page_size up to 50.
  "similar"  sound_id: sounds that sound like it (CLAP).
  "study"    sound_id: its information plus our own analysis of its preview (levels, onsets, the
             text spectrogram). Study before downloading.
  "download" sound_id: the original file into sounds/freesound/ (with a .json of its author, license
             and tags). Answers its path. Only download what the user wants to keep.

Each sound: id, name, tags, description, license, author, duration (s) and Freesound's analysis
(pitch in Hz and pitch_mc in midicents, note_mc, loudness, brightness, hardness, roughness ...:
AudioCommons values 0-100). Mention the license to the user: some ask for attribution (CC BY) or forbid
commercial use (NC)."""


def _short(s: Dict[str, Any], desc: int = 200) -> Dict[str, Any]:
    out = {k: s.get(k) for k in ("id", "name", "tags", "license", "username", "duration")}
    out["description"] = (s.get("description") or "")[:desc]
    out["analysis"] = s.get("analysis") or {}
    return out


def freesound_action(action: str, query: str = "", filter: str = "", sort: str = "score",
                     sound_id: Optional[int] = None, page_size: int = 10) -> str:
    from ..audio_processing.freesound import Freesound, FreesoundError
    try:
        fs = Freesound(load_config().audio)
        action = (action or "").strip().lower()
        if action in ("similar", "study", "download") and not sound_id:
            return f"ERROR: {action} needs sound_id."
        if action == "search":
            if not (query or filter):
                return "ERROR: search needs query or filter."
            r = fs.search(query, filter, sort or "score", max(1, min(int(page_size), 50)))
            return json.dumps({"count": r["count"], "results": [_short(s) for s in r["results"]]})
        if action == "similar":
            return json.dumps([_short(s) for s in fs.similar(int(sound_id), max(1, min(int(page_size), 50)))])
        if action == "study":
            return _study(fs, int(sound_id))
        if action == "download":
            os.makedirs(FOLDER, exist_ok=True)
            info = fs.download(int(sound_id), FOLDER)
            with open(os.path.splitext(info["path"])[0] + ".json", "w", encoding="utf-8") as f:
                json.dump({**info, "source": "freesound"}, f, indent=2)
            return json.dumps({"path": info["path"], "name": info["name"], "license": info["license"],
                               "author": info["username"], "url": info["url"]})
        return "ERROR: action is search, similar, study or download."
    except (ConfigError, FreesoundError) as exc:
        return f"ERROR: {exc}"


def _study(fs, sound_id: int) -> str:
    import tempfile
    import librosa
    from ..audio_processing.analysis import describe
    info = fs.sound(sound_id)
    with tempfile.TemporaryDirectory() as tmp:
        x, sr = librosa.load(fs.preview(sound_id, tmp), sr=None, mono=False)
    x = x.T if x.ndim > 1 else x
    text = describe(x, sr, f"preview of {info['name']} (mp3: levels are close, the top band is cut)")
    return json.dumps(_short(info, 1000)) + "\n\n" + text


def _refused() -> str:
    """Why the active instance may not use Freesound ("" when it may): its soundfile_sources."""
    from .buffer_process_tools import instance_settings
    from .session import NoTarget, target
    try:
        t = target()
    except NoTarget:
        return ""
    if t.type == "buffer" and not instance_settings(t.name).freesound:
        return (f"ERROR: Freesound is not among {t.name}'s soundfile_sources (set in Max). "
                "Use only the sources it allows.")
    return ""


def register_freesound_tools(mcp) -> None:
    def freesound(action: str, query: str = "", filter: str = "", sort: str = "score",
                  sound_id: Optional[int] = None, page_size: int = 10) -> str:
        return _refused() or freesound_action(action, query, filter, sort, sound_id, page_size)
    freesound.__doc__ = _DOC
    mcp.tool()(freesound)


__all__ = ["register_freesound_tools", "freesound_action", "FREESOUND_TOOLS", "FOLDER"]
