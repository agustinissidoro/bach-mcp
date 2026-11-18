"""Freesound (https://freesound.org/docs/api/): search, study, download.

Two keys, both from https://freesound.org/apiv2/apply, in bachmcp.toml [audio]:
    freesound_client_id   the "Client id" of your API credential
    freesound_api_key     its "Client secret/Api key"

Search, sound information and previews need only the key. The original file needs OAuth2:
`python py/main.py freesound-login` once opens the authorization page, you paste the code
it shows, and the tokens are kept in freesound_token.json at the root of the repository
(not in git). The access token lasts a day and is refreshed by itself.

Study before downloading: `search` gives name, tags, description, license, duration and
Freesound's analysis; `preview` fetches the HQ mp3 preview so our own analysis
(text spectrogram, tagger, CLAP) can read it; `download` fetches the original.
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from ..config import REPO_ROOT, AudioConfig, ConfigError

API = "https://freesound.org/apiv2"
TOKEN_FILE = os.path.join(REPO_ROOT, "freesound_token.json")
DEFAULT_REDIRECT = "https://freesound.org/home/app_permissions/permission_granted/"
INFO = ("id,name,tags,description,license,username,duration,samplerate,channels,bitdepth,"
        "type,filesize,avg_rating,num_downloads,geotag,created,url,previews,images")
# Freesound's analysis (Essentia, AudioCommons), asked for by name in `fields`: none come by default.
DESCRIPTORS = ("pitch,pitch_var,note_midi,note_confidence,loudness,dynamic_range,brightness,"
               "warmth,hardness,depth,roughness,sharpness,boominess,reverbness,spectral_centroid,"
               "spectral_flatness,zero_crossing_rate,onset_count,bpm,bpm_confidence,tonality,"
               "tonality_confidence,single_event,loopable")
FIELDS = INFO + "," + DESCRIPTORS


class FreesoundError(RuntimeError):
    pass


class Freesound:
    def __init__(self, audio: AudioConfig):
        self.key = audio.freesound_api_key.strip()
        self.client_id = audio.freesound_client_id.strip()
        self.redirect_uri = audio.freesound_redirect_uri.strip() or DEFAULT_REDIRECT
        self.verifier = self.state = ""
        if not self.key:
            raise ConfigError("Freesound needs [audio] freesound_api_key in bachmcp.toml "
                              "(https://freesound.org/apiv2/apply)")

    # --- requests -------------------------------------------------------------------------
    def _request(self, url: str, data: dict | None = None, bearer: str = "") -> bytes:
        headers = {"User-Agent": "bach-mcp"}
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        try:
            with urllib.request.urlopen(urllib.request.Request(url, body, headers), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            raise FreesoundError(f"Freesound {e.code}: {detail}") from None

    def _get(self, path: str, **params: Any) -> Any:
        params["token"] = self.key
        url = f"{API}{path}?{urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, '')})}"
        return json.loads(self._request(url))

    # --- OAuth2 ---------------------------------------------------------------------------
    def authorize_url(self) -> str:
        """The page where the user grants access. Uses PKCE (S256) and a random state, as Freesound
        requires for credentials registered from November 2026; both are kept for login()."""
        import base64, hashlib, secrets
        if not self.client_id:
            raise ConfigError("the Freesound login needs [audio] freesound_client_id in bachmcp.toml "
                              "(the \"Client id\" next to your key at https://freesound.org/apiv2/apply)")
        self.verifier = secrets.token_urlsafe(64)
        self.state = secrets.token_urlsafe(16)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        return f"{API}/oauth2/authorize/?" + urllib.parse.urlencode(
            {"client_id": self.client_id, "response_type": "code", "redirect_uri": self.redirect_uri,
             "code_challenge": challenge, "code_challenge_method": "S256", "state": self.state})

    def _token_request(self, **data: str) -> dict:
        data.update(client_id=self.client_id, client_secret=self.key)
        token = json.loads(self._request(f"{API}/oauth2/access_token/", data))
        token["expires_at"] = time.time() + float(token.get("expires_in", 86400)) - 60
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(token, f, indent=2)
        try:
            os.chmod(TOKEN_FILE, 0o600)
        except OSError:
            pass
        return token

    def login(self, code: str) -> dict:
        """Exchange the code of the authorization page (from authorize_url() of this same object)
        for tokens. The code lasts 10 minutes and works once. Pasting the whole redirect URL works too:
        its code and state are read from it, and a state that differs stops the login."""
        if not self.verifier:
            raise FreesoundError("call authorize_url() first")
        code = code.strip()
        if code.startswith("http"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(code).query)
            if q.get("error"):
                raise FreesoundError(f"Freesound answered {q['error'][0]}: access was not granted")
            if q.get("state", [self.state])[0] != self.state:
                raise FreesoundError("the state of that URL is not this login's: run the login again")
            code = q.get("code", [""])[0]
        return self._token_request(grant_type="authorization_code", code=code,
                                   code_verifier=self.verifier, redirect_uri=self.redirect_uri)

    def access_token(self) -> str:
        try:
            with open(TOKEN_FILE, encoding="utf-8") as f:
                token = json.load(f)
        except (OSError, ValueError):
            raise FreesoundError("not logged in to Freesound: run `python py/main.py freesound-login`") from None
        if time.time() >= token.get("expires_at", 0):
            try:
                token = self._token_request(grant_type="refresh_token", refresh_token=token["refresh_token"])
            except (FreesoundError, KeyError):
                raise FreesoundError("the Freesound login expired: run `python py/main.py freesound-login` again") from None
        return token["access_token"]

    def me(self) -> dict:
        return json.loads(self._request(f"{API}/me/", bearer=self.access_token()))

    # --- study ----------------------------------------------------------------------------
    def search(self, query: str = "", filter: str = "", sort: str = "score",
               page_size: int = 15, page: int = 1) -> dict:
        """Text search. filter uses Freesound's syntax, also on descriptors: 'duration:[1 TO 10] tag:metal
        pitch:[435 TO 445]'. sort: score, duration_desc, downloads_desc ... or target values of
        descriptors, 'pitch:220,pitch_var:0' (nearest first).
        Answers {count, results: [sound]} with tags, description, license and analysis."""
        data = self._get("/search/", query=query, filter=filter, sort=sort, fields=FIELDS,
                         page_size=max(1, min(int(page_size), 150)), page=page)
        return {"count": data.get("count", 0), "results": [_sound(s) for s in data.get("results", [])]}

    def sound(self, sound_id: int) -> dict:
        return _sound(self._get(f"/sounds/{int(sound_id)}/", fields=FIELDS))

    def similar(self, sound_id: int, page_size: int = 15, space: str = "laion_clap") -> list[dict]:
        """Sounds like this one: space laion_clap (CLAP) or freesound_classic (descriptors)."""
        data = self._get(f"/sounds/{int(sound_id)}/similar/", fields=FIELDS, page_size=page_size,
                         similarity_space=space)
        return [_sound(s) for s in data.get("results", [])]

    def preview(self, sound_id: int, folder: str) -> str:
        """The HQ mp3 preview into folder (only the key needed): the file's path."""
        url = self.sound(sound_id)["preview"]
        path = os.path.join(folder, f"freesound-{int(sound_id)}-preview.mp3")
        return _save(self._request(url), path)

    # --- download -------------------------------------------------------------------------
    def download(self, sound_id: int, folder: str) -> dict:
        """The original file into folder (needs the login): the sound's information plus 'path'.
        A file already there is not downloaded again."""
        info = self.sound(sound_id)
        name = _safe(f"freesound-{info['id']}-{info['name']}")
        if not os.path.splitext(name)[1] and info.get("type"):
            name += "." + info["type"]
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            data = self._request(f"{API}/sounds/{info['id']}/download/", bearer=self.access_token())
            _save(data, path)
        info["path"] = path
        return info


def _sound(s: dict) -> dict:
    """One sound, flattened: what the model reads to choose before downloading."""
    previews, images = s.get("previews") or {}, s.get("images") or {}
    out = {k: s.get(k) for k in ("id", "name", "tags", "description", "license", "username", "duration",
                                 "samplerate", "channels", "bitdepth", "type", "filesize", "avg_rating",
                                 "num_downloads", "geotag", "created", "url")}
    out["preview"] = previews.get("preview-hq-mp3") or previews.get("preview-lq-mp3")
    out["spectrogram_png"] = images.get("spectral_l") or images.get("spectral_m")
    out["waveform_png"] = images.get("waveform_l") or images.get("waveform_m")
    a = {k: s[k] for k in DESCRIPTORS.split(",") if s.get(k) is not None}
    if isinstance(a.get("pitch"), (int, float)) and a["pitch"] > 0:   # Hz, and in bach's units
        a["pitch_mc"] = round(6900 + 1200 * math.log2(a["pitch"] / 440.0))
    if isinstance(a.get("note_midi"), (int, float)):   # Freesound's note names count A4 = 440: give midicents only
        a["note_mc"] = int(a.pop("note_midi")) * 100
    out["analysis"] = a
    return out


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_. " else "_" for c in name).strip()[:120]


def _save(data: bytes, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return path
