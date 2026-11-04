"""Device-only playlist items for local audio files."""

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

_LOCAL_APP_DATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
DATABASE_PATH = _LOCAL_APP_DATA / "Prism" / "playlist_items.sqlite3"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS local_playlist_tracks (
                user_id TEXT NOT NULL,
                playlist_id TEXT NOT NULL,
                track_key TEXT NOT NULL,
                track_data TEXT NOT NULL,
                PRIMARY KEY (user_id, playlist_id, track_key)
            )
            """
        )
        connection.commit()
        return connection
    except sqlite3.Error:
        connection.close()
        raise


def _track_key(track: dict) -> str:
    path = str(track.get("audio_path") or "")
    if not path:
        raise ValueError("The local track has no file path.")
    return os.path.normcase(os.path.abspath(path))


def fetch_local_playlist_tracks(user_id: str, playlist_id: str) -> list[dict]:
    with closing(_connect()) as connection:
        rows = connection.execute(
            """
            SELECT track_data FROM local_playlist_tracks
            WHERE user_id = ? AND playlist_id = ?
            ORDER BY rowid
            """,
            (user_id, playlist_id),
        ).fetchall()
    return [json.loads(row[0]) for row in rows]


def add_local_playlist_track(user_id: str, playlist_id: str, track: dict) -> bool:
    if track.get("source") != "local":
        raise ValueError("Only local audio files can be stored on this device.")
    key = _track_key(track)
    path = Path(str(track["audio_path"]))
    if not path.is_file():
        raise FileNotFoundError(f"Local audio file is unavailable: {path}")
    track_data = {**track, "device_only": True}
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO local_playlist_tracks
                    (user_id, playlist_id, track_key, track_data)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, playlist_id, key, json.dumps(track_data)),
            )
    return cursor.rowcount > 0


def remove_local_playlist_track(user_id: str, playlist_id: str, track: dict) -> bool:
    with closing(_connect()) as connection:
        with connection:
            cursor = connection.execute(
                """
                DELETE FROM local_playlist_tracks
                WHERE user_id = ? AND playlist_id = ? AND track_key = ?
                """,
                (user_id, playlist_id, _track_key(track)),
            )
    return cursor.rowcount > 0


def delete_local_playlist_tracks(user_id: str, playlist_id: str) -> None:
    with closing(_connect()) as connection:
        with connection:
            connection.execute(
                """
                DELETE FROM local_playlist_tracks
                WHERE user_id = ? AND playlist_id = ?
                """,
                (user_id, playlist_id),
            )
