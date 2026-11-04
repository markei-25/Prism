"""Jamendo catalog and local audio source helpers."""

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

JAMENDO_API = "https://api.jamendo.com/v3.0"
SUPPORTED_AUDIO_EXTENSIONS = {".flac", ".mp3", ".ogg", ".oga", ".wav"}
MAX_TRACKS = 30
LOGGER = logging.getLogger(__name__)

JAMENDO_GENRES = {
    "All genres": "",
    "Classical": "classical",
    "Electronic": "electronic",
    "Hip-hop": "hiphop",
    "Jazz": "jazz",
    "Metal": "metal",
    "Pop": "pop",
    "Relaxation": "relaxation",
    "Rock": "rock",
    "Soundtrack": "soundtrack",
    "World": "world",
}


def _raise_walk_error(error: OSError) -> None:
    raise error


def _request_jamendo(resource: str, client_id: str, **params) -> list[dict]:
    query = {
        "client_id": client_id,
        "format": "json",
        "limit": 30,
        "include": "licenses",
        **params,
    }
    url = f"{JAMENDO_API}/{resource}/?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PrismMediaHub/1.0 (Jamendo API client)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = response.read(5_000_001)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Jamendo returned HTTP {error.code}.") from error
    except urllib.error.URLError as error:
        raise RuntimeError("Could not connect to Jamendo. Check your internet connection.") from error
    except OSError as error:
        raise RuntimeError(
            "Could not read Jamendo's response. Check your internet connection."
        ) from error

    if len(payload) > 5_000_000:
        raise RuntimeError("Jamendo returned an unexpectedly large response.")
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Jamendo returned an invalid response.") from error

    if not isinstance(data, dict):
        raise RuntimeError("Jamendo returned an unexpected response.")
    header = data.get("headers", {})
    if not isinstance(header, dict):
        raise RuntimeError("Jamendo returned an unexpected response.")
    if header.get("status") != "success" or header.get("code") != 0:
        detail = header.get("error_message") or "Jamendo could not complete the request."
        raise RuntimeError(str(detail))
    results = data.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Jamendo returned an unexpected response.")
    return [result for result in results if isinstance(result, dict)]


def _normalize_track(track: dict) -> dict | None:
    audio_url = str(track.get("audio") or "")
    if not audio_url.startswith("https://"):
        return None

    try:
        duration = int(track.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0

    return {
        "jamendo_id": str(track.get("id") or ""),
        "title": str(track.get("name") or "Unknown title"),
        "artist": str(track.get("artist_name") or "Unknown artist"),
        "album": str(track.get("album_name") or "Single"),
        "duration": duration,
        "audio_url": audio_url,
        "source": "jamendo",
        "share_url": str(track.get("shareurl") or "https://www.jamendo.com/"),
        "license_url": str(track.get("license_ccurl") or ""),
        "download_allowed": bool(track.get("audiodownload_allowed", False)),
    }


def search_jamendo_tracks(client_id: str, query: str = "", genre: str = "") -> list[dict]:
    if not client_id.strip():
        raise RuntimeError("Jamendo is not configured. Add JAMENDO_CLIENT_ID to your local .env file.")

    query = query.strip()
    common = {"tags": genre} if genre else {}
    if query:
        raw_tracks = _request_jamendo(
            "tracks",
            client_id,
            namesearch=query,
            **common,
        )
        artists = _request_jamendo(
            "artists",
            client_id,
            namesearch=query,
        )
        tracks_by_id = {
            str(track.get("id")): track
            for track in raw_tracks
            if track.get("id") is not None
        }
        for artist in artists[:5]:
            artist_id = artist.get("id")
            if artist_id is None:
                continue
            artist_results = _request_jamendo(
                "artists/tracks",
                client_id,
                id=artist_id,
                **common,
            )
            for artist_result in artist_results:
                artist_tracks = artist_result.get("tracks", [])
                if not isinstance(artist_tracks, list):
                    continue
                artist_name = str(artist_result.get("name") or "Unknown artist")
                for track in artist_tracks:
                    if not isinstance(track, dict) or track.get("id") is None:
                        continue
                    track.setdefault("artist_name", artist_name)
                    track.setdefault(
                        "shareurl",
                        f"https://www.jamendo.com/track/{track['id']}",
                    )
                    tracks_by_id.setdefault(str(track["id"]), track)
        raw_tracks = list(tracks_by_id.values())
    elif genre:
        raw_tracks = _request_jamendo(
            "tracks",
            client_id,
            tags=genre,
            featured=1,
            order="popularity_total_desc",
        )
    else:
        raw_tracks = _request_jamendo(
            "tracks",
            client_id,
            order="popularity_total_desc",
        )

    tracks = [_normalize_track(track) for track in raw_tracks]
    return [track for track in tracks if track is not None][:MAX_TRACKS]


def scan_audio_folder(folder: str) -> list[dict]:
    root = Path(folder).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError("The selected folder is no longer available.")

    tracks = []
    try:
        for current, directories, filenames in os.walk(root, onerror=_raise_walk_error):
            directories.sort()
            for filename in sorted(filenames):
                path = Path(current, filename)
                if path.suffix.casefold() not in SUPPORTED_AUDIO_EXTENSIONS:
                    continue
                tracks.append({
                    "title": path.stem,
                    "artist": "Local file",
                    "album": path.parent.name if path.parent != root else "Local files",
                    "duration": _audio_duration(path),
                    "audio_path": str(path),
                    "source": "local",
                })
    except OSError as error:
        raise RuntimeError(f"Could not scan the selected folder: {error}") from error
    return tracks


def _audio_duration(path: Path) -> int:
    try:
        audio = MutagenFile(path)
        return int(audio.info.length) if audio is not None and audio.info else 0
    except (OSError, MutagenError, ValueError, TypeError, AttributeError):
        LOGGER.warning("Could not read audio duration for %s", path, exc_info=True)
        return 0
