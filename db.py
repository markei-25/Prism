# db.py
"""Supabase media and playlist database operations for Prism."""

from supabase_client import supabase


def fetch_all_songs() -> list[dict]:
    """Retrieves all songs ordered by creation date."""
    response = supabase.table("songs").select("*").order("created_at", desc=True).execute()
    return response.data or []

def fetch_user_playlists(user_id: str) -> list[dict]:
    """Retrieves all playlists created by a specific user."""
    response = supabase.table("playlists").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
    return response.data or []


def create_playlist(user_id: str, name: str) -> dict:
    """Creates a new playlist record linked to the active user."""
    normalized_name = name.strip()
    if not normalized_name or len(normalized_name) > 80:
        raise ValueError("Playlist names must be between 1 and 80 characters.")
    response = (
        supabase.table("playlists")
        .insert({"user_id": user_id, "name": normalized_name})
        .select("*")
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase did not return the created playlist.")
    return response.data[0]


def rename_playlist(user_id: str, playlist_id: str, name: str) -> dict:
    """Renames a playlist owned by the active user."""
    normalized_name = name.strip()
    if not normalized_name or len(normalized_name) > 80:
        raise ValueError("Playlist names must be between 1 and 80 characters.")
    response = (
        supabase.table("playlists")
        .update({"name": normalized_name})
        .eq("id", playlist_id)
        .eq("user_id", user_id)
        .select("*")
        .execute()
    )
    if not response.data:
        raise LookupError("Playlist not found or no longer accessible.")
    return response.data[0]


def delete_playlist(user_id: str, playlist_id: str) -> None:
    """Deletes a playlist owned by the active user."""
    response = (
        supabase.table("playlists")
        .delete()
        .eq("id", playlist_id)
        .eq("user_id", user_id)
        .select("id")
        .execute()
    )
    if not response.data:
        raise LookupError("Playlist not found or no longer accessible.")


def fetch_playlist_tracks(user_id: str, playlist_id: str) -> list[dict]:
    """Returns Jamendo tracks in a playlist owned by the active user."""
    response = (
        supabase.table("playlist_tracks")
        .select("track_data")
        .eq("playlist_id", playlist_id)
        .eq("user_id", user_id)
        .order("position")
        .execute()
    )
    return [row["track_data"] for row in (response.data or [])]


def add_playlist_track(user_id: str, playlist_id: str, track: dict) -> None:
    """Adds a Jamendo track to a playlist; local file paths stay on-device."""
    track_id = str(track.get("jamendo_id") or "").strip()
    if track.get("source") != "jamendo" or not track_id:
        raise ValueError("Only Jamendo tracks can be synced to a playlist.")

    existing = (
        supabase.table("playlist_tracks")
        .select("position")
        .eq("playlist_id", playlist_id)
        .eq("user_id", user_id)
        .order("position", desc=True)
        .limit(1)
        .execute()
    )
    position = int(existing.data[0]["position"]) + 1 if existing.data else 0
    track_data = {
        key: track[key]
        for key in (
            "jamendo_id",
            "title",
            "artist",
            "album",
            "duration",
            "audio_url",
            "source",
            "share_url",
            "license_url",
            "download_allowed",
        )
        if key in track
    }
    response = (
        supabase.table("playlist_tracks")
        .insert(
            {
                "playlist_id": playlist_id,
                "user_id": user_id,
                "track_key": track_id,
                "track_data": track_data,
                "position": position,
            }
        )
        .select("id")
        .execute()
    )
    if not response.data:
        raise RuntimeError("Supabase did not confirm the playlist track was added.")


def remove_playlist_track(user_id: str, playlist_id: str, track: dict) -> None:
    """Removes a Jamendo track from a playlist owned by the active user."""
    track_id = str(track.get("jamendo_id") or "").strip()
    if not track_id:
        raise ValueError("The Jamendo track has no identifier.")
    response = (
        supabase.table("playlist_tracks")
        .delete()
        .eq("playlist_id", playlist_id)
        .eq("user_id", user_id)
        .eq("track_key", track_id)
        .select("id")
        .execute()
    )
    if not response.data:
        raise LookupError("Playlist track not found or no longer accessible.")

def toggle_like_song(user_id: str, song_id: str) -> bool:
    """Toggles a song in the user's liked_songs table."""
    try:
        existing = supabase.table("liked_songs").select("*").eq("user_id", user_id).eq("song_id", song_id).execute()
        if existing.data:
            supabase.table("liked_songs").delete().eq("user_id", user_id).eq("song_id", song_id).execute()
            return False
        else:
            supabase.table("liked_songs").insert({"user_id": user_id, "song_id": song_id}).execute()
            return True
    except Exception as err:
        print(f"Error toggling song like state: {err}")
        return False

def fetch_liked_songs(user_id: str) -> list[dict]:
    """Retrieves full song records for all songs liked by the user."""
    response = supabase.table("liked_songs").select("song_id").eq("user_id", user_id).execute()
    liked_ids = [item["song_id"] for item in (response.data or [])]
    if not liked_ids:
        return []
    songs_response = supabase.table("songs").select("*").in_("id", liked_ids).execute()
    return songs_response.data or []